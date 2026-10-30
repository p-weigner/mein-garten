"""Audit: konsistente Standort-Merkmale aus CC0-OpenPlantDB.

Nur Forschungslauf in GitHub Actions. Echte Pflanzenarten werden dynamisch
aus dem festen Upstream-Commit ermittelt; keine Testpflanzen-Sonderregeln.
"""
from __future__ import annotations

from collections import defaultdict, Counter
import json
import re

from tools.openplantdb_umfang_probe import ROOT, source, UPSTREAM_COMMIT

TRAITS = {
    "sun": {"full", "partial", "shade"},
    "water": {"low", "moderate", "high"},
    "frost_tolerance": {"hardy", "half-hardy", "tender"},
    "season": {"cool", "warm", "perennial"},
}
BINOMIAL = re.compile(r"^[A-Z][A-Za-z-]+ [a-z-]+$")
REPORT = ROOT / "berichte" / "standort_merkmale_audit_20261030.json"


def assess(raw: list[dict]) -> dict:
    group = defaultdict(list)
    drop = Counter()
    for item in raw:
        if not isinstance(item, dict):
            drop["kein_record"] += 1
            continue
        name = item.get("scientific_name")
        if not isinstance(name, str) or not BINOMIAL.fullmatch(name):
            drop["kein_binom"] += 1
            continue
        group[name.casefold()].append(item)

    accepted = {}
    distinct = Counter()
    conflict = Counter()
    incomplete = Counter()
    for key, items in group.items():
        traits = {}
        for attr, enum in TRAITS.items():
            values = set()
            invalid = 0
            for item in items:
                val = item.get(attr)
                if isinstance(val, str) and val in enum:
                    values.add(val)
                elif val not in (None, ""):
                    invalid += 1
            if invalid or len(values) > 1:
                conflict[attr] += 1
            elif len(values) == 1:
                traits[attr] = next(iter(values))
                distinct[attr] += 1
            else:
                incomplete[attr] += 1
        if traits:
            accepted[key] = traits
    tests = json.loads((ROOT / "daten" / "pflanzensuche_50_de.json").read_text(encoding="utf-8"))
    statuses = []
    for t in tests:
        key = t["wissenschaftlich"].casefold()
        statuses.append({
            "name": t["name_de"],
            "art": t["wissenschaftlich"],
            "gruppe": t["gruppe"],
            "merkmale": accepted.get(key, {}),
            "quell_records": len(group.get(key, [])),
        })
    return {
        "source_commit": UPSTREAM_COMMIT,
        "total_records": len(raw),
        "exakte_binomina": len(group),
        "arten_mit_merkmalsfeld": len(accepted),
        "merkmalsabdeckung": dict(distinct),
        "merkmalswidersprueche": dict(conflict),
        "merkmale_fehlend": dict(incomplete),
        "verworfen": dict(drop),
        "test50_arten_mit_daten": sum(bool(x["merkmale"]) for x in statuses),
        "test50_mit_licht_und_wasser": sum(
            "sun" in x["merkmale"] and "water" in x["merkmale"]
            for x in statuses
        ),
        "test50": statuses,
    }


def main() -> None:
    upstream, sha256 = source()
    report = assess(upstream)
    report["sha256"] = sha256
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TRAITS_AUDIT", json.dumps({
        k: v for k,v in report.items() if k != "test50"
    }, ensure_ascii=False), flush=True)
    for x in report["test50"]:
        print("TRAITS_TEST", json.dumps(x, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
