"""EIVE Offline-Export: unveränderliche Lizenz, Integrität und Schema."""
from __future__ import annotations
import base64
import gzip
import json
import unittest

from tools.eive_europa_export import produce_catalog, serialize_catalog, DIM


class TestEiveExport(unittest.TestCase):
    def test_spezies_und_quellenarten_werden_strikt_gefiltert(self):
        selected = {
            "rosa canina": {
                "art": "Rosa canina", "taxon_herkunft": "EuroMed",
                "felder": {"M": {"wert": 4.5, "systeme": 6},
                           "L": {"wert": 7.1, "systeme": 7}},
            },
            "rosa rugosa": {
                "art": "Rosa rugosa", "taxon_herkunft": "unresolved",
                "felder": {"M": {"wert": 2.8, "systeme": 1}},
            },
            "syringa vulgaris": {
                "art": "Syringa vulgaris", "taxon_herkunft": "additionalTaxa",
                "felder": {"T": {"wert": 5.8, "systeme": 4}},
            },
        }
        catalog = produce_catalog(selected)
        self.assertEqual(len(catalog["arten"]), 2)
        self.assertEqual(catalog["arten"][0][0], "Rosa canina")
        self.assertEqual(catalog["arten"][0][1:3], [4.5, 6])
        self.assertEqual(catalog["arten"][0][3:7], [None, None, None, None])
        self.assertEqual(catalog["ausgeschlossene_arten_nach_taxonquelle"], {"unresolved": 1})
        self.assertEqual(catalog["lizenz"], "CC BY 4.0")
        self.assertEqual(catalog["felder"], list(DIM))

    def test_deterministische_komprimierung_und_sha256(self):
        catalog = produce_catalog({
            "rosa canina": {
                "art": "Rosa canina", "taxon_herkunft": "EuroMed",
                "felder": {"L": {"wert": 6.26, "systeme": 20}},
            }
        })
        one, m1 = serialize_catalog(catalog)
        two, m2 = serialize_catalog(catalog)
        self.assertEqual(one, two)
        self.assertEqual(m1, m2)
        decoded = gzip.decompress(base64.b64decode(one))
        self.assertEqual(json.loads(decoded), catalog)
        self.assertEqual(m1["catalog_arten"], 1)
        self.assertLess(m1["catalog_base64_bytes"], 700_000)

    def test_kein_passender_datensatz_wird_abgelehnt(self):
        with self.assertRaisesRegex(ValueError, "Keine nach Taxonquelle"):
            produce_catalog({
                "rosa canina": {
                    "art": "Rosa canina", "taxon_herkunft": "unresolved",
                    "felder": {"M": {"wert": 4.5, "systeme": 2}},
                },
            })


if __name__ == "__main__":
    unittest.main()
