"""Prüft freie deutsche Namen/Aliase mit Wikidata, nur öffentliche Taxondaten."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from tools.wikidata_namen import suchname_de

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "berichte"
SEARCH = ("Bauernhortensie", "Gartenhortensie", "Hortensie",
          "Echter Lavendel", "Tomate", "Rote Johannisbeere")

def run():
    OUT.mkdir(exist_ok=True)
    results=[]
    for term in SEARCH:
        try:
            candidates = suchname_de(term)
            status = "ok"
            error = ""
        except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
            candidates = []
            status = "fehler"
            error = type(exc).__name__
        results.append({
            "suchbegriff": term, "status": status,
            "kandidaten": candidates, "fehlerart": error,
        })
        print(f"{term}: {status} | " + str([
            (p["wissenschaftlich"], p["deutscher_treffer"], p["alias"])
            for p in candidates[:5]
        ]), flush=True)
        time.sleep(0.7)
    data={
        "zeitpunkt_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hinweis": "Taxonomische Kandidaten, keine automatische Zuordnung; P225 wurde geprüft.",
        "ergebnisse": results,
    }
    (OUT / "wikidata_namen.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines=["# Deutsche Pflanzensuche über Wikidata",
           "", "Öffentliche Namen und botanische P225-Taxa; keine Pflegeinformation.", ""]
    for r in results:
        lines += [f"## {r['suchbegriff']} ({r['status']})", "",
                  "| Botanische Bezeichnung | Name | Alias |",
                  "|---|---|---|"]
        for c in r["kandidaten"]:
            lines.append(
                f"| {c['wissenschaftlich']} | {c['deutscher_treffer']} | {c['alias']} |"
            )
    (OUT / "wikidata_namen.md").write_text("\n".join(lines), encoding="utf-8")
    if not any(row["status"]=="ok" for row in results):
        raise SystemExit("Wikidata aus GitHub Actions nicht erreichbar")

if __name__=="__main__":
    run()
