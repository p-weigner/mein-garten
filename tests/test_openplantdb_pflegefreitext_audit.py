"""Offline-Tests für den vorsichtigen Audit von OpenPlantDB-Pflegefreitexten.

Keine Netzwerkanfrage und keine Veröffentlichung von fremden Freitexten.
"""
import unittest

from tools.openplantdb_pflegefreitext_audit import bewerte


def rec(name="Rosa canina", directions=None, planting_note=None, sources=None):
    return {
        "scientific_name": name,
        "directions": directions,
        "planting": {"note": planting_note},
        "sources": sources if sources is not None else ["general horticultural reference"],
    }


TEXT = "General observations about this garden plant, without a binding care schedule."
ALT = "A different observation for the same species with a conflicting cultivation suggestion."
NOTE = "An informational planting note not validated for climate or local season."


class TestPflegefreitextAudit(unittest.TestCase):
    def test_identische_texte_je_art_sind_konsistent_aber_nicht_freigegeben(self):
        records = [
            rec(directions=TEXT, planting_note=NOTE),
            rec(directions=TEXT, planting_note=NOTE),
        ]
        result = bewerte(records, [{
            "name_de": "Hundsrose", "gruppe": "Blumen, Stauden und Rosen",
            "wissenschaftlich": "Rosa canina",
        }])
        self.assertEqual(result["exakte_botanische_arten"], 1)
        self.assertEqual(result["felder"]["directions"]["einheitlich"], 1)
        self.assertEqual(result["felder"]["planting_note"]["einheitlich"], 1)
        self.assertEqual(result["benchmark50_einheitliche_anbauhinweise"], 1)
        self.assertEqual(result["automatische_pflegeaufgaben_freigegeben"], 0)
        self.assertFalse(result["benchmark50"][0]["fachlich_freigegeben"])

    def test_widerspruch_zwischen_sorten_sperrt_den_text(self):
        result = bewerte([
            rec(directions=TEXT, planting_note=NOTE),
            rec(directions=ALT, planting_note=NOTE),
        ], [])
        self.assertEqual(result["felder"]["directions"]["widerspruch"], 1)
        self.assertEqual(result["felder"]["planting_note"]["einheitlich"], 1)

    def test_luecken_und_zu_kurze_texte_werden_kenntlich(self):
        result = bewerte([
            rec(directions=TEXT, planting_note=NOTE),
            rec(directions="", planting_note="too short"),
        ], [])
        self.assertEqual(result["felder"]["directions"]["lueckenhaft"], 1)
        self.assertEqual(result["felder"]["planting_note"]["lueckenhaft"], 1)

    def test_html_und_ueberlange_texte_gelten_nicht_als_gesichert(self):
        result = bewerte([
            rec(directions="<script>evil()</script>" + TEXT, planting_note="x" * 1601),
        ], [])
        self.assertEqual(result["felder"]["directions"]["lueckenhaft"], 1)
        self.assertEqual(result["felder"]["planting_note"]["lueckenhaft"], 1)
        self.assertEqual(result["automatische_pflegeaufgaben_freigegeben"], 0)

    def test_ohne_quellenbeleg_ist_keine_fachfreigabe_moeglich(self):
        result = bewerte([rec(directions=TEXT, sources=[])], [])
        self.assertEqual(result["quellenqualitaet"]["keine_konkrete_quelle"], 1)
        self.assertEqual(result["automatische_pflegeaufgaben_freigegeben"], 0)

    def test_us_kontext_ist_nur_information_und_keine_regionale_freigabe(self):
        from tools.openplantdb_pflegefreitext_audit import US_CONTEXT
        self.assertTrue(bool(US_CONTEXT.search("Plant in USDA zone 7")))
        self.assertTrue(bool(US_CONTEXT.search("Keep at 65°F")))
        self.assertFalse(bool(US_CONTEXT.search("Observed blooming in April")))

    def test_ungueltige_art_bekommt_keinen_verwandten_ersatz(self):
        result = bewerte([
            rec(name="Rosa", directions=TEXT),
            rec(name="Rosa canina 'Alba'", directions=TEXT),
            rec(name="Rosa canina", directions=TEXT),
        ], [{"name_de": "Andere Rose", "gruppe": "Blumen, Stauden und Rosen",
             "wissenschaftlich": "Rosa rugosa"}])
        self.assertEqual(result["exakte_botanische_arten"], 1)
        self.assertEqual(result["ausgeschlossene_rohdatensaetze"]["keine_exakte_art"], 2)
        self.assertEqual(result["benchmark50"][0]["directions"], "fehlt")
        self.assertFalse(result["benchmark50"][0]["fachlich_freigegeben"])

    def test_einzelne_quellenangabe_ist_keine_fachliche_guetepruefung(self):
        result = bewerte([
            rec(directions=TEXT, sources=["https://example.com/a-source"]),
        ], [])
        self.assertEqual(result["quellenqualitaet"]["konkretere_quellenangabe_zu_pruefen"], 1)
        self.assertEqual(result["automatische_pflegeaufgaben_freigegeben"], 0)


if __name__ == "__main__":
    unittest.main()
