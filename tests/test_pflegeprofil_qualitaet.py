import json
import unittest
from tools.pflegeprofil_qualitaet import metadaten_profil, zusammenfassen


class TestPflegeprofilMetadaten(unittest.TestCase):
    def test_alle_attribute_statt_nur_adapter_felder(self):
        sample = {
            "scientific_name": "Hydrangea macrophylla",
            "description": "An example plant, but the original text must remain private.",
            "data": [
                {"key": "Light requirement", "value": "Partial sun/shade"},
                {"key": "Water requirement", "value": "Moist"},
                {"key": "Pruning", "value": "Do not cut old wood"},
                {"key": "Fertilizer", "value": "Use balanced fertilizer"},
                {"key": "Sowing season", "value": "Spring"},
            ],
        }
        meta = metadaten_profil(sample)
        self.assertEqual(meta["anzahl_attribute_mit_wert"], 5)
        self.assertTrue(meta["schnitt_als_strukturiertes_feld"])
        self.assertTrue(meta["duengung_als_strukturiertes_feld"])
        self.assertTrue(meta["saison_als_strukturiertes_feld"])
        self.assertGreater(meta["beschreibung_zeichen"], 0)
        public_json = json.dumps(meta)
        self.assertNotIn("Do not cut old wood", public_json)
        self.assertNotIn("Use balanced fertilizer", public_json)
        self.assertNotIn("original text must remain private", public_json)

    def test_keine_falsche_aussage_bei_nicht_vorhandenem_schnittfeld(self):
        meta = metadaten_profil({
            "description": "Some text could mention pruning, but no field exists.",
            "data": [
                {"key": "Water requirement", "value": "Dry"},
                {"key": "Soil type", "value": "Sandy"},
            ],
        })
        self.assertFalse(meta["schnitt_als_strukturiertes_feld"])
        self.assertFalse(meta["duengung_als_strukturiertes_feld"])
        self.assertTrue(meta["beschreibung_zeichen"] > 0)

    def test_ungueltige_attribute_abgelehnt(self):
        with self.assertRaises(ValueError):
            metadaten_profil({"data": {"Pruning": "yes"}})

    def test_wert_ist_leer_und_zaehlt_nicht(self):
        meta = metadaten_profil({"data": [{"key": "Water requirement", "value": ""}]})
        self.assertEqual(meta["anzahl_attribute_mit_wert"], 0)

    def test_schluessel_mit_zeilenumbruch_nicht_ausgegeben(self):
        meta = metadaten_profil({"data": [
            {"key": "Fake\nSECRET=example", "value": "anything"},
            {"key": "Light requirement", "value": "Full sun"},
        ]})
        self.assertEqual(meta["attributnamen_ohne_werte"], ["Light requirement"])

    def test_zusammenfassung(self):
        one = metadaten_profil({"data": [{"key": "Pruning", "value": "a"}], "description": "a"*220})
        two = metadaten_profil({"data": [{"key": "Pruning", "value": "b"}], "description": ""})
        result = zusammenfassen([
            {"api_metadaten": one}, {"api_metadaten": two}, {"api_metadaten": None},
        ])
        self.assertEqual(result["gepruefte_profile"], 2)
        self.assertEqual(result["strukturierte_schnittangaben"], 2)
        self.assertEqual(result["beschreibung_mehr_als_200_zeichen"], 1)
        self.assertEqual(result["api_attributnamen_haeufigkeit"]["Pruning"], 2)


if __name__ == "__main__":
    unittest.main()
