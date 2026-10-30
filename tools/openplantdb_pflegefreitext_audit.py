"""Unabhängiger Qualitätscheck für CC0-Anbau-Freitexte – KEIN Produktivimport.

Untersucht den exakt gepinnten OpenPlantDB-Quellstand im GitHub-Runner,
niemals auf Home Assistant Green. Es entstehen keine Pflegeaufgaben,
keine Übersetzungen und keine ungeprüften Texte in der Benutzeroberfläche.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from tools.openplantdb_umfang_probe import ROOT, UPSTREAM_COMMIT, source

EXPECTED_SOURCE_SHA256 = (
    "aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751"
)
BINOMIAL = re.compile(r"^[A-Z][A-Za-z-]+ [a-z-]+$")
HTML = re.compile(r"<[/!]?[a-z][^>]*>", re.IGNORECASE)
US_CONTEXT = re.compile(
    r"\b(?:USDA|fahrenheit|inches?|zones?)\b|°\s*F", re.IGNORECASE
)
GENERIC_SOURCES = {"", "general horticultural reference", "horticultural reference"}
FIELDS = ("directions", "planting_note")
REPORT = ROOT / "berichte" / "anbauhinweise_qualitaet_20261030.json"


def _field(record: dict, field: str) -> object:
    if field == "planting_note":
        planting = record.get("planting")
        return planting.get("note") if isinstance(planting, dict) else None
    return record.get(field)


def _normal_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    val = " ".join(value.split())
    if not 40 <= len(val) <= 1600 or HTML.search(val):
        return None
    if any(ord(c) < 32 for c in val):
        return None
    return val


def _source_status(item: dict) -> str:
    sources = item.get("sources")
    if not isinstance(sources, list) or not sources:
        return "keine_konkrete_quelle"
    if not all(isinstance(s, str) and 1 <= len(s) <= 300 for s in sources):
        return "keine_konkrete_quelle"
    if all(s.strip().casefold() in GENERIC_SOURCES for s in sources):
        return "nur_allgemeiner_hinweis"
    # Auch ein Quellenname / Link allein belegt nicht die fachliche Qualität.
    return "konkretere_quellenangabe_zu_pruefen"


def bewerte(records: list[dict], benchmark: list[dict]) -> dict:
    """Messung je botanischer Art, streng ohne Gattungs- oder Sortenersatz.

    Bei divergierenden Sortenangaben, fehlenden Texten oder Quelle ohne
    Einzelbeleg findet keine automatische Fachfreigabe statt.
    """
    groups = defaultdict(list)
    excluded = Counter()
    for item in records:
        if not isinstance(item, dict):
            excluded["kein_objekt"] += 1
            continue
        name = item.get("scientific_name")
        if not isinstance(name, str) or not BINOMIAL.fullmatch(name):
            excluded["keine_exakte_art"] += 1
            continue
        groups[name.casefold()].append(item)

    field_counts = {key: Counter() for key in FIELDS}
    quality = Counter()
    result = {}
    for species, variants in groups.items():
        values = {}
        for field in FIELDS:
            normalized = [_normal_text(_field(item, field)) for item in variants]
            unique = {v for v in normalized if v is not None}
            if len(unique) > 1:
                state = "widerspruch"
            elif any(v is None for v in normalized):
                state = "lueckenhaft"
            elif len(unique) == 1:
                state = "einheitlich"
            else:
                state = "fehlt"
            field_counts[field][state] += 1
            if state == "einheitlich":
                text = next(iter(unique))
                values[field] = {
                    "status": state,
                    "zeichen": len(text),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "us_bezug": bool(US_CONTEXT.search(text)),
                }
            else:
                values[field] = {"status": state}
        sources = {_source_status(item) for item in variants}
        if sources == {"konkretere_quellenangabe_zu_pruefen"}:
            origin = "konkretere_quellenangabe_zu_pruefen"
        elif "keine_konkrete_quelle" in sources:
            origin = "keine_konkrete_quelle"
        else:
            origin = "nur_allgemeiner_hinweis"
        quality[origin] += 1
        result[species] = {
            "artenname": variants[0]["scientific_name"],
            "varianten": len(variants),
            "herkunft": origin,
            "felder": values,
            # Ein eindeutig gleicher Text ist weiterhin NICHT fachlich freigegeben.
            "fachlich_freigegeben": False,
        }

    examples = []
    for plant in benchmark:
        name = plant["wissenschaftlich"]
        info = result.get(name.casefold())
        examples.append({
            "name_de": plant["name_de"],
            "gruppe": plant["gruppe"],
            "wissenschaftlich": name,
            "varianten": info["varianten"] if info else 0,
            "herkunft": info["herkunft"] if info else "keine_daten",
            "directions": info["felder"]["directions"]["status"] if info else "fehlt",
            "planting_note": info["felder"]["planting_note"]["status"] if info else "fehlt",
            "fachlich_freigegeben": False,
        })
    return {
        "quelle": "OpenPlantDB",
        "lizenz": "CC0 1.0",
        "upstream_commit": UPSTREAM_COMMIT,
        "rohdatensaetze": len(records),
        "exakte_botanische_arten": len(groups),
        "ausgeschlossene_rohdatensaetze": dict(excluded),
        "felder": {k: dict(v) for k, v in field_counts.items()},
        "quellenqualitaet": dict(quality),
        "benchmark50": examples,
        "benchmark50_einheitliche_anbauhinweise": sum(
            x["directions"] == "einheitlich" for x in examples
        ),
        "benchmark50_einheitliche_pflanzhinweise": sum(
            x["planting_note"] == "einheitlich" for x in examples
        ),
        "automatische_pflegeaufgaben_freigegeben": 0,
    }


def main() -> None:
    original, digest = source()
    if digest != EXPECTED_SOURCE_SHA256:
        raise ValueError("OpenPlantDB-Originalhash stimmt nicht: Abbruch")
    benchmark = json.loads(
        (ROOT / "daten" / "pflanzensuche_50_de.json").read_text(encoding="utf-8")
    )
    report = bewerte(original, benchmark)
    report["quell_sha256"] = digest
    REPORT.parent.mkdir(exist_ok=True, parents=True)
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("PFLEGEFREITEXT_AUDIT", json.dumps({
        k: v for k, v in report.items() if k != "benchmark50"
    }, ensure_ascii=False), flush=True)
    for plant in report["benchmark50"]:
        print("PFLEGEFREITEXT_TEST", json.dumps(plant, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
