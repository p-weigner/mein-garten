"""Vorsichtiger, offline nutzbarer Saisonfenster-Kalender für Mein Garten.

Grundlage: fest versioniertes CC0-Datenpaket, keine freien Pflegeanweisungen.
Die Regeln sind US-Hortikultur-Planungswerte, keine für Brandenburg geprüften
Pflanzempfehlungen. Ohne explizit gesetzten Frostanker gibt es keine Termine.
Auch mit Frostanker werden nur *Vorschläge* angezeigt, nicht automatisch
Aussaat-, Schnitt- oder Düngeaufträge erzeugt.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import re
from typing import Any

STORAGE_KEY = "mein_garten_saison_v1.data"
CATALOG_FILE = Path(__file__).parent / "data" / "saison_openplantdb_v0_1.json"
CATALOG_FILES = (
    CATALOG_FILE,
    Path(__file__).parent / "data" / "saison_openplantdb_v0_2.json",
)
SOURCE = "OpenPlantDB"
LICENSE = "CC0 1.0"
SOURCE_URL = "https://github.com/cwfrazier1/openplantdb"
_ALLOWED_ANCHORS = ("last_frost", "first_frost")
_METHODS = {
    "direct": "Direktsaat prüfen",
    "indoor-start": "Vorziehen prüfen",
    "transplant": "Pflanzzeitpunkt prüfen",
    "bulb": "Zwiebelpflanzung prüfen",
    "tuber": "Knollenpflanzung prüfen",
    "cutting": "Vermehrungszeitraum prüfen",
    "division": "Teilungszeitraum prüfen",
}
_SCINAME = re.compile(r"^[A-Z][A-Za-z-]+ [a-z-]+$")
_SLUG = re.compile(r"^[a-z0-9-]{1,100}$")
_COMMIT = re.compile(r"^[a-f0-9]{40}$")
_DEFAULT = {"last_frost": "", "first_frost": ""}


class SaisonFehler(ValueError):
    """Ungültiges Saisonfenster, fehlende Quelle oder widersprüchliche Eingabe."""


def _kalendertag(raw: Any) -> date | None:
    if raw == "":
        return None
    if not isinstance(raw, str) or len(raw) != 10:
        raise SaisonFehler("Frostdatum muss im Format JJJJ-MM-TT stehen")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise SaisonFehler("Ungültiges Frostdatum") from exc
    if not (2020 <= parsed.year <= 2100) or parsed.isoformat() != raw:
        raise SaisonFehler("Frostdatum außerhalb des unterstützten Bereichs")
    return parsed


def pruefe_anker(raw: Any) -> dict:
    """Keinen US-Frostkalender stillschweigend auf den Garten übertragen."""
    if not isinstance(raw, dict) or set(raw) != set(_DEFAULT):
        raise SaisonFehler("Bitte nur die beiden Frost-Referenzdaten angeben")
    fruehjahr = _kalendertag(raw["last_frost"])
    herbst = _kalendertag(raw["first_frost"])
    if fruehjahr and herbst:
        if fruehjahr.year != herbst.year or fruehjahr >= herbst:
            raise SaisonFehler("Beide Frostdaten müssen in einem Jahr liegen, Frühling vor Herbst")
    return {k: raw[k] for k in _DEFAULT}


def pruefe_katalog(raw: Any) -> dict:
    """Importgrenze zwischen CC0-Rohdaten und Kalender-Engine."""
    if (not isinstance(raw, dict) or raw.get("schema") != 1
            or raw.get("quelle") != SOURCE or raw.get("lizenz") != LICENSE
            or not isinstance(raw.get("ausgangs_commit"), str)
            or not _COMMIT.fullmatch(raw["ausgangs_commit"])
            or not isinstance(raw.get("regeln"), list)
            or not 1 <= len(raw["regeln"]) <= 3000):
        raise SaisonFehler("Ungültiger oder unbekannter Saisonkatalog")
    upstream_hash = raw.get("quelle_sha256")
    if upstream_hash is not None and (
        not isinstance(upstream_hash, str)
        or not re.fullmatch(r"[a-f0-9]{64}", upstream_hash)
    ):
        raise SaisonFehler("Ungültiger Quellen-Fingerabdruck")
    by_species = {}
    slugs = set()
    for r in raw["regeln"]:
        if (not isinstance(r, dict)
                or set(r) != {"id", "wissenschaftlich", "gruppe", "anker",
                              "wochen_von", "wochen_bis", "methode"}
                or not isinstance(r["id"], str) or not _SLUG.fullmatch(r["id"])
                or not isinstance(r["wissenschaftlich"], str)
                or not _SCINAME.fullmatch(r["wissenschaftlich"])
                or not isinstance(r["gruppe"], str)
                or r["anker"] not in _ALLOWED_ANCHORS
                or r["methode"] not in _METHODS
                or type(r["wochen_von"]) is not int
                or type(r["wochen_bis"]) is not int
                or not -24 <= r["wochen_von"] <= r["wochen_bis"] <= 24):
            raise SaisonFehler("Ungültiger Saison-Datensatz")
        key = " ".join(r["wissenschaftlich"].split()).casefold()
        if key in by_species or r["id"] in slugs:
            raise SaisonFehler("Nicht eindeutiger botanischer Saison-Datensatz")
        record = deepcopy(r)
        record["_quell_commit"] = raw["ausgangs_commit"]
        by_species[key] = record
        slugs.add(r["id"])
    return by_species


def fenster_fuer(regel: dict, frostanker: dict) -> tuple[date, date] | None:
    """Frostwochenfenster nur bei manuell bestätigter Jahresreferenz."""
    anchor = _kalendertag(frostanker[regel["anker"]])
    if anchor is None:
        return None
    return (
        anchor + timedelta(days=7 * regel["wochen_von"]),
        anchor + timedelta(days=7 * regel["wochen_bis"]),
    )


def vorschlaege_fuer(
    katalog: dict, anker: dict, pflanzen: list[dict], aufgaben: list[dict]
) -> list[dict]:
    """Nur exakte wissenschaftliche Namen. Keine Gattungs- oder Sortenvermutung."""
    results = []
    for pflanze in pflanzen[:250]:
        species = pflanze.get("wissenschaftlich")
        if not isinstance(species, str):
            continue
        rule = katalog.get(" ".join(species.split()).casefold())
        if rule is None:
            continue
        period = fenster_fuer(rule, anker)
        anchor = _kalendertag(anker[rule["anker"]])
        planned = bool(anchor and any(
            t.get("pflanzen_id") == pflanze["id"]
            and (b := t.get("saisonbezug"))
            and isinstance(b, dict)
            and b.get("katalog_id") == rule["id"]
            and b.get("anker_jahr") == anchor.year
            for t in aufgaben
        ))
        results.append({
            "pflanzen_id": pflanze["id"],
            "pflanze": pflanze["name"],
            "wissenschaftlich": rule["wissenschaftlich"],
            "katalog_id": rule["id"],
            "titel": _METHODS[rule["methode"]],
            "fenster_von": period[0].isoformat() if period else None,
            "fenster_bis": period[1].isoformat() if period else None,
            "fehlender_anker": None if period else rule["anker"],
            "vorgemerkt": planned,
            "quelle": SOURCE, "lizenz": LICENSE,
            "quell_commit": rule["_quell_commit"],
            "pruefstatus": "unverbindliche_Planungshilfe",
            "anker_jahr": anchor.year if anchor else None,
        })
    return results


class SaisonService:
    """Eigenständige saisonale Daten, bewusst getrennt vom Garten-Datenmodell."""

    def __init__(self, hass: Any, backend: Any):
        from homeassistant.helpers.storage import Store

        self.hass = hass
        self.backend = backend
        self._store = Store(hass, 1, STORAGE_KEY)
        self._lock = asyncio.Lock()
        self._anker = dict(_DEFAULT)
        self._katalog = {}
        self._ausgangs_commit = ""
        self._quellversionen = []

    async def async_laden(self) -> None:
        def load_catalog() -> tuple[dict, list[dict]]:
            total = {}
            sources = []
            for file in CATALOG_FILES:
                # Nur lokal mitgelieferte Quellen, keine Downloads im HA-Green.
                if not file.is_file() or not 0 < file.stat().st_size <= 650_000:
                    raise SaisonFehler("Saisonkatalog fehlt oder ist zu groß")
                with file.open("r", encoding="utf-8") as stream:
                    raw = json.load(stream)
                subset = pruefe_katalog(raw)
                if set(total).intersection(subset):
                    raise SaisonFehler("Saisonkatalog enthält doppelte Arten aus mehreren Quellen")
                total.update(subset)
                sources.append({
                    "quelle": SOURCE, "lizenz": LICENSE,
                    "commit": raw["ausgangs_commit"],
                    "arten": len(subset),
                })
            if len(total) > 3000:
                raise SaisonFehler("Zu viele Saisonarten")
            return total, sources

        catalog, sources = await self.hass.async_add_executor_job(load_catalog)
        saved = await self._store.async_load()
        if saved is not None:
            if (not isinstance(saved, dict) or saved.get("version") != 1
                    or not isinstance(saved.get("anker"), dict)):
                raise SaisonFehler("Unbekanntes Saison-Speicherformat; Daten nicht überschreiben")
            self._anker = pruefe_anker(saved["anker"])
        self._katalog = catalog
        self._quellversionen = sources
        self._ausgangs_commit = sources[0]["commit"]

    def stand(self) -> dict:
        data = self.backend.snapshot()
        return {
            "anker": deepcopy(self._anker),
            "vorschlaege": vorschlaege_fuer(
                self._katalog, self._anker, data["pflanzen"], data["aufgaben"]
            ),
            "quelle": SOURCE,
            "lizenz": LICENSE,
            "quell_url": SOURCE_URL,
            "katalog_arten": len(self._katalog),
            "quell_commit": self._ausgangs_commit,
            "quellversionen": deepcopy(self._quellversionen),
            "hinweis": (
                "US-Planungswerte, keine regional geprüften Gartenempfehlungen. "
                "Nur bei bewusst gesetztem Frostdatum; eine Tätigkeit wird "
                "erst nach deiner Terminbestätigung angelegt."
            ),
        }

    async def async_anker_speichern(self, raw: dict) -> dict:
        neue = pruefe_anker(raw)
        async with self._lock:
            await self._store.async_save({"version": 1, "anker": neue})
            self._anker = neue
        return deepcopy(neue)

    async def async_vormerken(
        self, pflanzen_id: str, katalog_id: str, datum: str,
    ) -> dict:
        """WebSocket bekommt nur IDs und Datum; Quelle/Tätigkeit kommen vom Server."""
        async with self._lock:
            daten = self.backend.snapshot()
            p = next((x for x in daten["pflanzen"] if x["id"] == pflanzen_id), None)
            if p is None:
                raise SaisonFehler("Pflanze nicht gefunden")
            species = p.get("wissenschaftlich", "")
            r = self._katalog.get(" ".join(species.split()).casefold())
            if r is None or r["id"] != katalog_id:
                raise SaisonFehler("Keine eindeutige Saisonregel für diese botanische Art")
            anchor = _kalendertag(self._anker[r["anker"]])
            if anchor is None:
                raise SaisonFehler("Bitte zuerst den Frost-Referenztermin festlegen")
            period = fenster_fuer(r, self._anker)
            when = _kalendertag(datum)
            if when is None or not period[0] <= when <= period[1]:
                raise SaisonFehler("Termin liegt außerhalb des gespeicherten Saisonfensters")
            return await self.backend.async_aendern(
                "saisonpruefung_anlegen",
                pflanzen_id=pflanzen_id,
                saison_id=r["id"],
                anker_jahr=anchor.year,
                name=_METHODS[r["methode"]] + " – " + p["name"],
                faellig_am=when.isoformat(),
                fenster_von=period[0].isoformat(),
                fenster_bis=period[1].isoformat(),
                quell_commit=r["_quell_commit"],
                wissenschaftlich=r["wissenschaftlich"],
            )
