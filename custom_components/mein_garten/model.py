"""Lokales Datenmodell für Mein Garten V1 – unabhängig von Home Assistant.

Jede Pflanzenart wird dynamisch als Datensatz angelegt, nie in Code hinterlegt.
Externe Pflegefreitexte gehören NICHT in dieses Stammdatenmodell.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from uuid import uuid4

SCHEMA_VERSION = 1
PFLANZENGRUPPEN = (
    "Blumen, Stauden und Rosen",
    "Sträucher, Hecken und Bäume",
    "Gemüse und Kräuter",
    "Obst und Beeren",
    "Kübel- und Topfpflanzen",
)


class DatensatzFehler(ValueError):
    """Ungültige Eingabe, nicht vorhandenes Objekt oder Datenkonflikt."""


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _id() -> str:
    return str(uuid4())


def _text(wert: str, feld: str, maximum: int, leer_erlaubt: bool = False) -> str:
    if not isinstance(wert, str):
        raise DatensatzFehler(f"{feld}: Text erwartet")
    value = " ".join(wert.split()) if feld != "Notizen" else wert.strip()
    if not value and not leer_erlaubt:
        raise DatensatzFehler(f"{feld} darf nicht leer sein")
    if len(value) > maximum:
        raise DatensatzFehler(f"{feld} überschreitet {maximum} Zeichen")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise DatensatzFehler(f"{feld} enthält Steuerzeichen")
    return value


def _datum(wert: str | None) -> str | None:
    if wert is None or wert == "":
        return None
    if not isinstance(wert, str):
        raise DatensatzFehler("Datum muss ISO-Datum sein")
    try:
        day = date.fromisoformat(wert)
    except ValueError as exc:
        raise DatensatzFehler("Datum muss JJJJ-MM-TT sein") from exc
    if day.isoformat() != wert:
        raise DatensatzFehler("Datum muss JJJJ-MM-TT sein")
    return wert


def _existiert(liste: list[dict], id: str, typ: str) -> dict:
    for obj in liste:
        if obj["id"] == id:
            return obj
    raise DatensatzFehler(f"{typ} nicht gefunden")


class GartenDaten:
    """Unabhängig testbare Operationen; Snapshot eignet sich für HA Store."""

    def __init__(self, data: dict | None = None):
        if data is None:
            data = {
                "version": SCHEMA_VERSION,
                "bereiche": [],
                "pflanzen": [],
                "aufgaben": [],
                "historie": [],
            }
        if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
            raise DatensatzFehler("Unbekanntes Garten-Datenformat. Daten nicht überschreiben.")
        for key in ("bereiche", "pflanzen", "aufgaben", "historie"):
            if not isinstance(data.get(key), list):
                raise DatensatzFehler(f"Garten-Datenfehler: {key}")
            if any(not isinstance(v, dict) or not isinstance(v.get("id"), str)
                   for v in data[key]):
                raise DatensatzFehler(f"Garten-Datenfehler in {key}")
            ids = [v["id"] for v in data[key]]
            if len(ids) != len(set(ids)):
                raise DatensatzFehler(f"Doppelte IDs in {key}")
        self._data = deepcopy(data)

    def snapshot(self) -> dict:
        return deepcopy(self._data)

    def _event(self, art: str, obj_id: str, person: str | None = None) -> None:
        self._data["historie"].append({
            "id": _id(),
            "art": art,
            "objekt_id": obj_id,
            "person": person,
            "datum_utc": _jetzt(),
        })
        # Für kleine Hausgärten ausreichend; übergroße History verhindern.
        self._data["historie"] = self._data["historie"][-3000:]

    def bereich_anlegen(self, name: str) -> dict:
        name = _text(name, "Bereichsname", 120)
        if any(v["name"].casefold() == name.casefold() for v in self._data["bereiche"]):
            raise DatensatzFehler("Dieser Bereich existiert bereits")
        obj = {"id": _id(), "name": name, "erstellt_utc": _jetzt()}
        self._data["bereiche"].append(obj)
        return deepcopy(obj)

    def bereich_umbenennen(self, bereich_id: str, name: str) -> dict:
        area = _existiert(self._data["bereiche"], bereich_id, "Bereich")
        name = _text(name, "Bereichsname", 120)
        if any(v["id"] != bereich_id and v["name"].casefold() == name.casefold()
               for v in self._data["bereiche"]):
            raise DatensatzFehler("Dieser Bereich existiert bereits")
        area["name"] = name
        return deepcopy(area)

    def bereich_entfernen(self, bereich_id: str) -> dict:
        area = _existiert(self._data["bereiche"], bereich_id, "Bereich")
        self._data["bereiche"] = [
            x for x in self._data["bereiche"] if x["id"] != bereich_id
        ]
        for plant in self._data["pflanzen"]:
            if plant["bereich_id"] == bereich_id:
                plant["bereich_id"] = None
        for task in self._data["aufgaben"]:
            if task["bereich_id"] == bereich_id:
                task["bereich_id"] = None
        self._event("bereich_entfernt", bereich_id)
        return deepcopy(area)

    def pflanze_anlegen(
        self, name: str, wissenschaftlich: str = "", bereich_id: str | None = None,
        gruppe: str | None = None, notizen: str = "",
    ) -> dict:
        name = _text(name, "Pflanzenname", 120)
        wissenschaftlich = _text(
            wissenschaftlich, "Wissenschaftlicher Name", 160, leer_erlaubt=True
        )
        notizen = _text(notizen, "Notizen", 4000, leer_erlaubt=True)
        if bereich_id:
            _existiert(self._data["bereiche"], bereich_id, "Bereich")
        if gruppe is not None and gruppe not in PFLANZENGRUPPEN:
            raise DatensatzFehler("Unbekannte Pflanzengruppe")
        now = _jetzt()
        obj = {
            "id": _id(), "name": name,
            "wissenschaftlich": wissenschaftlich,
            "bereich_id": bereich_id or None,
            "gruppe": gruppe,
            "notizen": notizen,
            "erstellt_utc": now,
            "aktualisiert_utc": now,
        }
        self._data["pflanzen"].append(obj)
        return deepcopy(obj)

    def pflanze_bearbeiten(self, pflanzen_id: str, **felder) -> dict:
        plant = _existiert(self._data["pflanzen"], pflanzen_id, "Pflanze")
        erlaubte = {"name", "wissenschaftlich", "bereich_id", "gruppe", "notizen"}
        if not felder or any(key not in erlaubte for key in felder):
            raise DatensatzFehler("Unbekanntes oder fehlendes Pflanzenfeld")
        neu = dict(plant)
        neu.update(felder)
        neu["name"] = _text(neu["name"], "Pflanzenname", 120)
        neu["wissenschaftlich"] = _text(
            neu["wissenschaftlich"], "Wissenschaftlicher Name", 160, True
        )
        neu["notizen"] = _text(neu["notizen"], "Notizen", 4000, True)
        if neu["bereich_id"] is not None:
            _existiert(self._data["bereiche"], neu["bereich_id"], "Bereich")
        if neu["gruppe"] is not None and neu["gruppe"] not in PFLANZENGRUPPEN:
            raise DatensatzFehler("Unbekannte Pflanzengruppe")
        neu["aktualisiert_utc"] = _jetzt()
        plant.update(neu)
        return deepcopy(plant)

    def pflanze_entfernen(self, pflanzen_id: str) -> dict:
        plant = _existiert(self._data["pflanzen"], pflanzen_id, "Pflanze")
        self._data["pflanzen"] = [
            p for p in self._data["pflanzen"] if p["id"] != pflanzen_id
        ]
        entfernte_tasks = [
            t["id"] for t in self._data["aufgaben"] if t["pflanzen_id"] == pflanzen_id
        ]
        self._data["aufgaben"] = [
            t for t in self._data["aufgaben"] if t["pflanzen_id"] != pflanzen_id
        ]
        # Echte Löschung: alte personenbezogene Aufgaben-/Aktivitätsbezüge
        # der entfernten Pflanze ebenfalls löschen.
        self._data["historie"] = [
            e for e in self._data["historie"]
            if e["objekt_id"] != pflanzen_id and e["objekt_id"] not in entfernte_tasks
        ]
        return deepcopy(plant)

    def aufgabe_anlegen(
        self, name: str, faellig_am: str | None = None,
        pflanzen_id: str | None = None, bereich_id: str | None = None,
    ) -> dict:
        name = _text(name, "Aufgabenname", 200)
        faellig_am = _datum(faellig_am)
        if pflanzen_id is not None:
            _existiert(self._data["pflanzen"], pflanzen_id, "Pflanze")
        if bereich_id is not None:
            _existiert(self._data["bereiche"], bereich_id, "Bereich")
        obj = {
            "id": _id(), "name": name, "faellig_am": faellig_am,
            "pflanzen_id": pflanzen_id, "bereich_id": bereich_id,
            "status": "offen", "erledigt_utc": None,
            "erstellt_utc": _jetzt(), "herkunft": "manuell",
        }
        self._data["aufgaben"].append(obj)
        return deepcopy(obj)

    def aufgabe_erledigen(self, aufgaben_id: str, person: str | None = None) -> dict:
        task = _existiert(self._data["aufgaben"], aufgaben_id, "Aufgabe")
        if task["status"] != "erledigt":
            task["status"] = "erledigt"
            task["erledigt_utc"] = _jetzt()
            self._event("aufgabe_erledigt", aufgaben_id, person)
        return deepcopy(task)

    def aufgabe_wieder_oeffnen(self, aufgaben_id: str, person: str | None = None) -> dict:
        task = _existiert(self._data["aufgaben"], aufgaben_id, "Aufgabe")
        if task["status"] != "offen":
            task["status"] = "offen"
            task["erledigt_utc"] = None
            self._event("aufgabe_wieder_geoeffnet", aufgaben_id, person)
        return deepcopy(task)

    def aufgabe_entfernen(self, aufgaben_id: str) -> dict:
        task = _existiert(self._data["aufgaben"], aufgaben_id, "Aufgabe")
        self._data["aufgaben"] = [
            t for t in self._data["aufgaben"] if t["id"] != aufgaben_id
        ]
        self._data["historie"] = [
            e for e in self._data["historie"] if e["objekt_id"] != aufgaben_id
        ]
        return deepcopy(task)
