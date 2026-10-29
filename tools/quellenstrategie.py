"""Dynamische Zusammenführung deutscher Pflanzenpflegehinweise.

Für jede neue Pflanze verwendbar. Keine hartcodierten Pflanzenarten.
Externe Texte gelten NICHT automatisch als fachlich geprüft.
Die bisherige Haupt-Home-Assistant-Installation wird nicht verändert.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence

from tools.pflegewissen import (
    ArtNichtPassend,
    PFLEGEFELDER,
    Pflegehinweis,
    gleiche_art,
)

QUELLENREIHENFOLGE = {
    "OpenPlantbook": 10,
    "Permapeople": 20,
}


def _quell_meta(hinweis: Pflegehinweis) -> dict:
    """Öffentlichkeitsfähige Fachinformation; Originaltext bleibt intern."""
    return {
        "quelle": hinweis.quelle,
        "quell_id": hinweis.quell_id,
        "quell_url": hinweis.quell_url,
        "abgerufen_utc": hinweis.abgerufen_utc,
        "lizenz_hinweis": hinweis.lizenz_hinweis,
        "text_de": hinweis.deutsch.strip() if isinstance(hinweis.deutsch, str) else None,
        "uebersetzungsstatus": hinweis.uebersetzung,
        "pruefstatus": hinweis.pruefstatus,
        "automatische_aufgabe_erlaubt": False,
    }


def kombiniere_pflegewissen(
    art: str,
    hinweise: Sequence[Pflegehinweis],
    eigene_hinweise: Mapping[str, str] | None = None,
) -> dict:
    """Fasst Felder zusammen ohne Arten oder Fachautoritäten zu vermischen.

    Strategie:
      1. Der selbst eingegebene deutsche Hinweis hat Vorrang und wird nie überschrieben.
      2. Externe Anbieter werden getrennt beibehalten; keine stille Textfusion.
      3. Für die Anzeige kommt nur ein tatsächlich deutscher Text infrage.
      4. Wird eine Übersetzung vermisst, bleibt das Feld als ausstehend erkennbar.
      5. Alle automatischen Aufgaben sind gesperrt, solange kein gesondertes
         validiertes Pflegeregel-Modell und die nötigen Nutzungsrechte existieren.
    """
    if not isinstance(art, str) or not art.strip():
        raise ValueError("Botanische Art fehlt")
    eigene_hinweise = eigene_hinweise or {}
    for feld, text in eigene_hinweise.items():
        if feld not in PFLEGEFELDER or not isinstance(text, str):
            raise ValueError("Ungültiger eigener Pflegehinweis")

    grouped: dict[str, list[Pflegehinweis]] = defaultdict(list)
    for hinweis in hinweise:
        if not isinstance(hinweis, Pflegehinweis):
            raise TypeError("Ungültiger Pflegehinweis")
        if not gleiche_art(art, hinweis.art):
            raise ArtNichtPassend(
                f"Pflegehinweis für {hinweis.art!r} gehört nicht zu {art!r}"
            )
        grouped[hinweis.feld].append(hinweis)

    fields = {}
    for feld in PFLEGEFELDER:
        kandidaten = sorted(
            grouped.get(feld, []),
            key=lambda h: (
                QUELLENREIHENFOLGE.get(h.quelle, 100),
                h.quelle.casefold(),
                h.abgerufen_utc,
            ),
        )
        unique = []
        seen = set()
        for h in kandidaten:
            identifier = (h.quelle, h.quell_id, h.original_sha256)
            if identifier not in seen:
                seen.add(identifier)
                unique.append(h)

        eigene = eigene_hinweise.get(feld, "").strip()
        ausgewaehlt = next(
            (
                h
                for h in unique
                if isinstance(h.deutsch, str) and h.deutsch.strip()
            ),
            None,
        )
        if eigene:
            text_de = eigene
            status = "eigener_hinweis"
            quelle = "Eigener Hinweis"
        elif ausgewaehlt:
            text_de = ausgewaehlt.deutsch.strip()
            status = "uebersetzung_vorhanden"
            quelle = ausgewaehlt.quelle
        elif unique:
            text_de = None
            status = "uebersetzung_ausstehend"
            quelle = None
        else:
            text_de = None
            status = "keine_quelle"
            quelle = None

        fields[feld] = {
            "text_de": text_de,
            "status": status,
            "anzeigequelle": quelle,
            "eigener_hinweis": bool(eigene),
            "quellen": [_quell_meta(h) for h in unique],
            "pruefstatus": "nicht_fachlich_freigegeben",
            "automatische_aufgabe_erlaubt": False,
        }

    return {
        "art": art.strip(),
        "felder": fields,
        "pflegefelder_mit_deutschem_text": sum(
            bool(f["text_de"]) for f in fields.values()
        ),
        "pflegefelder_mit_externer_quelle": sum(
            bool(f["quellen"]) for f in fields.values()
        ),
        "automatische_pflegeaufgaben_erlaubt": False,
    }
