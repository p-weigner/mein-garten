"""Offline-Regression für das installierbare, aber noch nicht freigegebene Alpha-Paket."""
from __future__ import annotations

from pathlib import Path
from shutil import copytree, copy2
import json
import tempfile
import unittest
from unittest.mock import patch

from qa.validate_alpha_package import PaketFehler, validiere_paket


class TestAlphaPaket(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        base = Path(self.work.name)
        self.root = base / "repository"
        self.package = self.root / "paket"
        self.src = self.root / "custom_components" / "mein_garten"
        self.src.mkdir(parents=True)
        self._write(self.src / "__init__.py",
                    'RESOURCE = "/api/mein_garten/mein-garten-v1-card.js"\n')
        self._write(self.src / "api.py", "# API\n")
        self._write(self.src / "config_flow.py", "# Flow\n")
        self._write(self.src / "const.py", "# Const\n")
        self._write(self.src / "frontend/mein-garten-card.js",
                    'customElements.define("mein-garten-v1-card", class {});\n')
        self._write(self.src / "data/eive_europa_ccby_v1.json.gz.b64", "AA==\n")
        self._write(self.src / "manifest.json", json.dumps({
            "domain": "mein_garten",
            "version": "1.0.0b3",
            "config_flow": True,
            "requirements": [],
        }))
        self._write(self.root / "frontend/mein-garten-card.js",
                    (self.src / "frontend/mein-garten-card.js").read_text())
        self._write(self.root / "frontend/dashboard-mein-garten.yaml",
                    "title: Mein Garten\nviews:\n  - title: Mein Garten\n"
                    "    cards:\n      - type: custom:mein-garten-v1-card\n")
        self._write(self.root / "docs/ALPHA_INSTALLATION.md", "# Testanleitung\n")
        self._write(self.root / "hacs.json", '{"name":"Mein Garten"}\n')
        (self.package / "custom_components").mkdir(parents=True)
        copytree(self.src, self.package / "custom_components/mein_garten")
        self._copy("frontend/dashboard-mein-garten.yaml", "Mein_Garten_Dashboard.yaml")
        self._copy("docs/ALPHA_INSTALLATION.md", "ANLEITUNG.md")
        self._copy("hacs.json", "hacs.json")
        self._write(self.package / "STATUS.txt",
                    "TECHNISCHER ALPHA-TEST - NICHT DIE FERTIGE V1\n")

    @staticmethod
    def _write(path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _copy(self, source: str, target: str):
        copy2(self.root / source, self.package / target)

    def test_gueltiger_belegter_paketstand(self):
        report = validiere_paket(self.package, self.root)
        self.assertEqual(report["integrationsdomain"], "mein_garten")
        self.assertEqual(report["manifest_version"], "1.0.0b3")
        self.assertEqual(report["status"], "ci_validiert_live_abnahme_ausstehend")
        self.assertFalse(report["home_assistant_green_installiert"])
        self.assertGreaterEqual(report["integration_dateien"], 7)
        self.assertEqual(len(report["frontend_sha256"]), 64)

    def test_abweichendes_javascript_darf_nicht_in_paket(self):
        f = self.package / "custom_components/mein_garten/frontend/mein-garten-card.js"
        f.write_text(f.read_text() + "\n// Falsche Version\n", encoding="utf-8")
        with self.assertRaisesRegex(PaketFehler, "weicht"):
            validiere_paket(self.package, self.root)

    def test_fehlende_lokale_europa_daten_stoppen(self):
        f = self.package / "custom_components/mein_garten/data/eive_europa_ccby_v1.json.gz.b64"
        f.unlink()
        with self.assertRaisesRegex(PaketFehler, "Integrationsdatei fehlt"):
            validiere_paket(self.package, self.root)

    def test_keine_fremde_dashboard_datei(self):
        f = self.package / "Mein_Garten_Dashboard.yaml"
        f.write_text("title: Zuhause\n", encoding="utf-8")
        with self.assertRaises(PaketFehler):
            validiere_paket(self.package, self.root)

    def test_alte_kartenregistrierung_ist_nicht_erlaubt(self):
        text = (self.src / "frontend/mein-garten-card.js").read_text()
        text += '\ncustomElements.define("mein-garten-card", class {});\n'
        self._write(self.src / "frontend/mein-garten-card.js", text)
        self._write(self.root / "frontend/mein-garten-card.js", text)
        self._write(self.package /
                    "custom_components/mein_garten/frontend/mein-garten-card.js", text)
        with self.assertRaisesRegex(PaketFehler, "überschreibt"):
            validiere_paket(self.package, self.root)

    def test_private_home_assistant_storage_wird_abgelehnt(self):
        self._write(self.package / "custom_components/mein_garten/.storage/private", "test")
        with self.assertRaisesRegex(PaketFehler, "Private"):
            validiere_paket(self.package, self.root)

    def test_private_configuration_yaml_wird_abgelehnt(self):
        self._write(self.package / "custom_components/mein_garten/configuration.yaml", "api: x")
        with self.assertRaisesRegex(PaketFehler, "Private"):
            validiere_paket(self.package, self.root)

    def test_schluesseldateien_werden_abgelehnt(self):
        self._write(self.package / "custom_components/mein_garten/secret.pem", "test")
        with self.assertRaisesRegex(PaketFehler, "Schlüsseldatei"):
            validiere_paket(self.package, self.root)

    def test_mischversion_des_manifests_wird_abgelehnt(self):
        f = self.package / "custom_components/mein_garten/manifest.json"
        body = json.loads(f.read_text())
        body["version"] = "1.0.0b2"
        self._write(f, json.dumps(body))
        with self.assertRaises(PaketFehler):
            validiere_paket(self.package, self.root)

    def test_installationsanleitung_muss_aus_diesem_commit_stammen(self):
        self._write(self.package / "ANLEITUNG.md", "# Veraltete Anleitung\n")
        with self.assertRaisesRegex(PaketFehler, "Anleitung"):
            validiere_paket(self.package, self.root)

    def test_keine_symlinks_im_paket(self):
        target = self.package / "custom_components/mein_garten/alias.txt"
        target.symlink_to("manifest.json")
        with self.assertRaisesRegex(PaketFehler, "Symbolische Links"):
            validiere_paket(self.package, self.root)

    def test_pr_head_sha_ist_nicht_der_temporare_github_merge_commit(self):
        pr_head = "a" * 40
        test_merge = "b" * 40
        with patch.dict("os.environ", {
            "GARTEN_SOURCE_COMMIT": pr_head,
            "GITHUB_SHA": test_merge,
        }):
            report = validiere_paket(self.package, self.root)
        self.assertEqual(report["ci_commit"], pr_head)
        self.assertEqual(report["ci_event_sha"], test_merge)
        self.assertNotEqual(report["ci_commit"], report["ci_event_sha"])

    def test_manipulierte_quellcommit_kennung_stoppt_auslieferung(self):
        with patch.dict("os.environ", {
            "GARTEN_SOURCE_COMMIT": "unbekannt",
            "GITHUB_SHA": "b" * 40,
        }):
            with self.assertRaisesRegex(PaketFehler, "Quell-Commit"):
                validiere_paket(self.package, self.root)

    def test_keine_fremde_hauptdatei_im_paket(self):
        self._write(self.package / "Zuhause.yaml", "title: Zuhause\n")
        with self.assertRaisesRegex(PaketFehler, "Hauptdatei"):
            validiere_paket(self.package, self.root)


if __name__ == "__main__":
    unittest.main()
