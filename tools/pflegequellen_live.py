"""Getrennter Live-Probelauf der Pflegequellen; schreibt keine Fachtexte in GitHub-Artefakte.

Nur bei manuellem GitHub-Actions-Start, Schlüssel ausschließlich aus Secrets.
Fehlende Zugangsdaten werden als 'nicht_getestet' gemeldet, nie als Erfolg.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from collections import Counter
from datetime import datetime, timezone

from tools.anbieter import permapeople_suche, AzureUebersetzer, Monatsbudget
from tools.pflegewissen import normalisiere_permapeople, ArtNichtPassend
from tools.pflegeprofil_qualitaet import metadaten_profil, zusammenfassen

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "berichte"


def run():
    pflanzen = json.loads((ROOT / "daten" / "testpflanzen.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    key_id = os.environ.get("PERMAPEOPLE_KEY_ID", "").strip()
    secret = os.environ.get("PERMAPEOPLE_KEY_SECRET", "").strip()
    bereit = bool(key_id and secret)
    counts = Counter()
    einzel = []
    for plant in pflanzen:
        name = plant["wissenschaftlich"]
        profil_metrik = None
        if not bereit:
            state = "nicht_getestet"
            fields = []
        else:
            try:
                found = permapeople_suche(name, key_id, secret)
                # Achtung: fehlerfreie Suche ohne Profil bleibt eine echte Lücke.
                if not found:
                    state = "kein_exakter_treffer"
                    fields = []
                else:
                    records = normalisiere_permapeople(found[0], name)
                    profil_metrik = metadaten_profil(found[0])
                    fields = sorted({h.feld for h in records})
                    state = "exakt_mit_daten" if fields else "exakt_ohne_pflegedaten"
            except (ValueError, OSError, RuntimeError, TimeoutError, ArtNichtPassend):
                state = "anbieterfehler"
                fields = []
            time.sleep(0.3)
        counts[state] += 1
        einzel.append({"art": name, "status": state, "felder": fields, "api_metadaten": profil_metrik})
        print(f"Permapeople {name}: {state}, {len(fields)} zulässige Felder", flush=True)

    azure_key = os.environ.get("AZURE_TRANSLATOR_KEY", "").strip()
    region = os.environ.get("AZURE_TRANSLATOR_REGION", "").strip()
    translation = "nicht_getestet"
    if azure_key:
        try:
            budget = Monatsbudget(OUT / ".privates_testbudget.json", limit=100)
            # Eigener kurzer Prüfsatz, KEIN urheberrechtlich geschützter Pflegequelltext.
            result = AzureUebersetzer(azure_key, region, budget)(
                "This garden plant prefers partial shade and moist soil."
            )
            translation = "api_antwort_ok" if result.strip() else "anbieterfehler"
        except (ValueError, OSError, RuntimeError, TimeoutError):
            translation = "anbieterfehler"

    report = {
        "zeitpunkt_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gesamte_testarten": len(pflanzen),
        "permapeople_test_mit_credentials": bereit,
        "permapeople_statistik": dict(counts),
        "permapeople_einzel": einzel,
        "permapeople_metadaten": zusammenfassen(einzel),
        "azure_uebersetzung": translation,
        "openplantbook": "in_diesem_workflow_nicht_getestet_bestehende_HA_Integration",
        "recht": "Permapeople-Daten CC BY-SA 4.0; Originaltexte werden NICHT veröffentlicht.",
        "warnung": "Technischer API-Test, keine Prüfung medizinischer, gärtnerischer oder rechtlicher Zuverlässigkeit.",
    }
    (OUT / "pflegequellen.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    lines = [
        "# Mein Garten – Pflegequellen-Livetest", "",
        f"Zeitpunkt: {report['zeitpunkt_utc']}", "",
        f"Permapeople-Zugang: {'konfiguriert' if bereit else 'nicht konfiguriert'}",
        f"Azure Übersetzung: {translation}", "",
        "| Status | Anzahl |", "|---|---:|",
    ]
    for status, n in sorted(counts.items()):
        lines.append(f"| {status} | {n} |")
    lines += ["", "| Botanische Art | Status | Abrufbare Felder |", "|---|---|---|"]
    for plant in einzel:
        lines.append(f"| {plant['art']} | {plant['status']} | {', '.join(plant['felder']) or '–'} |")
    m = report["permapeople_metadaten"]
    lines += [
        "", "## Gesamter API-Datenbestand je gefundenem Profil (nur Metadaten)", "",
        f"- Ausgewertete API-Profile: {m['gepruefte_profile']}",
        f"- Profile mit Beschreibungstext: {m['beschreibung_vorhanden']}",
        f"- Profile mit Beschreibung länger als 200 Zeichen: {m['beschreibung_mehr_als_200_zeichen']}",
        f"- Eigene Schnitt-Feldnamen: {m['strukturierte_schnittangaben']}",
        f"- Eigene Dünge-Feldnamen: {m['strukturierte_duengeangaben']}",
        f"- Eigene Saison-Feldnamen: {m['strukturierte_saisonangaben']}",
        "", "| API-Attributname | Anzahl gefundener Profile |", "|---|---:|",
    ]
    for key, count in m["api_attributnamen_haeufigkeit"].items():
        lines.append(f"| {key} | {count} |")
    lines += ["", "## Inhaltslängen pro Pflanze (ohne Veröffentlichung der Texte)", "",
              "| Art | Attributanzahl | Beschreibung (Zeichen) |", "|---|---:|---:|"]
    for plant in einzel:
        meta = plant.get("api_metadaten")
        if meta is not None:
            lines.append(
                f"| {plant['art']} | {meta['anzahl_attribute_mit_wert']} | {meta['beschreibung_zeichen']} |"
            )
    lines += [
        "", "> **Wichtig:** Die ursprünglichen vier Felder stammen aus unserem "
        "Adapter, NICHT zwingend aus dem gesamten API-Datenbestand. Auch ein "
        "längerer Beschreibungstext bedeutet noch keine geprüfte Pflegeanleitung. "
        "Keine Originaltexte oder Geheimnisse im Bericht; fachliche Qualität noch ungeprüft."
    ]
    (OUT / "pflegequellen.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        (OUT / ".privates_testbudget.json").unlink(missing_ok=True)
    except OSError:
        pass
    print("Pflegequellen-Bericht geschrieben (keine API-Schlüssel oder Quelltexte enthalten).")


if __name__ == "__main__":
    run()
