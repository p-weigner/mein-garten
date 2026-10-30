"""Live-Breitenprüfung: aktuelle Gartensuche gegen 50 deutsche Pflanzennamen.

Nur öffentliche Pflanzennamen und Taxonzuordnungen; weder private Garten-
daten noch Pflegetexte. Kein starres Artenverzeichnis in der Anwendung:
die Benchmarkliste liegt ausschließlich im Verzeichnis daten/.

Der Bericht ist eine Diagnostik, kein Beweis für fachliche Qualität oder
Vollständigkeit der Datenquellen. Falsche Synonyme werden NICHT still
als Treffer gezählt.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error

from qa.run_backend_unit_tests import _bootstrap_stub

_bootstrap_stub()
from custom_components.mein_garten.search import Pflanzensuche, _norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PLANTS = ROOT / "daten" / "pflanzensuche_50_de.json"
OUT = ROOT / "berichte"
MAX_RESPONSE = 1_000_000
QUERY_DELAY = 0.7
USER_AGENT = "MeinGarten-GermanGardenAudit/1.0 (github.com/p-weigner/mein-garten; noncommercial)"


def _get_json(url: str, params: dict) -> object:
    encoded = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        encoded,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=11) as response:
        content = response.read(MAX_RESPONSE + 1)
    if len(content) > MAX_RESPONSE:
        raise ValueError("Öffentliche API-Antwort zu groß")
    return json.loads(content)


class BenchmarkSuche(Pflanzensuche):
    async def _json(self, url: str, **params):
        return await asyncio.to_thread(_get_json, url, params)


def _fakten(report: list[dict]) -> dict:
    counts = Counter(v["status"] for v in report)
    groups = {}
    for name in sorted({r["gruppe"] for r in report}):
        subset = [r for r in report if r["gruppe"] == name]
        groups[name] = {
            "gesamt": len(subset),
            "exakt_in_top15": sum(x["status"] in ("top1_exakt", "top15_exakt")
                                  for x in subset),
            "top1_exakt": sum(x["status"] == "top1_exakt" for x in subset),
            "nicht_exakt": sum(x["status"] not in ("top1_exakt", "top15_exakt")
                               for x in subset),
        }
    return {"statusanzahl": dict(counts), "gruppen": groups}


async def run():
    candidates = json.loads(PLANTS.read_text(encoding="utf-8"))
    if not isinstance(candidates, list) or len(candidates) != 50:
        raise ValueError("Benchmark benötigt exakt 50 Arten")
    audit = BenchmarkSuche(object())
    report = []
    for i, plant in enumerate(candidates, 1):
        expected = plant["wissenschaftlich"]
        name = plant["name_de"]
        try:
            result = await audit.async_suchen(name)
            suggestions = result.get("pflanzen", [])
            matched = [
                rank + 1 for rank, candidate in enumerate(suggestions)
                if _norm(candidate["wissenschaftlich"]) == _norm(expected)
            ]
            status = ("top1_exakt" if matched and matched[0] == 1
                      else "top15_exakt" if matched else "nicht_exakt_gefunden")
            record = {
                "gruppe": plant["gruppe"],
                "name_de": name,
                "erwartete_art": expected,
                "status": status,
                "trefferposition": matched[0] if matched else None,
                "angezeigte_treffer": len(suggestions),
                "erster_vorschlag": suggestions[0].get("wissenschaftlich") if suggestions else None,
                "quellenstatus": result.get("quellenstatus", []),
            }
        except Exception as exc:
            record = {
                "gruppe": plant["gruppe"], "name_de": name,
                "erwartete_art": expected,
                "status": "technischer_fehler",
                "trefferposition": None, "angezeigte_treffer": 0,
                "erster_vorschlag": None,
                "quellenstatus": [type(exc).__name__],
            }
        report.append(record)
        print(f"{i:02}/50 {name:28} {record['status']:22} "
              f"{record['erster_vorschlag']}", flush=True)
        await asyncio.sleep(QUERY_DELAY)

    OUT.mkdir(exist_ok=True)
    summary = _fakten(report)
    data = {
        "zeitpunkt_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hinweis": (
            "Der Benchmark vergleicht einen erwarteten botanischen Namen mit "
            "den maximal 15 tatsächlich angebotenen Ergebnissen. Synonyme, "
            "Sorten und wissenschaftlich nicht eindeutige Trivialnamen können "
            "abweichende, durchaus sinnvolle Ergebnisse liefern. "
            "Keine automatische Verwechslung oder Pflegefreigabe."
        ),
        "messung": summary,
        "arten": report,
    }
    (OUT / "pflanzensuche_50_de.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Mein Garten – 50 deutsche Gartenpflanzen: echter Suchtest",
        "",
        "**Nur Suchabdeckung, keine fachliche Pflegefreigabe.**",
        f"Zeitpunkt (UTC): {data['zeitpunkt_utc']}",
        "",
        "## Ergebnis je Pflanzengruppe",
        "",
        "| Gruppe | Testfälle | Exakt in Top 15 | Rang 1 exakt | Nicht exakt |",
        "|---|---:|---:|---:|---:|",
    ]
    for group, d in summary["gruppen"].items():
        lines.append(
            f"| {group} | {d['gesamt']} | {d['exakt_in_top15']} | "
            f"{d['top1_exakt']} | {d['nicht_exakt']} |"
        )
    lines += [
        "",
        "## Einzelne Suchfälle",
        "",
        "| Deutscher Name | Erwartete Art | Ergebnis | Vorschlag Rang 1 | API-Hinweise |",
        "|---|---|---|---|---|",
    ]
    for item in report:
        safe = lambda v: str(v or "–").replace("|", "/").replace("\n", " ")
        lines.append(
            f"| {safe(item['name_de'])} | {safe(item['erwartete_art'])} | "
            f"{safe(item['status'])} | {safe(item['erster_vorschlag'])} | "
            f"{safe(', '.join(item['quellenstatus']))} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Eine Fehlstelle beweist nicht, dass die Art weltweit nicht bekannt ist. Sie kann durch einen anderen deutschen Namen, ein botanisches Synonym, Anbieterfehler oder ein Ranking entstehen.",
        "- Kein Treffer wird künstlich ergänzt. Die Benchmarkliste wird nicht in den Produktiv-Suchalgorithmus eingebaut.",
        "- Unbestätigte oder alternative Arten dürfen keine automatischen Pflegeanweisungen auslösen.",
        "- Externe APIs sind freiwillig kostenlos und können Limits, Ausfälle oder geänderte Suchergebnisse haben.",
    ]
    (OUT / "pflanzensuche_50_de.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("ERGEBNIS", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(run())
