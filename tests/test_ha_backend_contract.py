import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "custom_components" / "mein_garten"


class TestHomeAssistantIntegrationContract(unittest.TestCase):
    def test_manifest_valid(self):
        data = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(data["domain"], "mein_garten")
        self.assertTrue(data["config_flow"])
        self.assertEqual(data["requirements"], [])
        self.assertIn("websocket_api", data["dependencies"])

    def test_strings_valid_und_deutsch(self):
        content = json.loads((BASE / "translations" / "de.json").read_text(
            encoding="utf-8"
        ))
        self.assertEqual(content["title"], "Mein Garten")
        self.assertIn("Pflanzen", content["config"]["step"]["user"]["description"])

    def test_alle_python_module_syntaktisch_korrekt(self):
        for path in BASE.glob("*.py"):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_backend_hat_sicheren_local_store(self):
        init = (BASE / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("GartenDaten", init)
        self.assertIn("self._store.async_save", init)
        self.assertIn("asyncio.Lock", init)
        self.assertIn("neuer_stand = GartenDaten(self._modell.snapshot())", init)
        self.assertNotIn("http://", init)
        self.assertNotIn("https://", init)

    def test_ws_alle_datenoperationen_und_subscriptions(self):
        source = (BASE / "api.py").read_text(encoding="utf-8")
        for name in (
            "mein_garten/get", "mein_garten/subscribe",
            "mein_garten/bereich_anlegen",
            "mein_garten/bereich_umbenennen",
            "mein_garten/bereich_entfernen",
            "mein_garten/pflanze_anlegen",
            "mein_garten/pflanze_bearbeiten",
            "mein_garten/pflanze_entfernen",
            "mein_garten/beobachtung_anlegen",
            "mein_garten/beobachtung_entfernen",
            "mein_garten/aufgabe_anlegen",
            "mein_garten/aufgabe_erledigen",
            "mein_garten/aufgabe_wieder_oeffnen",
            "mein_garten/aufgabe_entfernen",
        ):
            with self.subTest(name=name):
                self.assertIn(name, source)

    def test_keine_bisherigen_ha_dashboards_oder_api_credentials(self):
        for path in BASE.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in (".py", ".json"):
                continue
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("title: Zuhause", content)
            self.assertNotIn("notify.iphone_von_patrick", content)
            self.assertNotIn("AZURE_TRANSLATOR_KEY", content)
            self.assertNotIn("PERMAPEOPLE_KEY_SECRET", content)


if __name__ == "__main__":
    unittest.main()
