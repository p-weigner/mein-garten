"""Reproduzierbarer CC0-Import ohne Pflanzen-Sonderregeln oder Pflegefreitexte."""
import unittest

from tools.openplantdb_standort_export import make_dataset, FIELD_ORDER


def source(species="Rosa canina", **kwargs):
    return {
        "scientific_name": species,
        "sun": kwargs.get("sun", "full"),
        "water": kwargs.get("water", "low"),
        "frost_tolerance": kwargs.get("frost_tolerance", "hardy"),
        "season": kwargs.get("season", "perennial"),
        "directions": "Dies ist ein ausdrücklich NICHT zu exportierender Freitext.",
        "sources": ["Quellentext-Beispiel"],
    }


def exported(records):
    return make_dataset(records, mindest_arten=1, maximal_arten=15)


class TestStandortImport(unittest.TestCase):
    def test_identische_sortenwerte_werden_pro_art_konsentiert(self):
        payload, report = exported([
            source("Rosa canina", sun="full", water="low"),
            source("Rosa canina", sun="full", water="low"),
            source("Buddleja davidii", sun="full", water="low"),
        ])
        self.assertEqual(payload["felder"], list(FIELD_ORDER))
        self.assertEqual(len(payload["arten"]), 2)
        self.assertEqual(payload["arten"][0][0], "Buddleja davidii")
        self.assertEqual(payload["arten"][1][0], "Rosa canina")
        self.assertEqual(report["arten"], 2)
        self.assertEqual(report["merkmale"]["water"], 2)

    def test_sortenwiderspruch_betrifft_nur_das_jeweilige_feld(self):
        payload, report = exported([
            source("Hydrangea macrophylla", sun="partial",
                   water="moderate", frost_tolerance="hardy"),
            source("Hydrangea macrophylla", sun="partial",
                   water="high", frost_tolerance="hardy"),
        ])
        r = payload["arten"][0]
        self.assertEqual(r[0], "Hydrangea macrophylla")
        self.assertEqual(r[1], "partial")
        self.assertIsNone(r[2])
        self.assertEqual(r[3], "hardy")
        self.assertEqual(report["merkmale_ausgeschlossen_bei_widerspruch"]["water"], 1)

    def test_unbekannte_werte_koennen_keine_wirkung_ausloesen(self):
        payload, _ = exported([
            source("Rosa rugosa", water="very high"),
            source("Rosa rugosa", water="low"),
        ])
        self.assertEqual(payload["arten"][0][0], "Rosa rugosa")
        self.assertIsNone(payload["arten"][0][2])
        self.assertEqual(payload["arten"][0][1], "full")

    def test_unbelegte_oder_nicht_binomiale_art_nicht_erraten(self):
        payload, _ = exported([
            source("Rosa canina"),
            source("Rosa", water="low"),
            source("Rosa canina 'Alba'", water="high"),
            source("Amelanchier lamarckii", sun=None, water=None,
                   frost_tolerance=None, season=None),
        ])
        self.assertEqual([r[0] for r in payload["arten"]], ["Rosa canina"])

    def test_kein_quellfreitext_im_katalog(self):
        payload, _ = exported([source("Rosa canina")])
        self.assertEqual(set(payload), {
            "schema", "quelle", "lizenz", "ausgangs_commit",
            "quelle_sha256", "herkunft", "pruefstatus", "felder", "arten",
        })
        self.assertEqual(payload["lizenz"], "CC0 1.0")
        self.assertNotIn("Quellentext-Beispiel", str(payload))
        self.assertNotIn("Dies ist ein", str(payload))
        self.assertNotIn("directions", str(payload))

    def test_ungueltiges_exportvolumen_und_leerer_katalog_fehler(self):
        with self.assertRaises(ValueError):
            make_dataset([source("Rosa canina")])
        with self.assertRaises(ValueError):
            make_dataset([], mindest_arten=1, maximal_arten=10)
        with self.assertRaises(ValueError):
            make_dataset([
                source("Rosa canina"), source("Buddleja davidii"),
            ], mindest_arten=1, maximal_arten=1)


if __name__ == "__main__":
    unittest.main()
