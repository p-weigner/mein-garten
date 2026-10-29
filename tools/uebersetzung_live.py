"""Echter Übersetzungs-Livetest mit selbst verfassten Sätzen, ohne Kontodaten.

Nur in GitHub Actions, keine Home-Assistant-Installation.
Die fünf synthetischen Beispielsätze sind von diesem Projekt verfasst.
Keine OpenPlantbook-/Permapeople-Texte und keine privaten Daten übertragen.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from tools.mymemory import MyMemoryUebersetzer, Tagesbudget

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "berichte"

EXAMPLES = [
    ("Wasser", "Water moderately and avoid waterlogging."),
    ("Standort", "The plant prefers partial shade and moist, well-drained soil."),
    ("Schnitt", "Do not prune in autumn because the flower buds develop on older wood."),
    ("Düngung", "Apply a little fertilizer in spring, but do not overfertilize."),
    ("Frost", "Protect the roots from severe frost and do not water frozen soil."),
]


def run():
    OUTPUT.mkdir(exist_ok=True)
    translate = MyMemoryUebersetzer(Tagesbudget(
        OUTPUT / ".mymemory_livetest_budget.json",
        limit=1200,
    ))
    results = []
    for category, english in EXAMPLES:
        try:
            german = translate(english)
            state = "antwort_vorhanden" if german.strip() and german.strip() != english else "nicht_uebersetzt"
            fail = None
        except (RuntimeError, ValueError, OSError, TimeoutError) as exc:
            german = ""
            state = "anbieterfehler"
            fail = type(exc).__name__
        results.append({
            "thema": category,
            "synthetischer_text_en": english,
            "antwort_de": german,
            "status": state,
            "fehlerklasse": fail,
        })
        # Den freien Gemeinschaftsdienst nicht unnötig belasten.
        print(f"{category}: {state} | {len(german)} deutsche Zeichen", flush=True)
        time.sleep(1.1)

    report = {
        "zeitpunkt_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dienst": "MyMemory, anonyme REST API, ohne Schlüssel",
        "quelle": "https://mymemory.translated.net/doc/spec.php",
        "nur_selbst_verfasste_beispiele": True,
        "ergebnisse": results,
        "eingeschaenkte_aussage": (
            "Ein positiver Status bestätigt API-Transport und eine anderssprachige Antwort. "
            "Er bestätigt NICHT die Übersetzungsqualität oder die fachliche Korrektheit. "
            "Für OpenPlantbook-Volltexte gelten eigene Nutzungsrechte."
        ),
    }
    (OUTPUT / "uebersetzung_livetest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Mein Garten – kostenloser Übersetzungslivetest",
        "",
        f"Zeitpunkt UTC: {report['zeitpunkt_utc']}",
        "Dienst: MyMemory ohne Konto und ohne Zugangsdaten",
        "",
        "> **Alle Beispielsätze sind eigens für den Test verfasst.**",
        "> Die Antwortqualität und Gärtnerei-Fachlichkeit müssen getrennt geprüft werden.",
    ]
    for row in results:
        lines.extend([
            "",
            f"## {row['thema']}",
            f"- Status: {row['status']}",
            f"- Englisch: {row['synthetischer_text_en']}",
            f"- Antwort Deutsch: {row['antwort_de'] or '(keine)'}",
        ])
    lines.extend([
        "",
        "## Datenschutz und Kosten",
        "",
        "Keine persönlichen Informationen oder fremden Pflegequellentexte übertragen.",
        "Dienst erfordert kein Konto; anonymes Limit 5.000 Zeichen/Tag und 500 Byte/Request.",
        "Eigenes Testbudget beträgt maximal 1.200 Zeichen/Tag. Anbieterlimits",
        "und Ausfälle können unabhängig von diesem Budget auftreten.",
        "Es gibt keinen automatischen Wechsel in einen kostenpflichtigen Tarif.",
        "",
    ])
    (OUTPUT / "uebersetzung_livetest.md").write_text("\n".join(lines), encoding="utf-8")
    (OUTPUT / ".mymemory_livetest_budget.json").unlink(missing_ok=True)
    if not any(r["status"] == "antwort_vorhanden" for r in results):
        raise SystemExit("Keine einzige bestätigte API-Übersetzungsantwort; Bericht im Artefakt.")
    print("Bericht erfolgreich erstellt.", flush=True)


if __name__ == "__main__":
    run()
