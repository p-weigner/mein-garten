"""Offline-Prüfung des einzelnen Home-Assistant-Testskripts.

Verifiziert YAML, Jinja2-Templates und Datensparsamkeit mit simulierten
OpenPlantbook-Antworten. Kein Live-Test auf Home Assistant Green.
"""
import unittest
from pathlib import Path
import yaml
from jinja2 import Environment
from jinja2.nativetypes import NativeEnvironment

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "tests" / "manual" / "Mein_Garten_OpenPlantbook_Pflegepruefung.yaml"


class TestOPBPflegepruefung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = FILE.read_text(encoding="utf-8")
        cls.script = yaml.safe_load(cls.text)
        cls.repeat = cls.script["sequence"][1]["repeat"]
        cls.steps = cls.repeat["sequence"]
        cls.environment = Environment()
        cls.native = NativeEnvironment()

    def test_yaml_ist_eine_einzelne_skriptdefinition(self):
        self.assertIsInstance(self.script, dict)
        self.assertEqual(self.script["mode"], "single")
        self.assertIn("sequence", self.script)
        self.assertIn("alias", self.script)
        self.assertNotIn("script", self.script)

    def test_testarten_kategorien(self):
        arten = self.script["sequence"][0]["variables"]["garten_testarten"]
        self.assertEqual(len(arten), 13)
        self.assertIn("Hydrangea macrophylla", arten)
        self.assertIn("Solanum lycopersicum", arten)
        self.assertIn("Monstera deliciosa", arten)

    def test_suche_und_detail_enthalten_care(self):
        self.assertEqual(self.steps[1]["action"], "openplantbook.search")
        self.assertEqual(self.steps[1]["response_variable"], "garten_suche")
        details = self.steps[3]["choose"][0]["sequence"][0]
        self.assertEqual(details["action"], "openplantbook.get")
        self.assertEqual(details["data"]["include"], "care")
        self.assertEqual(details["response_variable"], "garten_details")

    def test_exakte_art_findet_pid(self):
        t = self.steps[2]["variables"]["garten_pid"]
        result = self.environment.from_string(t).render(
            repeat={"item": "Hydrangea macrophylla"},
            garten_suche={
                "hydrangea paniculata": "Rispenhortensie",
                "hydrangea macrophylla": "Bauernhortensie",
            },
        )
        self.assertEqual(result, "hydrangea macrophylla")

    def test_andere_art_keine_uebernahme(self):
        t = self.steps[2]["variables"]["garten_pid"]
        result = self.environment.from_string(t).render(
            repeat={"item": "Hydrangea macrophylla"},
            garten_suche={"hydrangea paniculata": "Rispenhortensie"},
        )
        self.assertEqual(result, "")

    def test_hybrid_schreibweisen(self):
        t = self.steps[2]["variables"]["garten_pid"]
        result = self.environment.from_string(t).render(
            repeat={"item": "Fragaria x ananassa"},
            garten_suche={"fragaria × ananassa": "Erdbeere"},
        )
        self.assertEqual(result, "fragaria × ananassa")

    def test_pflegetexte_werden_nicht_in_report_uebernommen(self):
        t = self.steps[4]["variables"]["garten_ergebnis"]
        values = self.native.from_string(t).render(
            repeat={"item": "Hydrangea macrophylla"},
            garten_pid="hydrangea macrophylla",
            garten_suche={"hydrangea macrophylla": "Hydrangea"},
            garten_details={
                "pid": "hydrangea macrophylla",
                "watering": "Water regularly",
                "sunlight": "Partial shade",
                "soil": "Moist soil",
                "pruning": "Avoid severe cuts",
                "fertilization": "Fertilize moderately",
            },
        )
        self.assertIsInstance(values, dict)
        self.assertEqual(values["suchtreffer"], 1)
        self.assertTrue(values["profil"])
        self.assertEqual(values["schnitt"], len("Avoid severe cuts"))
        self.assertEqual(values["duengung"], len("Fertilize moderately"))
        self.assertNotIn("Avoid severe cuts", str(values))
        self.assertNotIn("Water regularly", str(values))

    def test_kein_treffer_ergibt_keine_profildaten(self):
        t = self.steps[4]["variables"]["garten_ergebnis"]
        values = self.native.from_string(t).render(
            repeat={"item": "Hydrangea macrophylla"},
            garten_pid="",
            garten_suche={},
            garten_details={},
        )
        self.assertFalse(values["profil"])
        self.assertEqual(values["schnitt"], 0)

    def test_nachricht_zeigt_nur_metadaten(self):
        report = self.script["sequence"][2]["variables"]["garten_bericht"]
        rendered = self.environment.from_string(report).render(
            garten_ergebnisse=[{
                "art": "Hydrangea macrophylla",
                "suchtreffer": 1,
                "pid": "hydrangea macrophylla",
                "profil": True,
                "wasser": 15, "licht": 13, "boden": 10,
                "schnitt": 17, "duengung": 20,
            }]
        )
        self.assertIn("Hydrangea macrophylla", rendered)
        self.assertIn("Schnitt", rendered)
        self.assertIn("Düngung", rendered)
        self.assertNotIn("Water regularly", rendered)

    def test_keine_upload_aktion_und_keine_geheimnisse(self):
        self.assertNotIn("openplantbook.upload", self.text)
        for verboten in ("client_secret", "api_key", "password:", "notify."):
            self.assertNotIn(verboten, self.text)

    def test_ergebnis_in_persistent_notification_und_response(self):
        self.assertEqual(
            self.script["sequence"][3]["action"],
            "persistent_notification.create",
        )
        self.assertEqual(
            self.script["sequence"][-1]["response_variable"],
            "garten_antwort",
        )


if __name__ == "__main__":
    unittest.main()
