"""Isolierte Live-Diagnose: deutsche GBIF-Trivialnamenssuche statt Suggest.

Liest nur öffentliche Suchergebnisse und veröffentlicht keine privaten Daten.
Ausgabe enthält maximal drei botanische Namen je Versuch, keinen Quellvolltext.
"""
from __future__ import annotations
import json
import time
import urllib.parse
import urllib.request

NAMES = [
    "Rispenhortensie",
    "Gewöhnlicher Flieder",
    "Felsenbirne",
    "Apfelbaum",
    "Süßkirsche",
    "Zwetschge",
    "Engelstrompete",
    "Japanischer Fächerahorn",
]
BACKBONE = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
API = "https://api.gbif.org/v1/species/search"


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "MeinGarten-VernacularResearch/1.0 (github.com/p-weigner/mein-garten)",
    })
    with urllib.request.urlopen(request, timeout=10) as res:
        raw = res.read(500001)
    if len(raw) > 500000:
        raise ValueError("Antwort zu groß")
    return json.loads(raw)


def run():
    for query in NAMES:
        for mode, extra in [
            ("nur_gbif_backbone", {"datasetKey": BACKBONE}),
            ("alle_checklisten", {}),
        ]:
            try:
                data = get({
                    "q": query, "qField": "VERNACULAR",
                    "rank": "SPECIES", "status": "ACCEPTED",
                    "limit": 12, **extra,
                })
                results = data.get("results", [])[:12]
                items = [{
                    "name": v.get("canonicalName") or v.get("scientificName"),
                    "kingdom": v.get("kingdom"),
                    "status": v.get("taxonomicStatus"),
                    "rank": v.get("rank"),
                    "key": v.get("key"),
                    "taxonKey": v.get("taxonKey"),
                    "nubKey": v.get("nubKey"),
                } for v in results if isinstance(v, dict)
                    and str(v.get("kingdom", "")).casefold() == "plantae"]
                print(json.dumps({
                    "frage": query, "modus": mode,
                    "alle": data.get("count"),
                    "pflanzen": len(items), "treffer": items[:6],
                }, ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({
                    "frage": query, "modus": mode,
                    "fehler": type(exc).__name__
                }, ensure_ascii=False), flush=True)
            time.sleep(0.4)


if __name__ == "__main__":
    run()
