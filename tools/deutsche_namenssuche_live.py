"""Live-Test der deutschsprachigen Pflanzensuche mit öffentlichen Taxonomie-APIs.

Ermittelt nur öffentliche botanische Namen, deutsche gebräuchliche Namen
und taxonomische Ränge. Keine Benutzer-, Garten- oder Standortdaten.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "berichte"

SUCHBEGRIFFE = (
    "Hortensie",
    "Bauernhortensie",
    "Lavendel",
    "Tomate",
    "Apfelbaum",
    "Rote Johannisbeere",
)


def _fetch(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "MeinGarten-GermanSearchStudy/1.0 (noncommercial)",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(700_001)
    if len(raw) > 700_000:
        raise ValueError("Antwort zu groß")
    return json.loads(raw)


def _clean(value, length=140):
    return str(value or "").replace("\n", " ").replace("\r", " ")[:length]


def run():
    OUTPUT.mkdir(exist_ok=True)
    data = []
    for query in SUCHBEGRIFFE:
        entry = {"suche": query, "anbieter": {}}
        urls = {
            "inat": "https://api.inaturalist.org/v1/taxa/autocomplete?"
            + urllib.parse.urlencode({
                "q": query, "locale": "de", "per_page": 12,
                "taxon_id": 47126,
            }),
            "gbif": "https://api.gbif.org/v1/species/suggest?"
            + urllib.parse.urlencode({"q": query, "limit": 12}),
        }
        for provider, url in urls.items():
            try:
                response = _fetch(url)
                if provider == "inat":
                    results = response.get("results", [])
                    candidates = [{
                        "wissenschaftlich": _clean(v.get("name")),
                        "deutscher_name": _clean(v.get("preferred_common_name")),
                        "rang": _clean(v.get("rank")),
                        "id": v.get("id"),
                    } for v in results[:8] if isinstance(v, dict)]
                else:
                    if not isinstance(response, list):
                        raise ValueError("Ungültiges GBIF-Antwortformat")
                    candidates = [{
                        "wissenschaftlich": _clean(
                            v.get("canonicalName") or v.get("scientificName")
                        ),
                        "deutscher_name": "",
                        "rang": _clean(v.get("rank")),
                        "id": v.get("key"),
                    } for v in response[:8] if isinstance(v, dict)]
                entry["anbieter"][provider] = {
                    "status": "ok",
                    "anzahl_beispiele": len(candidates),
                    "kandidaten": candidates,
                }
            except (ValueError, TimeoutError, OSError, RuntimeError) as exc:
                entry["anbieter"][provider] = {
                    "status": "fehler",
                    "fehlerart": type(exc).__name__,
                    "kandidaten": [],
                }
            time.sleep(0.5)
        data.append(entry)
        print(f"Suche {query!r}: "
              f"iNaturalist={entry['anbieter']['inat']['status']}, "
              f"GBIF={entry['anbieter']['gbif']['status']}", flush=True)

    report = {
        "zeitpunkt_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hinweis": (
            "Taxonomische Vorschläge aus deutschen Suchbegriffen. "
            "Ein Gattungs-/Sammelbegriff beweist nicht die Pflanzenart. "
            "Die Nutzerin muss bei Mehrdeutigkeit die Art auswählen."
        ),
        "suchen": data,
    }
    (OUTPUT / "deutsche_namenssuche.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Mein Garten: echte Suche mit deutschen Pflanzennamen", "",
        "Nicht mit individueller Artverifikation gleichsetzen.", "",
    ]
    for query in data:
        lines += ["", "## " + query["suche"]]
        for provider in ("inat", "gbif"):
            result = query["anbieter"][provider]
            lines += [
                "", f"### {provider} – {result['status']}",
                "", "| Wiss. Name | Deutscher Name | Rang |", "|---|---|---|",
            ]
            for cand in result["kandidaten"]:
                lines.append(
                    f"| {cand['wissenschaftlich']} | {cand['deutscher_name']} | "
                    f"{cand['rang']} |"
                )
    (OUTPUT / "deutsche_namenssuche.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    if not any(
        v["status"] == "ok"
        for row in data for v in row["anbieter"].values()
    ):
        raise SystemExit("Keine Such-API antwortete erfolgreich.")


if __name__ == "__main__":
    run()
