"""Recherche: deutsche Pflanzen-Schreibvarianten über Wikimedia-/Wikidata-APIs.

Keine privaten Benutzerdaten, keine Pflegefreitexte. Nur öffentliche Titel,
Taxonbezeichnungen und HTTP-Fehlerklassen protokollieren.
"""
from __future__ import annotations
import json
import time
import urllib.parse
import urllib.request

QUERY = (
    "Rispenhortensie",
    "Rispen-Hortensie",
    "Japanischer Fächerahorn",
    "Fächerahorn",
    "Fächer-Ahorn",
    "Japanischer Ahorn",
    "Süßkirsche",
    "Gewöhnlicher Flieder",
)


def get(url, args):
    req = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(args),
        headers={
            "Accept": "application/json",
            "User-Agent": "MeinGarten-BotanischeNamensrecherche/1.0 (github.com/p-weigner/mein-garten)",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        raw = res.read(500001)
    if len(raw) > 500000:
        raise ValueError("Unerwartet große API-Antwort")
    return json.loads(raw)


def run():
    for term in QUERY:
        for label, url, args in (
            ("de_wikipedia_opensearch", "https://de.wikipedia.org/w/api.php", {
                "action": "opensearch", "search": term, "limit": 5,
                "format": "json", "namespace": 0,
            }),
            ("de_wikipedia_suche", "https://de.wikipedia.org/w/api.php", {
                "action": "query", "list": "search", "srsearch": term,
                "srlimit": 5, "format": "json",
            }),
            ("wikidata_aliase", "https://www.wikidata.org/w/api.php", {
                "action": "wbsearchentities", "language": "de",
                "search": term, "uselang": "de", "limit": 5,
                "type": "item", "format": "json",
            }),
        ):
            try:
                payload = get(url, args)
                if label == "de_wikipedia_opensearch":
                    titles = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                elif label == "de_wikipedia_suche":
                    titles = [x.get("title") for x in payload.get("query", {}).get("search", [])]
                else:
                    titles = [x.get("label") for x in payload.get("search", [])]
                print(json.dumps({"query": term, "provider": label,
                    "titles": titles[:5]}, ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({"query": term, "provider": label,
                    "error": type(exc).__name__}, ensure_ascii=False), flush=True)
            time.sleep(0.3)


if __name__ == "__main__":
    run()
