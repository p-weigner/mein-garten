"""Regressionen: lokale Entwicklungsphasen statt ungeprüfter Pflegemaßnahmen."""
from copy import deepcopy
from datetime import date
import unittest

from custom_components.mein_garten.model import (
    BEOBACHTUNGSPHASEN, DatensatzFehler, GartenDaten,
)


class TestEigenePflanzenentwicklung(unittest.TestCase):
    def setUp(self):
        self.garten = GartenDaten()
        self.p = self.garten.pflanze_anlegen(
            "Bauernhortensie", "Hydrangea macrophylla"
        )
        self.heute = date(2026, 10, 30)

    def test_sieben_allgemeine_entwicklungsphasen_ohne_pflegemassnahmen(self):
        self.assertEqual(BEOBACHTUNGSPHASEN, (
            "austrieb", "knospenbildung", "bluete_beginn",
            "fruchtansatz", "fruchtreife", "laubfaerbung", "blattfall",
        ))
        self.assertNotIn("duengen", BEOBACHTUNGSPHASEN)
        self.assertNotIn("schneiden", BEOBACHTUNGSPHASEN)

    def test_beobachtung_lokal_erfasst_mit_verlaesslicher_herkunft(self):
        o = self.garten.beobachtung_anlegen(
            self.p["id"], "bluete_beginn", "2026-05-11",
            notiz="Erste Blüte am Südbeet", person="Angelina", heute=self.heute,
        )
        self.assertEqual(o["phase"], "bluete_beginn")
        self.assertEqual(o["quelle"], "eigene_beobachtung")
        self.assertEqual(o["wissenschaftlich"], "Hydrangea macrophylla")
        self.assertEqual(o["person"], "Angelina")
        self.assertEqual(o["notiz"], "Erste Blüte am Südbeet")
        self.assertIn("erstellt_utc", o)
        data = self.garten.snapshot()
        self.assertEqual(len(data["beobachtungen"]), 1)
        self.assertEqual(len(data["aufgaben"]), 0)
        self.assertEqual(data["historie"][-1]["art"], "pflanzenphase_beobachtet")
        self.assertEqual(data["historie"][-1]["person"], "Angelina")

    def test_doppelklick_erzeugt_keine_doppelte_beobachtung(self):
        args = (self.p["id"], "austrieb", "2026-04-01")
        first = self.garten.beobachtung_anlegen(
            *args, notiz="Erste Triebe", heute=self.heute,
        )
        second = self.garten.beobachtung_anlegen(
            *args, notiz="Erste Triebe", heute=self.heute,
        )
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.garten.snapshot()["beobachtungen"]), 1)
        self.assertEqual(len(self.garten.snapshot()["historie"]), 1)
        with self.assertRaisesRegex(DatensatzFehler, "bereits dokumentiert"):
            self.garten.beobachtung_anlegen(
                *args, notiz="Andere Beobachtung", heute=self.heute,
            )

    def test_verschiedene_jahre_und_phasen_bleiben_unabhaengig(self):
        for when, phase in (
            ("2025-05-03", "bluete_beginn"),
            ("2026-04-28", "bluete_beginn"),
            ("2026-09-01", "fruchtreife"),
        ):
            self.garten.beobachtung_anlegen(
                self.p["id"], phase, when, heute=self.heute,
            )
        second = GartenDaten(self.garten.snapshot())
        self.assertEqual(len(second.snapshot()["beobachtungen"]), 3)

    def test_unbekannte_art_darf_ohne_externe_quelle_beobachtet_werden(self):
        unknown = self.garten.pflanze_anlegen("Neue Sorte ohne Treffer")
        record = self.garten.beobachtung_anlegen(
            unknown["id"], "knospenbildung", "2026-04-22", heute=self.heute,
        )
        self.assertEqual(record["wissenschaftlich"], "")
        self.assertEqual(self.garten.snapshot()["aufgaben"], [])

    def test_keine_future_prognose_als_beobachtung_speichern(self):
        with self.assertRaisesRegex(DatensatzFehler, "Zukunft"):
            self.garten.beobachtung_anlegen(
                self.p["id"], "bluete_beginn", "2026-11-01", heute=self.heute,
            )
        self.assertFalse(self.garten.snapshot()["beobachtungen"])

    def test_unbekannte_phase_datum_und_notiz_verweigern(self):
        tests = [
            ("schneiden", "2026-05-01", "", DatensatzFehler),
            ("bluete_beginn", "2026-02-31", "", DatensatzFehler),
            ("bluete_beginn", "1899-05-01", "", DatensatzFehler),
            ("bluete_beginn", "2026-05-01", "\\x00", DatensatzFehler),
            ("bluete_beginn", "2026-05-01", "a" * 501, DatensatzFehler),
        ]
        for phase, when, note, exc in tests:
            with self.subTest(phase=phase, when=when), self.assertRaises(exc):
                self.garten.beobachtung_anlegen(
                    self.p["id"], phase, when, notiz=note, heute=self.heute,
                )
        self.assertEqual(len(self.garten.snapshot()["beobachtungen"]), 0)

    def test_unbekannte_pflanze_blockiert_beobachtung(self):
        with self.assertRaises(DatensatzFehler):
            self.garten.beobachtung_anlegen(
                "fremde-id", "austrieb", "2026-04-03", heute=self.heute,
            )

    def test_beobachtung_entfernen_loescht_auch_activity_eintrag(self):
        record = self.garten.beobachtung_anlegen(
            self.p["id"], "austrieb", "2026-04-03",
            person="Angelina", heute=self.heute,
        )
        self.assertEqual(len(self.garten.snapshot()["historie"]), 1)
        self.garten.beobachtung_entfernen(record["id"])
        self.assertEqual(self.garten.snapshot()["beobachtungen"], [])
        self.assertEqual(self.garten.snapshot()["historie"], [])
        with self.assertRaises(DatensatzFehler):
            self.garten.beobachtung_entfernen(record["id"])

    def test_pflanze_entfernen_loescht_nur_zugehoerige_beobachtungen(self):
        other = self.garten.pflanze_anlegen("Rose", "Rosa canina")
        first = self.garten.beobachtung_anlegen(
            self.p["id"], "austrieb", "2026-04-01", heute=self.heute,
        )
        second = self.garten.beobachtung_anlegen(
            other["id"], "bluete_beginn", "2026-06-01", heute=self.heute,
        )
        self.garten.pflanze_entfernen(self.p["id"])
        after = self.garten.snapshot()
        self.assertEqual(
            [r["id"] for r in after["beobachtungen"]], [second["id"]],
        )
        self.assertNotIn(first["id"], [
            h["objekt_id"] for h in after["historie"]
        ])
        self.assertIn(second["id"], [
            h["objekt_id"] for h in after["historie"]
        ])

    def test_alter_alpha_datenspeicher_wird_ohne_datenverlust_geladen(self):
        before = self.garten.snapshot()
        before.pop("beobachtungen")
        unchanged = deepcopy(before)
        restarted = GartenDaten(before)
        self.assertEqual(restarted.snapshot()["beobachtungen"], [])
        self.assertEqual(before, unchanged)
        restarted.beobachtung_anlegen(
            self.p["id"], "austrieb", "2026-04-05", heute=self.heute,
        )
        self.assertEqual(len(restarted.snapshot()["pflanzen"]), 1)

    def test_pflanzenart_bei_alten_beobachtungen_bleibt_nach_aenderung_erhalten(self):
        first = self.garten.beobachtung_anlegen(
            self.p["id"], "bluete_beginn", "2026-05-01", heute=self.heute,
        )
        self.garten.pflanze_bearbeiten(
            self.p["id"], wissenschaftlich="Hydrangea paniculata"
        )
        self.assertEqual(
            self.garten.snapshot()["beobachtungen"][0]["wissenschaftlich"],
            first["wissenschaftlich"],
        )


if __name__ == "__main__":
    unittest.main()
