"""Isolierte Datenqualitätsmessung für den CC0-Saisonkatalog.

Nur GitHub Actions / Entwicklung, NIEMALS auf Home Assistant Green laden.
Datenbestand vollständig aus exaktem upstream Commit, nicht aktuellem main.
Es werden keine Pflanzenpflege-Anweisungen erstellt oder ausgeführt.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.request

UPSTREAM_COMMIT = "c6287784527ebb4162e242394ee08f46d338218b"
UPSTREAM_URL = (
    "https://raw.githubusercontent.com/cwfrazier1/openplantdb/"
    + UPSTREAM_COMMIT + "/data/plants.json"
)
MAX_BYTES = 90_000_000
BINOMIAL = re.compile(r"^[A-Z][A-Za-z-]+ [a-z-]+$")
METHODS = {"direct", "indoor-start", "transplant", "bulb", "tuber", "cutting", "division"}
ANCHORS = {"last_frost", "first_frost"}
ROOT = Path(__file__).resolve().parent.parent


def source() -> tuple[list[dict], str]:
    request = urllib.request.Request(
        UPSTREAM_URL,
        headers={"User-Agent": "MeinGarten-SourceAudit/1.0 (github.com/p-weigner/mein-garten)"},
    )
    with tempfile.TemporaryFile() as tmp:
        digest = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(request, timeout=100) as response:
            while True:
                block = response.read(256 * 1024)
                if not block:
                    break
                size += len(block)
                if size > MAX_BYTES:
                    raise ValueError("OpenPlantDB-Quelldatei überschreitet 90 MB")
                digest.update(block)
                tmp.write(block)
        tmp.seek(0)
        payload = json.load(tmp)
    if not isinstance(payload, list):
        raise ValueError("OpenPlantDB-Format nicht erkannt")
    return payload, digest.hexdigest()


def normal(record: dict) -> tuple[str, tuple] | None:
    if not isinstance(record, dict):
        return None
    name = record.get("scientific_name")
    planting = record.get("planting")
    method = record.get("sow_method")
    if not isinstance(name, str) or not BINOMIAL.fullmatch(name):
        return None
    if not isinstance(planting, dict):
        return None
    weeks = planting.get("weeks_from_anchor")
    anchor = planting.get("anchor")
    if (anchor not in ANCHORS or not isinstance(weeks, dict)
            or type(weeks.get("min")) is not int
            or type(weeks.get("max")) is not int
            or not -24 <= weeks["min"] <= weeks["max"] <= 24
            or method not in METHODS):
        return None
    species = " ".join(name.split()).casefold()
    window = (anchor, weeks["min"], weeks["max"], method)
    return species, window


def evaluate(payload: list[dict]) -> dict:
    benchmark = json.loads(
        (ROOT / "daten" / "pflanzensuche_50_de.json").read_text(encoding="utf-8")
    )
    by_species = defaultdict(list)
    rejected = Counter()
    categories = Counter()
    for item in payload:
        x = normal(item)
        if x is None:
            rejected["nicht_geeignet"] += 1
            continue
        species, window = x
        by_species[species].append((window, item))
    selected = {}
    conflicts = {}
    for species, rows in by_species.items():
        windows = {x[0] for x in rows}
        if len(windows) != 1:
            conflicts[species] = {
                "anzahl": len(rows), "verschiedene_fenster": len(windows),
                "fenster_auszug": [list(w) for w in sorted(windows)[:3]],
            }
            continue
        window = next(iter(windows))
        slugs = sorted({x[1].get("slug", "") for x in rows if isinstance(x[1].get("slug"), str)})
        selected[species] = {
            "scientific_name": rows[0][1]["scientific_name"],
            "window": list(window),
            "rows": len(rows),
            "example_slug": slugs[0] if slugs else "",
            "category": rows[0][1].get("category", ""),
        }
        categories[rows[0][1].get("category", "unbekannt")] += 1

    baseline = json.loads(
        (ROOT / "custom_components" / "mein_garten" / "data" /
         "saison_openplantdb_v0_1.json").read_text(encoding="utf-8")
    )
    old_names = {
        r["wissenschaftlich"].casefold() for r in baseline["regeln"]
    }
    cases = []
    for plant in benchmark:
        key = plant["wissenschaftlich"].casefold()
        status = (
            "eindeutig" if key in selected else
            "widerspruechlich" if key in conflicts else "kein_frostfenster"
        )
        cases.append({
            "gruppe": plant["gruppe"], "name_de": plant["name_de"],
            "wissenschaftlich": plant["wissenschaftlich"],
            "vorher": key in old_names,
            "ergebnis": status,
            "fenster": selected[key]["window"] if key in selected else None,
            "varianten": conflicts[key] if key in conflicts else None,
        })
    return {
        "total": len(payload),
        "saisonfaehige_arten": len(selected),
        "arten_mit_widerspruch": len(conflicts),
        "kategorien": dict(categories),
        "verworfen": dict(rejected),
        "einzigartige_regeln": selected,
        "konflikte": conflicts,
        "benchmark": cases,
        "benchmark_eindeutig": sum(x["ergebnis"] == "eindeutig" for x in cases),
        "benchmark_alt": sum(x["vorher"] for x in cases),
        "benchmark_widerspruechlich": sum(x["ergebnis"] == "widerspruechlich" for x in cases),
    }


def main():
    payload, sha256 = source()
    result = evaluate(payload)
    print("QUELLE", json.dumps({
        "commit": UPSTREAM_COMMIT,
        "sha256": sha256,
        "eintraege": result["total"],
        "eindeutige_arten": result["saisonfaehige_arten"],
        "widerspruechliche_arten": result["arten_mit_widerspruch"],
        "kategorien": result["kategorien"],
        "benchmark_vorher": result["benchmark_alt"],
        "benchmark_eindeutig": result["benchmark_eindeutig"],
        "benchmark_widerspruechlich": result["benchmark_widerspruechlich"],
    }, ensure_ascii=False), flush=True)
    for item in result["benchmark"]:
        print("TESTART", json.dumps(item, ensure_ascii=False), flush=True)
    # Für Audit/Artefakte nur kleine Zusammenfassung, niemals gesamte Rohdatei.
    report = {
        k: v for k, v in result.items()
        if k not in ("einzigartige_regeln", "konflikte")
    }
    report["commit"] = UPSTREAM_COMMIT
    report["sha256"] = sha256
    out = ROOT / "berichte"
    out.mkdir(parents=True, exist_ok=True)
    (out / "saison_quellcheck_20261030.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
