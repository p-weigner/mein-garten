"""Offline-Grundmerkmale für den Garten, aus einem fixierten CC0-Datensatz.

Allgemeine, teilweise US-orientierte Quellkategorien – keine regional
verifizierten Empfehlungen und NIEMALS Grundlage autonomer Pflegeaufgaben.
Nur exakter botanischer Artnamensabgleich; keine Gattung-/Sorten-Heuristik.
Die große Rohdatenbank wird NICHT im Home Assistant heruntergeladen.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SOURCE = "OpenPlantDB"
LICENSE = "CC0 1.0"
COMMIT = "c6287784527ebb4162e242394ee08f46d338218b"
SOURCE_SHA256 = "aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751"
CATALOG_SHA256 = "fb368b13a28d42bebdedadeff6e76fca09f322d4b2ca04dbeb3637fbf37e7a38"
SOURCE_URL = "https://github.com/cwfrazier1/openplantdb"
SOURCE_DATA_URL = f"{SOURCE_URL}/blob/{COMMIT}/data/plants.json"
FILE = Path(__file__).parent / "data" / "standort_cc0_v1.json"
MAX_BYTES = 900_000
FIELDS = ("sun", "water", "frost_tolerance", "season")
VALUES = {
    "sun": {"full", "partial", "shade"},
    "water": {"low", "moderate", "high"},
    "frost_tolerance": {"hardy", "half-hardy", "tender"},
    "season": {"cool", "warm", "perennial"},
}
SCIENTIFIC_NAME = re.compile(r"^[A-Z][A-Za-z-]+ [a-z-]+$")
_NOTICE = (
    "Unverbindliche Kategorien aus einer offenen, teilweise US-orientierten "
    "Garten-Datenquelle. Keine fachliche Prüfung für Brandenburg, keine "
    "konkrete Gießmenge, keine sichere Winterhärte und keine automatische "
    "Schnitt-, Dünge- oder Bewässerungsanweisung."
)


class StandortFehler(ValueError):
    """Ungültiger oder nicht verifizierbarer Standort-Katalog."""


def pruefe_standortdaten(raw: Any) -> dict[str, dict[str, str]]:
    """Reject unknown fields, invalid classifications and ambiguous taxonomy."""
    if (
        not isinstance(raw, dict)
        or set(raw) != {
            "schema", "quelle", "lizenz", "ausgangs_commit", "quelle_sha256",
            "herkunft", "pruefstatus", "felder", "arten",
        }
        or type(raw["schema"]) is not int or raw["schema"] != 1
        or raw["quelle"] != SOURCE or raw["lizenz"] != LICENSE
        or raw["ausgangs_commit"] != COMMIT
        or raw["quelle_sha256"] != SOURCE_SHA256
        or raw["herkunft"] != SOURCE_DATA_URL
        or raw["pruefstatus"] != "unverbindliche_Quellkategorien"
        or raw["felder"] != list(FIELDS)
        or not isinstance(raw["arten"], list)
        or not 10_000 <= len(raw["arten"]) <= 12_000
    ):
        raise StandortFehler("Unbekanntes oder unvollständiges Standortdatenpaket")

    result = {}
    for item in raw["arten"]:
        if (
            not isinstance(item, list) or len(item) != len(FIELDS) + 1
            or not isinstance(item[0], str)
            or not 3 <= len(item[0]) <= 160
            or not SCIENTIFIC_NAME.fullmatch(item[0])
        ):
            raise StandortFehler("Ungültige botanische Art")
        key = item[0].casefold()
        if key in result:
            raise StandortFehler("Doppelte botanische Art")
        traits = {}
        for name, value in zip(FIELDS, item[1:]):
            if value is None:
                continue
            if not isinstance(value, str) or value not in VALUES[name]:
                raise StandortFehler("Unbekannte oder mehrdeutige Standortkategorie")
            traits[name] = value
        if not traits:
            raise StandortFehler("Standortprofil ohne belegtes Merkmal")
        result[key] = traits
    return result


class StandortService:
    """In Home Assistant ausschließlich lokaler Dateizugriff, ohne Store/API."""

    def __init__(self, hass: Any):
        self.hass = hass
        self._profiles = {}

    async def async_laden(self) -> None:
        def _lade():
            if not FILE.is_file() or not 0 < FILE.stat().st_size <= MAX_BYTES:
                raise StandortFehler("Standortdaten fehlen oder sind zu groß")
            data = FILE.read_bytes()
            if hashlib.sha256(data).hexdigest() != CATALOG_SHA256:
                raise StandortFehler("Standortkatalog wurde verändert")
            return pruefe_standortdaten(json.loads(data))

        self._profiles = await self.hass.async_add_executor_job(_lade)

    def stand_fuer(self, pflanzen: list[dict]) -> dict:
        """Die WS-Antwort enthält NUR Profile der eigenen Pflanzen, nie 10k Arten."""
        result = {}
        for plant in pflanzen[:250]:
            if not isinstance(plant, dict) or not isinstance(plant.get("id"), str):
                continue
            species = plant.get("wissenschaftlich", "")
            if not isinstance(species, str) or not SCIENTIFIC_NAME.fullmatch(species):
                continue
            traits = self._profiles.get(species.casefold())
            if traits:
                result[plant["id"]] = {
                    "wissenschaftlich": species,
                    "merkmale": deepcopy(traits),
                }
        return {
            "profile": result,
            "abgedeckte_pflanzen": len(result),
            "katalog_arten": len(self._profiles),
            "quelle": SOURCE,
            "lizenz": LICENSE,
            "quell_url": SOURCE_URL,
            "quell_commit": COMMIT,
            "hinweis": _NOTICE,
        }
