"""Quellen- und Lizenzprobe für europäische Standortindikatoren (EIVE 1.0).

Strikt getrennte Forschungsmessung im GitHub-Runner; KEIN Produktivimport,
keine direkten Abrufe auf Home Assistant Green, keine Kultur-/Pflegeanweisungen.
Weder Excel-Rohdaten noch aus ihnen erzeugte Einzelwerte werden publiziert.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
RECORD = "7534792"
METADATA_URL = f"https://zenodo.org/api/records/{RECORD}"
DATA_URL = (
    f"https://zenodo.org/records/{RECORD}/files/"
    "EIVE_Paper_1.0_SM_08.xlsx?download=1"
)
EXPECTED_MD5 = "0f0ce19cd2a781eeed027d8b0acadbcb"
EXPECTED_SIZE_MAX = 5_000_000
REQUIRED_LICENSE = "cc-by-4.0"
REPORT_FILE = ROOT / "berichte" / "eive_europa_quellenprobe_20261030.json"
DOI = "10.5281/zenodo.7534792"
SOURCE_PUBLICATION = "10.3897/VCS.98324"
_SENSITIVE = re.compile(r"(^|[^a-z])(?:username|token|password|secret|email)([^a-z]|$)", re.I)


def lizenz_id(metadata: dict) -> str:
    """Nur tatsächlich im Datensatz genannte Lizenz akzeptieren, keine Zenodo-Defaults."""
    if not isinstance(metadata, dict):
        raise ValueError("Zenodo-Metadaten haben kein Objektformat")
    body = metadata.get("metadata")
    if not isinstance(body, dict):
        raise ValueError("Zenodo-Metadaten fehlen")
    rights = body.get("rights")
    found = set()
    if isinstance(rights, list):
        for obj in rights:
            if isinstance(obj, dict):
                identifier = obj.get("id")
                if isinstance(identifier, str):
                    found.add(identifier.casefold().strip())
    license_entry = body.get("license")
    if isinstance(license_entry, dict):
        identifier = license_entry.get("id")
        if isinstance(identifier, str):
            found.add(identifier.casefold().strip())
    elif isinstance(license_entry, str):
        found.add(license_entry.casefold().strip())
    if found != {REQUIRED_LICENSE}:
        raise ValueError(
            "Kein eindeutig bestätigtes CC BY 4.0 im Quelldatensatz – "
            "Quellenimport aus Sicherheitsgründen gesperrt"
        )
    record_id = str(metadata.get("id"))
    if record_id != RECORD:
        raise ValueError("Zenodo-Datensatz-ID stimmt nicht überein")
    return REQUIRED_LICENSE


def bounded_download(url: str, limit: int) -> bytes:
    if not url.startswith("https://zenodo.org/"):
        raise ValueError("Nur der gepinnte Zenodo-Ursprung wird angefragt")
    req = urllib.request.Request(
        url, headers={
            "User-Agent": "MeinGarten-EIVE-Qualitaet/1.0 (github.com/p-weigner/mein-garten)",
            "Accept": "application/json" if "/api/" in url else "application/octet-stream",
        },
    )
    blocks, size = [], 0
    with urllib.request.urlopen(req, timeout=45) as resp:
        while True:
            chunk = resp.read(min(131072, limit + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError("Quellantwort überschreitet das feste Größenlimit")
            blocks.append(chunk)
    return b"".join(blocks)


def limited_value(cell: object) -> object:
    """Nur kurze öffentliche Schema-Beispiele – keine Rohtext-Dumps."""
    if isinstance(cell, str):
        cell = " ".join(cell.split())
        return cell[:90] if cell else None
    if isinstance(cell, (int, float, bool)):
        return cell
    return None


def workbook_preview(payload: bytes) -> list[dict]:
    """Read-only XLSX-Vorschau ohne Formeln, automatische Korrektur oder Export."""
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(payload), data_only=True, read_only=True)
    summary = []
    try:
        for sheet in book.worksheets[:12]:
            sheet.reset_dimensions()
            rows = []
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                rows.append([limited_value(x) for x in row[:15]])
                if i >= 5:
                    break
            summary.append({"blatt": sheet.title[:70], "anfang": rows})
    finally:
        book.close()
    if not summary:
        raise ValueError("EIVE-Arbeitsmappe ohne Tabellen")
    return summary


def main() -> None:
    metadata_bytes = bounded_download(METADATA_URL, 250_000)
    metadata = json.loads(metadata_bytes)
    licence = lizenz_id(metadata)
    binary = bounded_download(DATA_URL, EXPECTED_SIZE_MAX)
    md5 = hashlib.md5(binary).hexdigest()
    if md5 != EXPECTED_MD5:
        raise ValueError("EIVE-Originaldatei MD5 stimmt nicht; Abbruch")
    if not binary.startswith(b"PK\x03\x04"):
        raise ValueError("EIVE-Datei ist keine XLSX-ZIP-Datei")
    sheets = workbook_preview(binary)
    report = {
        "status": "quellenprobe_keine_produktivfreigabe",
        "quelle": "Ecological Indicator Values for Europe (EIVE) 1.0",
        "record_id": RECORD,
        "doi": DOI,
        "publikation_doi": SOURCE_PUBLICATION,
        "lizenz_im_zenodo_datensatz": licence,
        "datei": "EIVE_Paper_1.0_SM_08.xlsx",
        "datei_md5": md5,
        "datei_bytes": len(binary),
        "sheets": sheets,
        "pflegeaufgaben_freigegeben": 0,
        "einschraenkung": (
            "Ökologische Pflanzen-Nischenwerte sind weder Gartenpflegeanleitungen "
            "noch regionale Schnitt-/Dünge-/Gießtermine; zunächst Schema und "
            "taxonomische Eindeutigkeit auswerten."
        ),
    }
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("EIVE_QUELLENPROBE", json.dumps({
        k: v for k, v in report.items() if k != "sheets"
    }, ensure_ascii=False), flush=True)
    for item in sheets:
        print("EIVE_SCHEMA", json.dumps(item, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
