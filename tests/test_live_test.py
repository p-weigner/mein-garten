import unittest
from unittest.mock import patch
from tools.live_test import norm, exact, hybrid_variante, check_gbif, check_inat


class TestIdentitaet(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(exact("Hydrangea macrophylla","Hydrangea macrophylla","species"))

    def test_falsche_art(self):
        self.assertFalse(exact("Hydrangea paniculata","Hydrangea macrophylla","species"))

    def test_gattung_ist_nicht_art(self):
        self.assertFalse(exact("Hydrangea macrophylla","Hydrangea macrophylla","genus"))

    def test_hybrid(self):
        self.assertTrue(exact("Fragaria × ananassa","Fragaria x ananassa","species"))

    def test_hybrid_rank(self):
        self.assertTrue(exact("Citrus × limon","Citrus × limon","hybrid"))

    def test_hybrid_variante(self):
        self.assertTrue(hybrid_variante("Citrus limon","Citrus × limon"))
        self.assertTrue(hybrid_variante("Fragaria ananassa","Fragaria × ananassa"))

    def test_hybrid_keine_andere_art(self):
        self.assertFalse(hybrid_variante("Hydrangea paniculata","Hydrangea macrophylla"))
        self.assertFalse(hybrid_variante("Fragaria vesca","Fragaria × ananassa"))

    def test_hybrid_ohne_x_keine_variante(self):
        self.assertFalse(hybrid_variante("Hydrangea macrophylla","Hydrangea macrophylla"))

    def test_gbif_hybrid_100_prozent(self):
        with patch("tools.live_test.fetch", return_value={
            "matchType": "EXACT", "rank": "SPECIES", "confidence": 100,
            "canonicalName": "Citrus limon", "usageKey": 123
        }):
            self.assertEqual(check_gbif("Citrus × limon")["status"], "hybrid_schreibweise")

    def test_gbif_hybrid_niedrige_konfidenz(self):
        with patch("tools.live_test.fetch", return_value={
            "matchType": "FUZZY", "rank": "SPECIES", "confidence": 50,
            "canonicalName": "Citrus limon", "usageKey": 123
        }):
            self.assertEqual(check_gbif("Citrus × limon")["status"], "nicht_eindeutig")

    def test_inaturalist_hybrid(self):
        with patch("tools.live_test.fetch", return_value={
            "results": [{"name": "Citrus × limon", "rank": "hybrid", "id": 123}]
        }):
            self.assertEqual(check_inat("Citrus × limon")["status"], "exakt")

    def test_umlaute(self):
        self.assertEqual(norm("Grüne Pflanze"), "grüne pflanze")


if __name__ == "__main__":
    unittest.main()
