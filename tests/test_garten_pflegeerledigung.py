"""Regression: kombinierte Pflege-Erledigungen und nachvollziehbare Historie."""
import unittest
from datetime import date

from custom_components.mein_garten.model import DatensatzFehler, GartenDaten


class TestPflegeErledigungen(unittest.TestCase):
    def setUp(self):
        self.garten = GartenDaten()
        self.pflanze = self.garten.pflanze_anlegen("Echter Lavendel", "Lavandula angustifolia")

    def test_einfache_aufgabe_bleibt_einklick_erledigung(self):
        task = self.garten.aufgabe_anlegen("Unkraut entfernen")
        result = self.garten.aufgabe_erledigen(task["id"], "Angelina")
        self.assertEqual(result["ergebnis"], "erledigt")
        self.assertEqual(self.garten.snapshot()["historie"][-1]["ergebnis"], "erledigt")

    def test_giesskontrolle_ohne_entscheidung_bleibt_offen(self):
        task = self.garten.aufgabe_anlegen(
            "Wasser prüfen", pflanzen_id=self.pflanze["id"], aufgabentyp="giesskontrolle"
        )
        with self.assertRaises(DatensatzFehler):
            self.garten.aufgabe_erledigen(task["id"], "Angelina")
        self.assertEqual(self.garten.snapshot()["aufgaben"][0]["status"], "offen")
        self.assertEqual(self.garten.snapshot()["historie"], [])

    def test_kein_wasser_noetig_ist_eigenstaendiges_ergebnis(self):
        task = self.garten.aufgabe_anlegen("Wasser prüfen", aufgabentyp="giesskontrolle")
        result = self.garten.aufgabe_erledigen(
            task["id"], "Angelina", ergebnis="kontrolliert_kein_wasser"
        )
        self.assertEqual(result["status"], "erledigt")
        self.assertEqual(result["ergebnis"], "kontrolliert_kein_wasser")
        history = self.garten.snapshot()["historie"]
        self.assertEqual(history[-1]["ergebnis"], "kontrolliert_kein_wasser")
        self.assertEqual(history[-1]["person"], "Angelina")

    def test_gegossen_vom_kontrollieren_unterscheidbar(self):
        task = self.garten.aufgabe_anlegen("Gießkontrolle", aufgabentyp="giesskontrolle")
        result = self.garten.aufgabe_erledigen(task["id"], ergebnis="gegossen")
        self.assertEqual(result["ergebnis"], "gegossen")

    def test_falsches_giessergebnis_wird_nicht_akzeptiert(self):
        task = self.garten.aufgabe_anlegen("Gießkontrolle", aufgabentyp="giesskontrolle")
        for wrong in ("duengen", "wasser_noetig", "", "erledigt", None):
            with self.subTest(ergebnis=wrong), self.assertRaises(DatensatzFehler):
                self.garten.aufgabe_erledigen(task["id"], ergebnis=wrong)
        self.assertEqual(self.garten.snapshot()["aufgaben"][0]["status"], "offen")

    def test_einfache_aufgabe_darf_nicht_als_gegossen_markiert_werden(self):
        task = self.garten.aufgabe_anlegen("Beet kontrollieren")
        with self.assertRaises(DatensatzFehler):
            self.garten.aufgabe_erledigen(task["id"], ergebnis="gegossen")

    def test_doppelklick_erzeugt_keine_doppelte_historie(self):
        task = self.garten.aufgabe_anlegen("Wässern", aufgabentyp="giesskontrolle")
        self.garten.aufgabe_erledigen(task["id"], "Angelina", "gegossen")
        self.garten.aufgabe_erledigen(task["id"], "Angelina", "gegossen")
        self.assertEqual(len(self.garten.snapshot()["historie"]), 1)
        with self.assertRaises(DatensatzFehler):
            self.garten.aufgabe_erledigen(
                task["id"], "Angelina", "kontrolliert_kein_wasser"
            )

    def test_erneutes_oeffnen_setzt_ergebnis_zurueck(self):
        task = self.garten.aufgabe_anlegen("Gießkontrolle", aufgabentyp="giesskontrolle")
        self.garten.aufgabe_erledigen(task["id"], "Angelina", "gegossen")
        reopened = self.garten.aufgabe_wieder_oeffnen(task["id"], "Patrick")
        self.assertIsNone(reopened["ergebnis"])
        self.assertIsNone(reopened["erledigt_utc"])
        self.garten.aufgabe_erledigen(task["id"], "Patrick", "kontrolliert_kein_wasser")
        events = self.garten.snapshot()["historie"]
        self.assertEqual([e["art"] for e in events], [
            "aufgabe_erledigt", "aufgabe_wieder_geoeffnet", "aufgabe_erledigt"
        ])
        self.assertEqual(events[0]["ergebnis"], "gegossen")
        self.assertEqual(events[2]["ergebnis"], "kontrolliert_kein_wasser")

    def test_wiederkehrende_bewasserung_behaelt_typ_auch_nach_neustart(self):
        self.garten.regel_anlegen(
            "Gießbedarf prüfen", "2026-11-01", "tage", intervall_tage=7,
            pflanzen_id=self.pflanze["id"], pflegefeld="watering",
            aufgabentyp="giesskontrolle",
        )
        self.assertEqual(self.garten.pflegeplan_aktualisieren(date(2026, 11, 1)), 1)
        task = self.garten.snapshot()["aufgaben"][0]
        self.assertEqual(task["aufgabentyp"], "giesskontrolle")
        self.garten.aufgabe_erledigen(task["id"], "Angelina", "kontrolliert_kein_wasser")
        new = GartenDaten(self.garten.snapshot())
        self.assertEqual(new.pflegeplan_aktualisieren(date(2026, 11, 8)), 1)
        self.assertEqual(new.snapshot()["aufgaben"][-1]["aufgabentyp"], "giesskontrolle")

    def test_alte_speicherdatei_ist_kompatibel(self):
        task = self.garten.aufgabe_anlegen("Frühjahrsarbeiten")
        daten = self.garten.snapshot()
        daten["aufgaben"][0].pop("aufgabentyp")
        daten["aufgaben"][0].pop("ergebnis")
        neu = GartenDaten(daten)
        self.assertEqual(neu.aufgabe_erledigen(task["id"])["ergebnis"], "erledigt")

    def test_ungueltiger_typ_und_watering_mismatch_werden_gesperrt(self):
        with self.assertRaises(DatensatzFehler):
            self.garten.aufgabe_anlegen("Gießen", aufgabentyp="unbekannt")
        with self.assertRaises(DatensatzFehler):
            self.garten.regel_anlegen(
                "Wasser prüfen", "2027-04-01", "jaehrlich",
                pflanzen_id=self.pflanze["id"], pflegefeld="watering",
                aufgabentyp="einfach",
            )


if __name__ == "__main__":
    unittest.main()
