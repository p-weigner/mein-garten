"""Sicherheits- und Reproduzierbarkeitsprüfung des Mein-Garten-Alpha-Pakets.

Nur lokale Dateien im CI-Workspace: kein Netzwerk, keine Schreiboperationen
an Home Assistant und keine Veröffentlichung privater Garten-/Zugangsdaten.
Der Prüfbericht ist ausdrücklich KEINE Live-Abnahme auf Home Assistant Green.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
RESOURCE = "/api/mein_garten/mein-garten-v1-card.js"
CARD_TYPE = "custom:mein-garten-v1-card"
MANIFEST_RE = re.compile(r"^1\.0\.0b[0-9]+$")
FORBIDDEN_NAMES = {
    ".env", ".storage", ".git", ".github", ".ssh", "__pycache__",
    "secrets.yaml", "known_devices.yaml", "configuration.yaml",
    "automations.yaml", "scripts.yaml", "scenes.yaml",
    "auth", "home-assistant_v2.db", "home-assistant.log",
    "zuhause.yaml", "ui-lovelace.yaml", "lovelace.yaml",
}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".key", ".pem", ".p12", ".pfx", ".sqlite", ".db")
REQUIRED_INTEGRATION = (
    "__init__.py", "api.py", "config_flow.py", "const.py", "manifest.json",
    "frontend/mein-garten-card.js", "data/eive_europa_ccby_v1.json.gz.b64",
)
REQUIRED_PACKAGE = (
    "ANLEITUNG.md", "STATUS.txt", "hacs.json", "Mein_Garten_Dashboard.yaml",
    "custom_components/mein_garten/manifest.json",
    "custom_components/mein_garten/frontend/mein-garten-card.js",
)
TOP_LEVEL = {
    "ANLEITUNG.md", "STATUS.txt", "hacs.json", "Mein_Garten_Dashboard.yaml",
    "custom_components",
}


class PaketFehler(ValueError):
    """Alpha-Paket nicht freigeben; vorher Quelle oder Paket korrigieren."""


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sicherer_baum(package: Path) -> int:
    """Keine Benutzerkonfiguration, Verknüpfungen, Backups oder Geheimdateien."""
    if not package.is_dir() or package.is_symlink():
        raise PaketFehler("Paketordner fehlt oder ist eine Verknüpfung")
    all_entries = list(package.rglob("*"))
    if len(all_entries) > 300:
        raise PaketFehler("Paket enthält unerwartet viele Dateien")
    for entry in all_entries:
        rel = entry.relative_to(package)
        if entry.is_symlink():
            raise PaketFehler("Symbolische Links sind im Alpha-Paket verboten")
        if any(part.lower() in FORBIDDEN_NAMES for part in rel.parts):
            raise PaketFehler("Private Konfigurations- oder Hilfsdatei im Paket")
        if entry.is_file():
            if entry.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise PaketFehler("Unzulässige Binär-, Backup- oder Schlüsseldatei")
            if entry.stat().st_size > 2_500_000:
                raise PaketFehler("Unerwartet große Einzeldatei im Paket")
    if {p.name for p in package.iterdir()} != TOP_LEVEL:
        raise PaketFehler("Unerwartete Hauptdatei oder fehlende Paketdatei")
    if {p.name for p in (package / "custom_components").iterdir()} != {"mein_garten"}:
        raise PaketFehler("Paket enthält fremde Home-Assistant-Integrationen")
    return sum(p.is_file() for p in all_entries)


def validiere_paket(package: Path, repo: Path) -> dict:
    """Gibt einen frei teilbaren Hash-Bericht zurück oder stoppt strikt."""
    package, repo = Path(package), Path(repo)
    count = _sicherer_baum(package)
    for item in REQUIRED_PACKAGE:
        if not (package / item).is_file():
            raise PaketFehler("Pflichtbestandteil fehlt: " + item)
    integration = package / "custom_components" / "mein_garten"
    origin = repo / "custom_components" / "mein_garten"
    for item in REQUIRED_INTEGRATION:
        if not (integration / item).is_file():
            raise PaketFehler("Integrationsdatei fehlt: " + item)
        if not (origin / item).is_file():
            raise PaketFehler("Quellendatei fehlt: " + item)

    # Der Paketbau kopiert den vollständigen Integrationsbaum, keine alten
    # oder unvollständigen Mischversionen dürfen neben den Quellen liegen.
    source_files = sorted(
        p.relative_to(origin).as_posix()
        for p in origin.rglob("*") if p.is_file()
        and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
    copied_files = sorted(
        p.relative_to(integration).as_posix()
        for p in integration.rglob("*") if p.is_file()
    )
    if source_files != copied_files:
        raise PaketFehler("Paket und Integrations-Quellverzeichnis unterscheiden sich")
    for item in source_files:
        if digest((origin / item).read_bytes()) != digest((integration / item).read_bytes()):
            raise PaketFehler("Paketdatei weicht von der Quelle ab: " + item)

    source_frontend = repo / "frontend" / "mein-garten-card.js"
    frontend = integration / "frontend" / "mein-garten-card.js"
    if not source_frontend.is_file() or frontend.read_bytes() != source_frontend.read_bytes():
        raise PaketFehler("Frontend-Dateien stimmen nicht bytegenau überein")
    source_dashboard = repo / "frontend" / "dashboard-mein-garten.yaml"
    target_dashboard = package / "Mein_Garten_Dashboard.yaml"
    if not source_dashboard.is_file() or target_dashboard.read_bytes() != source_dashboard.read_bytes():
        raise PaketFehler("Dashboard-YAML stimmt nicht mit der Quelle überein")
    dashboard = target_dashboard.read_text(encoding="utf-8")
    if dashboard.count("type: " + CARD_TYPE) != 1 or "type: custom:mein-garten-card" in dashboard:
        raise PaketFehler("Dashboard referenziert nicht eindeutig die neue Gartenkarte")
    if "title: Mein Garten" not in dashboard or "title: Zuhause" in dashboard:
        raise PaketFehler("Dashboard könnte ein anderes Dashboard überschreiben")

    readme = repo / "docs" / "ALPHA_INSTALLATION.md"
    if not readme.is_file() or (package / "ANLEITUNG.md").read_bytes() != readme.read_bytes():
        raise PaketFehler("Paket-Anleitung nicht auf dem aktuellen Entwicklungsstand")
    origin_hacs = repo / "hacs.json"
    if not origin_hacs.is_file() or (package / "hacs.json").read_bytes() != origin_hacs.read_bytes():
        raise PaketFehler("HACS-Metadaten weichen von der Quelle ab")

    try:
        manifest = json.loads((integration / "manifest.json").read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise PaketFehler("HA-Manifest ist nicht lesbar") from exc
    version = manifest.get("version")
    if (manifest.get("domain") != "mein_garten" or
        not isinstance(version, str) or not MANIFEST_RE.fullmatch(version) or
        manifest.get("config_flow") is not True or
        manifest.get("requirements") != []):
        raise PaketFehler("Unerwartete Manifestversion, Domain oder Abhängigkeit")

    init_code = (integration / "__init__.py").read_text(encoding="utf-8")
    frontend_code = frontend.read_text(encoding="utf-8")
    if RESOURCE not in init_code or "mein-garten-v1-card" not in frontend_code:
        raise PaketFehler("Integration registriert nicht die eindeutige V1-Ressource")
    if "customElements.define(\"mein-garten-card\"" in frontend_code:
        raise PaketFehler("Neue Gartenkarte überschreibt den bisherigen Kartennamen")
    status = (package / "STATUS.txt").read_text(encoding="utf-8")
    if "NICHT DIE FERTIGE V1" not in status:
        raise PaketFehler("Alpha-Warnung fehlt")

    source_commit = os.environ.get("GARTEN_SOURCE_COMMIT") or os.environ.get("GITHUB_SHA", "")
    if source_commit and not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise PaketFehler("Quell-Commit ist kein vollständiger Git-SHA")
    if os.environ.get("GITHUB_ACTIONS") == "true" and not source_commit:
        raise PaketFehler("GitHub-Lauf ohne eindeutigen Quell-Commit")

    return {
        "art": "Mein Garten – Integritätsprüfung Alpha-Testpaket",
        "status": "ci_validiert_live_abnahme_ausstehend",
        "home_assistant_green_installiert": False,
        "zuhause_dashboard_im_paket": False,
        "zuhause_live_zustand_geprueft": False,
        "integrationsdomain": "mein_garten",
        "manifest_version": version,
        "kartentyp": CARD_TYPE,
        "js_ressource": RESOURCE,
        "anzahl_dateien": count,
        "integration_dateien": len(source_files),
        "frontend_sha256": digest(frontend.read_bytes()),
        "dashboard_sha256": digest(target_dashboard.read_bytes()),
        "manifest_sha256": digest((integration / "manifest.json").read_bytes()),
        "anleitung_sha256": digest((package / "ANLEITUNG.md").read_bytes()),
        # Auf pull_request ist GITHUB_SHA der temporäre Merge-Commit.
        # Die auszuliefernden Quellen müssen eindeutig auf die PR-HEAD-SHA
        # zurückführbar sein – niemals den Merge-SHA als PR-HEAD ausgeben.
        "ci_commit": source_commit,
        "ci_event_sha": os.environ.get("GITHUB_SHA", ""),
        "pruefhinweis": "Paketintegrität ist keine Home-Assistant-Laufzeitprüfung.",
    }


def main() -> None:
    report = validiere_paket(ROOT / "paket", ROOT)
    # Der Bericht ist bewusst innerhalb des später hochgeladenen Pakets.
    dest = ROOT / "paket" / "ABNAHME.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ALPHA_PAKET_GEPRUEFT", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
