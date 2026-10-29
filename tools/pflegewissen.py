"""Quellenneutrales Pflegewissen: Identität, Quelle, Übersetzung, Prüfstatus.

Prototyp für Mein Garten V1. Keine direkte Home-Assistant-Integration.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

PFLEGEFELDER = ("sunlight", "watering", "soil", "fertilization", "pruning", "hardiness")
RISIKOFELDER = {"fertilization", "pruning"}
QUELLEN = {
    "openplantbook": {
        "name": "OpenPlantbook",
        "url": "https://open.plantbook.io/",
        "lizenz": "Nutzungsrechte für dauerhafte Speicherung vor Produktivstart klären",
    },
    "permapeople": {
        "name": "Permapeople",
        "url": "https://permapeople.org/",
        "lizenz": "CC BY-SA 4.0; Quellenangabe und Share-Alike beachten",
    },
}
PERMAPEOPLE_FELDER = {
    "Light requirement": "sunlight",
    "Water requirement": "watering",
    "Soil type": "soil",
    "USDA Hardiness zone": "hardiness",
}


class ArtNichtPassend(ValueError):
    """Die abgerufene Art entspricht nicht der ausgewählten Art."""


def artnorm(name: str) -> str:
    """Normalisiert nur Schreibweisen, KEINE unterschiedlichen Taxa oder Synonyme."""
    return re.sub(r"\s+", " ", str(name).replace("×", " x ").strip()).casefold()


def gleiche_art(erwartet: str, geliefert: str) -> bool:
    return bool(erwartet and geliefert) and artnorm(erwartet) == artnorm(geliefert)


def utc_jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Pflegehinweis:
    art: str
    feld: str
    original: str
    sprache_original: str
    quelle: str
    quell_id: str
    quell_url: str
    lizenz_hinweis: str
    abgerufen_utc: str
    deutsch: str | None = None
    uebersetzung: str = "ausstehend"
    pruefstatus: str = "unverifiziert"
    aufgabenfreigabe: bool = False
    original_sha256: str = ""

    def __post_init__(self):
        if self.feld not in PFLEGEFELDER:
            raise ValueError("Unbekanntes Pflegefeld")
        if not self.original or not self.quelle or not self.art:
            raise ValueError("Pflegehinweis muss Text, Quelle und Art haben")
        self.original_sha256 = hashlib.sha256(self.original.encode("utf-8")).hexdigest()
        # Freitexte können niemals direkt Pflegemaßnahmen auslösen.
        self.aufgabenfreigabe = False

    def to_dict(self):
        return asdict(self)


def _hinweis(art: str, feld: str, text: str, provider: str, source_id: str,
             source_lang: str, source_url: str) -> Pflegehinweis:
    info = QUELLEN[provider]
    text = text.strip()
    if not text or len(text) > 12000:
        raise ValueError("Leerer oder übermäßig langer Quelltext")
    return Pflegehinweis(
        art=art, feld=feld, original=text, sprache_original=source_lang,
        quelle=info["name"], quell_id=source_id,
        quell_url=source_url or info["url"], lizenz_hinweis=info["lizenz"],
        abgerufen_utc=utc_jetzt(),
        deutsch=text if source_lang == "de" else None,
        uebersetzung="original_deutsch" if source_lang == "de" else "ausstehend",
    )


def normalisiere_openplantbook(antwort: dict, erwartete_art: str) -> list[Pflegehinweis]:
    # Die API verwendet pid als stabilen Schlüssel; ein Alias ist kein Artbeweis.
    art = str(antwort.get("pid") or antwort.get("scientific_name") or "").strip()
    if not gleiche_art(erwartete_art, art):
        raise ArtNichtPassend(f"OpenPlantbook lieferte keine eindeutige Übereinstimmung mit {erwartete_art}")
    ergebnisse = []
    for feld in PFLEGEFELDER:
        if feld not in ("sunlight", "watering", "soil", "fertilization", "pruning"):
            continue
        text = antwort.get(feld)
        if isinstance(text, str) and text.strip():
            ergebnisse.append(_hinweis(
                erwartete_art, feld, text, "openplantbook", art, "en",
                QUELLEN["openplantbook"]["url"],
            ))
    return ergebnisse


def normalisiere_permapeople(antwort: dict, erwartete_art: str) -> list[Pflegehinweis]:
    art = str(antwort.get("scientific_name") or "").strip()
    if not gleiche_art(erwartete_art, art):
        raise ArtNichtPassend(f"Permapeople lieferte keine eindeutige Übereinstimmung mit {erwartete_art}")
    sid = str(antwort.get("id") or "")
    url = QUELLEN["permapeople"]["url"].rstrip("/") + str(antwort.get("link") or "/")
    ergebnisse = []
    attributes = antwort.get("data") or []
    if not isinstance(attributes, list):
        raise ValueError("Ungültige Attributliste")
    for attr in attributes:
        if not isinstance(attr, dict):
            continue
        feld = PERMAPEOPLE_FELDER.get(attr.get("key"))
        wert = attr.get("value")
        # Insbesondere Giftigkeit und Essbarkeit werden bewusst NICHT übernommen.
        if feld and isinstance(wert, str) and wert.strip():
            ergebnisse.append(_hinweis(erwartete_art, feld, wert,
                                       "permapeople", sid, "en", url))
    return ergebnisse


class LokalerUebersetzungscache:
    """Atomar gespeicherte, private JSON-Datei. Nicht im öffentlichen GitHub-Repo."""
    def __init__(self, pfad: str | Path):
        self.pfad = Path(pfad)
        self.daten = {}
        if self.pfad.exists():
            obj = json.loads(self.pfad.read_text(encoding="utf-8"))
            if not isinstance(obj, dict):
                raise ValueError("Ungültiger Übersetzungscache")
            self.daten = obj

    @staticmethod
    def schluessel(original: str, provider: str, feld: str) -> str:
        return hashlib.sha256(
            json.dumps([provider, feld, original, "de", "v1"],
                       ensure_ascii=False).encode("utf-8")).hexdigest()

    def _sichern(self):
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".garten-", dir=self.pfad.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.daten, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.pfad)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def get(self, key: str) -> str | None:
        wert = self.daten.get(key)
        return wert if isinstance(wert, str) and wert.strip() else None

    def put(self, key: str, uebersetzung: str):
        if not uebersetzung.strip():
            raise ValueError("Leere Übersetzung")
        self.daten[key] = uebersetzung
        self._sichern()


def uebersetze_hinweise(
    hinweise: list[Pflegehinweis],
    uebersetzer: Callable[[str], str] | None,
    cache: LokalerUebersetzungscache,
) -> list[Pflegehinweis]:
    """Nur öffentliche Quelltexte werden an den optionalen Übersetzer gegeben."""
    for hinweis in hinweise:
        if hinweis.sprache_original == "de":
            continue
        key = cache.schluessel(hinweis.original, hinweis.quelle, hinweis.feld)
        existing = cache.get(key)
        if existing:
            hinweis.deutsch = existing
            hinweis.uebersetzung = "cache"
        elif uebersetzer is not None:
            try:
                result = uebersetzer(hinweis.original)
                if isinstance(result, str) and result.strip():
                    cache.put(key, result.strip())
                    hinweis.deutsch = result.strip()
                    hinweis.uebersetzung = "automatisch"
                else:
                    hinweis.uebersetzung = "fehler"
            except (OSError, ValueError, RuntimeError, TimeoutError):
                hinweis.uebersetzung = "fehler"
        else:
            hinweis.uebersetzung = "nicht_konfiguriert"
    return hinweise


def fuer_deutsche_anzeige(hinweise: list[Pflegehinweis]) -> list[dict]:
    """Englischer Originaltext bleibt verfügbar, aber nicht als deutscher Pflegetext."""
    return [{
        "feld": h.feld,
        "text_de": h.deutsch,
        "deutsch_verfuegbar": bool(h.deutsch),
        "original_einblendbar": True,
        "quelle": h.quelle,
        "quell_url": h.quell_url,
        "lizenz": h.lizenz_hinweis,
        "uebersetzungsstatus": h.uebersetzung,
        "pruefstatus": h.pruefstatus,
        "automatische_aufgabe_erlaubt": False,
    } for h in hinweise]
