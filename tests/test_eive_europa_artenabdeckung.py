"""Eindeutiger botanischer EIVE-Artabgleich ohne Synonym-/Gattungsersatz."""
from __future__ import annotations
import unittest
from tools.eive_europa_artenabdeckung import REQUIRED, analyse_rows, number


def row(species, *, rank="Species", according="EuroMed", measures=None):
    data = {"TaxonConcept": species, "TaxonRank": rank, "AccordingTo": according}
    for dim, (value, n) in (measures or {}).items():
        data["EIVEres-" + dim] = value
        data["EIVEres-" + dim + ".n"] = n
    return tuple(data.get(col) for col in REQUIRED)


BENCH = [
    {"gruppe": "Sträucher", "name_de": "Hundsrose", "wissenschaftlich": "Rosa canina"},
    {"gruppe": "Kräuter", "name_de": "Lavendel", "wissenschaftlich": "Lavandula angustifolia"},
]


class TestEiveAbdeckung(unittest.TestCase):
    def test_exakte_arten_und_einzelindikatoren(self):
        result = analyse_rows([
            REQUIRED,
            row("Rosa canina", measures={"M": (4.2, 6), "L": (7.3, 9)}),
            row("Lavandula angustifolia", measures={"M": (2.4, 5)}),
        ], BENCH)
        self.assertEqual(result["benchmark50_exakt"], 2)
        self.assertEqual(result["benchmark50_alle_fuenf_indikatoren"], 0)
        self.assertEqual(result["arten_pro_indikator"]["M"], 2)
        self.assertEqual(result["arten_pro_indikator"]["L"], 1)
        self.assertEqual(result["benchmark50"][0]["indikatoren"], ["L", "M"])
        self.assertEqual(result["benchmark50"][0]["quellsysteme_pro_indikator"]["M"], 6)

    def test_gattung_und_unterart_sind_keine_ersatzarten(self):
        result = analyse_rows([
            REQUIRED,
            row("Rosa", measures={"M": (3, 2)}),
            row("Rosa canina subsp. canina", measures={"M": (4, 5)}),
            row("Rosa gallica", measures={"M": (5, 4)}),
        ], BENCH)
        self.assertEqual(result["benchmark50_exakt"], 0)
        self.assertEqual(result["verworfene_zeilen"]["nicht_exakte_art"], 2)

    def test_doppelte_arten_werden_statt_zufallswahl_gesperrt(self):
        result = analyse_rows([
            REQUIRED,
            row("Rosa canina", measures={"M": (4.2, 6)}),
            row("Rosa canina", measures={"M": (9.5, 2)}),
        ], BENCH)
        self.assertEqual(result["benchmark50"][0]["status"], "mehrdeutig")
        self.assertEqual(result["arten_mehrdeutig"], 1)
        self.assertEqual(result["benchmark50_exakt"], 0)

    def test_falsche_oder_untaugliche_messwerte_sind_nicht_nutzbar(self):
        result = analyse_rows([
            REQUIRED,
            row("Rosa canina", measures={
                "M": (float("nan"), 3),
                "N": (999, 2),
                "R": (4, True),
                "L": (7.1, 0),
                "T": (6.3, 5),
            }),
        ], BENCH)
        self.assertEqual(result["benchmark50"][0]["indikatoren"], ["T"])
        self.assertEqual(result["arten_pro_indikator"]["T"], 1)
        self.assertEqual(result["benchmark50_alle_fuenf_indikatoren"], 0)

    def test_quelle_mit_fehlenden_spalten_stoppt(self):
        with self.assertRaisesRegex(ValueError, "erforderliche Spalten"):
            analyse_rows([("TaxonConcept", "TaxonRank")], BENCH)
        with self.assertRaisesRegex(ValueError, "doppelten Spalten"):
            analyse_rows([("TaxonConcept", "TaxonConcept")], BENCH)

    def test_keine_autonomen_pflegemassnahmen_aus_messwerten(self):
        self.assertIsNone(number("water daily"))
        self.assertIsNone(number(-1))
        self.assertIsNone(number(11))
        self.assertIsNone(number(True))
        self.assertEqual(number(3.257), 3.26)


if __name__ == "__main__":
    unittest.main()
