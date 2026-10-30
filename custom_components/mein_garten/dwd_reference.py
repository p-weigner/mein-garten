"""Validierte, schreibgeschützte DWD-Phänologiereferenz für Mein Garten.

Keine Netzwerkzugriffe auf Home Assistant Green. Die Daten stammen aus einem
fest mitgelieferten kompakten CI-Snapshot mit DWD-Provenienz (CC BY 4.0).
Weder Standortdaten noch botanische Benutzereinträge fließen in die Quelle.
Die Werte dürfen NIEMALS Pflegeaufgaben auslösen.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

DATA_FILE = Path(__file__).parent / "data" / "dwd_phaenologie_region_v1.json"
SOURCE_NAME = "Deutscher Wetterdienst (DWD), Climate Data Center"
SOURCE_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/"
    "observations_germany/phenology/immediate_reporters/wild/recent/"
)
_ALLOWED = {
    "hasel_bluete": ("Hasel (Arten nicht unterschieden)", "Blütebeginn"),
    "forsythie_bluete": ("Forsythie", "Blütebeginn"),
    "rotbuche_blatt": ("Rotbuche", "Blattentfaltung"),
}
_REGIONS = {"nordost", "deutschland"}
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")


class PhänologieFehler(ValueError):
    """Das DWD-Referenzpaket ist unvollständig oder widersprüchlich."""


def _iso(value: Any) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise PhänologieFehler("Ungültiger ISO-DWD-Kalendertag")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise PhänologieFehler("Ungültiges DWD-Datum") from exc
    if result.isoformat() != value:
        raise PhänologieFehler("DWD-Datum nicht ISO-konform")
    return result


def pruefe_dwd_paket(raw: Any) -> dict:
    """Harte Integritätsgrenze; keine fremden Texte ungeprüft an die UI."""
    if (
        not isinstance(raw, dict)
        or raw.get("schema") != 1
        or raw.get("quelle") != SOURCE_NAME
        or raw.get("lizenz") != "CC BY 4.0"
        or raw.get("quellen_url") != SOURCE_URL
        or raw.get("meldeverfahren") != "DWD Sofortmelder, wildwachsende Pflanzen"
        or not isinstance(raw.get("qualitaetsfilter"), str)
        or "Eintrittsdatum_QB=1" not in raw["qualitaetsfilter"]
    ):
        raise PhänologieFehler("Unbekannte DWD-Referenzdatei")
    today = _iso(raw.get("abgerufen_am"))
    if today.year < 2024 or today > date.today():
        raise PhänologieFehler("DWD-Quellenstand ungültig")
    if (
        not isinstance(raw.get("regionen"), dict)
        or set(raw["regionen"]) != _REGIONS
    ):
        raise PhänologieFehler("DWD-Gebietsdefinitionen fehlen")
    area = raw["regionen"]["nordost"]
    if not isinstance(area, dict) or (
        area.get("lat_min"), area.get("lat_max"),
        area.get("lon_min"), area.get("lon_max")
    ) != (52.0, 54.2, 12.0, 15.0):
        raise PhänologieFehler("DWD-Gebietsgrenzen weichen ab")
    for region in _REGIONS:
        if not isinstance(raw["regionen"][region].get("label"), str):
            raise PhänologieFehler("DWD-Gebietsbezeichnung fehlt")
    hashes = raw.get("quell_sha256")
    if (
        not isinstance(hashes, dict)
        or set(hashes) != {
            "stationen", "hasel_bluete", "forsythie_bluete",
            "rotbuche_blatt",
        }
        or not all(isinstance(s, str) and _SHA256.fullmatch(s)
                   for s in hashes.values())
    ):
        raise PhänologieFehler("DWD-Quelldateien nicht identifizierbar")
    values = raw.get("werte")
    if not isinstance(values, list) or not 5 <= len(values) <= 48:
        raise PhänologieFehler("DWD-Referenzumfang unplausibel")
    seen = set()
    for row in values:
        if not isinstance(row, dict) or set(row) != {
            "indikator", "pflanze", "phase", "region", "jahr",
            "stationen", "median", "quartil_von", "quartil_bis",
        }:
            raise PhänologieFehler("Unbekannte DWD-Datenfelder")
        key = row["indikator"]
        if (
            not isinstance(key, str)
            or key not in _ALLOWED
            or (row["pflanze"], row["phase"]) != _ALLOWED[key]
            or row["region"] not in _REGIONS
            or type(row["jahr"]) is not int
            or not 2023 <= row["jahr"] <= today.year
            or type(row["stationen"]) is not int
            or not 5 <= row["stationen"] <= 2000
        ):
            raise PhänologieFehler("Ungültige DWD-Referenz")
        day1, day2, day3 = (_iso(row[k]) for k in (
            "quartil_von", "median", "quartil_bis"
        ))
        if (
            not day1 <= day2 <= day3
            or any(d.year != row["jahr"] for d in (day1, day2, day3))
        ):
            raise PhänologieFehler("Inkonsequenter DWD-Referenzzeitraum")
        signature = (key, row["region"], row["jahr"])
        if signature in seen:
            raise PhänologieFehler("Doppelte DWD-Statistik")
        seen.add(signature)

    # Keine externen Freitexte nötig. Gefrorene Quelle enthält nur einen
    # festen Hinweistext und offizielle Labels, nie Nutzer- oder Stationsorte.
    return deepcopy({
        "quelle": SOURCE_NAME,
        "lizenz": "CC BY 4.0",
        "quellen_url": SOURCE_URL,
        "abgerufen_am": raw["abgerufen_am"],
        "meldeverfahren": raw["meldeverfahren"],
        "qualitaetsfilter": raw["qualitaetsfilter"],
        "regionen": raw["regionen"],
        "werte": values,
        "hinweis": (
            "DWD-Stationsbeobachtungen: teilweise nur formal geprüft. "
            "Grobe Region statt Standortmessung. "
            "Keine Prognose und keine Pflegeanweisung."
        ),
    })


class DwdPhaenologie:
    """Lädt ausschließlich den mitgelieferten Snapshot im HA-Executor."""

    def __init__(self, hass: Any):
        self.hass = hass
        self._stand = None

    async def async_laden(self) -> None:
        def lade():
            if not DATA_FILE.is_file() or not 0 < DATA_FILE.stat().st_size <= 55_000:
                raise PhänologieFehler("DWD-Referenzdatei fehlt oder ist zu groß")
            with DATA_FILE.open("r", encoding="utf-8") as stream:
                return pruefe_dwd_paket(json.load(stream))

        self._stand = await self.hass.async_add_executor_job(lade)

    def stand(self) -> dict | None:
        return deepcopy(self._stand)
