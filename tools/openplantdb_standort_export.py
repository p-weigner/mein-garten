"""Erzeugt einen kompakten, prüfbaren CC0-Standortkatalog ohne Pflegefreitexte.

Die große OpenPlantDB-Quelldatei wird ausschließlich im GitHub-CI-Entwicklungs-
workflow heruntergeladen. Home Assistant Green bekommt nur den festen,
kleinen Offline-Snapshot und führt keinerlei Download aus.

Je botanischer Art und Merkmal werden alle gültigen Quellzeilen verglichen.
Unbekannte oder widersprüchliche Werte werden NICHT geraten/aufgelöst.
"""
from __future__ import annotations

from collections import defaultdict, Counter
import hashlib
import json
from pathlib import Path

from tools.openplantdb_umfang_probe import ROOT, UPSTREAM_COMMIT, source
from tools.openplantdb_standort_audit import BINOMIAL, TRAITS

SOURCE_SHA256 = "aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751"
FIELD_ORDER = ("sun", "water", "frost_tolerance", "season")
OUTPUT = ROOT / "custom_components" / "mein_garten" / "data" / "standort_cc0_v1.json"
LIMIT = 1_350_000


def make_dataset(
    records: list[dict], *, mindest_arten: int = 10_000,
    maximal_arten: int = 12_000,
) -> tuple[dict, dict]:
    group = defaultdict(list)
    for entry in records:
        if not isinstance(entry, dict):
            continue
        name = entry.get("scientific_name")
        if not isinstance(name, str) or not BINOMIAL.fullmatch(name):
            continue
        group[name.casefold()].append(entry)

    rows = []
    conflicts = Counter()
    missing = Counter()
    support = Counter()
    for scientific in sorted(group):
        source_rows = group[scientific]
        traits = []
        for key in FIELD_ORDER:
            values = set()
            malformed = False
            for entry in source_rows:
                value = entry.get(key)
                if isinstance(value, str) and value in TRAITS[key]:
                    values.add(value)
                elif value not in (None, ""):
                    malformed = True
            if malformed or len(values) > 1:
                traits.append(None)
                conflicts[key] += 1
            elif len(values) == 1:
                traits.append(next(iter(values)))
                support[key] += 1
            else:
                traits.append(None)
                missing[key] += 1
        if any(x is not None for x in traits):
            name = min(
                (record["scientific_name"] for record in source_rows),
                key=lambda s: (len(s), s),
            )
            rows.append([name, *traits])

    if not mindest_arten <= len(rows) <= maximal_arten:
        raise ValueError("Unerwartete Größe des konsistenten CC0-Standortkatalogs")
    if len({r[0].casefold() for r in rows}) != len(rows):
        raise ValueError("Doppelte Pflanzengattung/Artidentität")
    payload = {
        "schema": 1,
        "quelle": "OpenPlantDB",
        "lizenz": "CC0 1.0",
        "ausgangs_commit": UPSTREAM_COMMIT,
        "quelle_sha256": SOURCE_SHA256,
        "herkunft": "https://github.com/cwfrazier1/openplantdb/blob/" + UPSTREAM_COMMIT + "/data/plants.json",
        "pruefstatus": "unverbindliche_Quellkategorien",
        "felder": list(FIELD_ORDER),
        "arten": rows,
    }
    metrics = {
        "arten": len(rows),
        "merkmale": dict(support),
        "merkmale_ausgeschlossen_bei_widerspruch": dict(conflicts),
        "merkmale_ohne_quellenwert": dict(missing),
        "original_datensaetze": len(records),
    }
    return payload, metrics


def main():
    original, actual_hash = source()
    if actual_hash != SOURCE_SHA256:
        raise ValueError("OpenPlantDB SHA-256 abweichend: Import nicht erlaubt")
    payload, metrics = make_dataset(original)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(text.encode("utf-8")) > LIMIT:
        raise ValueError("CC0-Standortkatalog zu groß für Home Assistant Green")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print("STANDORT_KATALOG", json.dumps({
        **metrics,
        "byte": len(text.encode("utf-8")),
        "datei_sha256": checksum,
        "quelle_sha256": actual_hash,
        "quelle_commit": UPSTREAM_COMMIT,
    }, ensure_ascii=False), flush=True)
    # In transportierbare Teile für den GitHub-Connector aufteilen. Der
    # CI-Runner bekommt keine Schreibrechte auf die GitHub-Branch.
    chunks = [text[i:i + 1800] for i in range(0, len(text), 1800)]
    for i, chunk in enumerate(chunks):
        print("STANDORT_PART|" + str(i) + "|" + str(len(chunks)) + "|" +
              json.dumps(chunk, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
