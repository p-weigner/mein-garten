"""Deterministischer CC0-Saisonkatalog aus einem festgehaltenen Quell-Commit.

Läuft ausschließlich in CI (niemals auf Home Assistant Green).
Verwirft Datensätze mit widersprüchlichen Saisonfenstern und schreibt keine
unbelegten artspezifischen Schnitt-/Düngearbeiten.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from tools.openplantdb_umfang_probe import (
    ROOT, UPSTREAM_COMMIT, normal, source,
)

EXPECTED_SHA256 = "aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751"
DESTINATION = (
    ROOT / "custom_components" / "mein_garten" / "data" /
    "saison_openplantdb_v0_2.json"
)
_MAX_RULES = 3000


def make_catalog(
    upstream_records: list[dict], baseline_records: list[dict],
) -> tuple[dict, dict]:
    """Exakte Art; nur wenn ALLE gültigen Varianten dieselbe Regel besitzen."""
    old = {r["wissenschaftlich"].casefold() for r in baseline_records}
    grouped = defaultdict(list)
    for entry in upstream_records:
        result = normal(entry)
        if result is not None:
            species, window = result
            grouped[species].append((window, entry))
    chosen = []
    rejected_conflict = 0
    already_supported = 0
    for key in sorted(grouped):
        entries = grouped[key]
        if key in old:
            already_supported += 1
            continue
        unique_windows = {w for w, _ in entries}
        if len(unique_windows) != 1:
            rejected_conflict += 1
            continue
        original = min(
            (r["scientific_name"] for _, r in entries),
            key=lambda name: (len(name), name),
        )
        canonical = " ".join(original.split())
        if not re.fullmatch(r"[A-Z][A-Za-z-]+ [a-z-]+", canonical):
            continue
        anchor, lo, hi, method = next(iter(unique_windows))
        rule_id = "opdb26-" + canonical.casefold().replace(" ", "-")
        if len(rule_id) > 100:
            continue
        category = next((r.get("category") for _, r in entries
                         if isinstance(r.get("category"), str)
                         and 0 < len(r["category"]) <= 48), "unbekannt")
        chosen.append({
            "id": rule_id,
            "wissenschaftlich": canonical,
            "gruppe": category,
            "anker": anchor,
            "wochen_von": lo,
            "wochen_bis": hi,
            "methode": method,
        })
    if not chosen or len(chosen) > _MAX_RULES:
        raise ValueError("Unerwartete Anzahl eindeutiger Saisonfenster")
    if len({r["id"] for r in chosen}) != len(chosen):
        raise ValueError("Doppelte Katalog-IDs")
    report = {
        "ausgangs_datensaetze": len(upstream_records),
        "bereits_im_basiskatalog": already_supported,
        "ausgeschlossene_arten_mit_widerspruch": rejected_conflict,
        "neue_eindeutige_arten": len(chosen),
    }
    return {
        "schema": 1,
        "quelle": "OpenPlantDB",
        "lizenz": "CC0 1.0",
        "ausgangs_commit": UPSTREAM_COMMIT,
        "quelle_sha256": EXPECTED_SHA256,
        "quelle_datei": "data/plants.json",
        "status": "unverbindliche_Planungshilfe",
        "regeln": chosen,
    }, report


def main() -> None:
    current, checksum = source()
    if checksum != EXPECTED_SHA256:
        raise ValueError("OpenPlantDB-Quellenhash abweichend; Import abgebrochen")
    baseline = json.loads((
        ROOT / "custom_components" / "mein_garten" / "data" /
        "saison_openplantdb_v0_1.json"
    ).read_text(encoding="utf-8"))
    compact, report = make_catalog(current, baseline["regeln"])
    text = json.dumps(compact, ensure_ascii=False, indent=2) + "\n"
    if len(text.encode("utf-8")) > 650_000:
        raise ValueError("Kompaktkatalog zu groß für Home Assistant Green")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(text, encoding="utf-8")

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print("KATALOG", json.dumps({
        **report, "byte": len(text.encode("utf-8")), "katalog_sha256": sha,
        "quelle_commit": UPSTREAM_COMMIT, "quelle_sha256": checksum,
    }, ensure_ascii=False), flush=True)
    # Ausgabe in 2.000-Zeichen-Paketen. Ein Assistenzwerkzeug kann diese
    # prüfen und in einen expliziten GitHub-CreatFile-Commit übertragen,
    # ohne Repository-Schreibrechte an GitHub Actions vergeben zu müssen.
    chunk_size = 1800
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    for i, chunk in enumerate(chunks):
        print(
            "CATPART|" + str(i) + "|" + str(len(chunks)) + "|" +
            json.dumps(chunk, ensure_ascii=True),
            flush=True,
        )


if __name__ == "__main__":
    main()
