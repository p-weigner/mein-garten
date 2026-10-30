"""Regressionsprüfungen für manuell konfigurierte Garten-Wiederholungen."""
import unittest
from datetime import date, datetime, timezone
from custom_components.mein_garten.model import GartenDaten, DatensatzFehler
from custom_components.mein_garten.recurrence import regel_faellig, lokaler_kalendertag


class TestWiederholungen(unittest.TestCase):
    def setUp(self):
        self.model = GartenDaten()

    def create(self, **extra):
        return self.model.regel_anlegen("Pflanzen prüfen", "2026-11-01", "tage",
                                      intervall_tage=7, **extra)

    def test_alte_speicherdatei_bleibt_lesbar(self):
        old = self.model.snapshot()
        del old["regeln"]
        self.assertEqual(GartenDaten(old).snapshot()["regeln"], [])

    def test_regel_idempotent_auch_nach_neustart(self):
        self.create()
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 11, 1)), 1)
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 11, 1)), 0)
        restarted = GartenDaten(self.model.snapshot())
        self.assertEqual(restarted.pflegeplan_aktualisieren(date(2026, 11, 1)), 0)
        self.assertEqual(len(restarted.snapshot()["aufgaben"]), 1)

    def test_erledigte_aufgabe_folgetermin(self):
        self.create()
        self.model.pflegeplan_aktualisieren(date(2026, 11, 1))
        task = self.model.snapshot()["aufgaben"][0]
        self.model.aufgabe_erledigen(task["id"])
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 11, 8)), 1)
        self.assertEqual(len(self.model.snapshot()["aufgaben"]), 2)

    def test_offene_aufgabe_blockiert_zweite(self):
        self.create()
        self.model.pflegeplan_aktualisieren(date(2026, 11, 1))
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 12, 1)), 0)

    def test_entfernte_aufgabe_kommt_nicht_zurueck(self):
        self.create()
        self.model.pflegeplan_aktualisieren(date(2026, 11, 1))
        task = self.model.snapshot()["aufgaben"][0]
        self.model.aufgabe_entfernen(task["id"])
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 11, 1)), 1)
        self.assertEqual(self.model.snapshot()["aufgaben"][0]["faellig_am"], "2026-11-08")

    def test_pausieren_entfernt_offene_instanz(self):
        rule = self.create()
        self.model.pflegeplan_aktualisieren(date(2026, 11, 1))
        self.model.regel_aktiv_setzen(rule["id"], False)
        self.assertEqual(self.model.snapshot()["aufgaben"], [])
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 11, 8)), 0)

    def test_jaehrliche_wiederholung(self):
        rule = self.model.regel_anlegen("Winterkontrolle", "2026-12-01", "jaehrlich")
        self.assertEqual(regel_faellig(rule, [], date(2026, 11, 1)).isoformat(), "2026-12-01")
        self.assertEqual(regel_faellig(rule, [], date(2027, 11, 1)).isoformat(), "2027-12-01")

    def test_februar_29_nicht_jahresregel(self):
        with self.assertRaises(DatensatzFehler):
            self.model.regel_anlegen("Kontrolle", "2028-02-29", "jaehrlich")

    def test_pflegequelle_generiert_keine_aufgaben(self):
        self.model.pflanze_anlegen("Hortensie", "Hydrangea macrophylla")
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2026, 11, 1)), 0)

    def test_pflanze_entfernen_entfernt_regel(self):
        plant = self.model.pflanze_anlegen("Rose")
        self.create(pflanzen_id=plant["id"])
        self.model.pflanze_entfernen(plant["id"])
        self.assertFalse(self.model.snapshot()["regeln"])


    def test_manuel_aus_pflegewissen_mit_quellstatus(self):
        plant = self.model.pflanze_anlegen("Echter Lavendel", "Lavandula angustifolia")
        regel = self.model.regel_anlegen(
            "Schnittbedarf prüfen", "2027-03-15", "jaehrlich",
            pflanzen_id=plant["id"], pflegefeld="pruning",
        )
        self.assertEqual(regel["pflegebezug"]["quelle"], "OpenPlantbook")
        self.assertEqual(regel["pflegebezug"]["feld"], "pruning")
        self.assertEqual(regel["pflegebezug"]["freigabe"], "manuell_durch_benutzer")
        self.assertEqual(self.model.pflegeplan_aktualisieren(date(2027, 3, 1)), 1)

    def test_ungepruefte_quelle_darf_ohne_pflanze_keine_regel_erzeugen(self):
        with self.assertRaises(DatensatzFehler):
            self.model.regel_anlegen(
                "Schnitt", "2027-03-15", "jaehrlich", pflegefeld="pruning"
            )
        plant = self.model.pflanze_anlegen("Hortensie")
        with self.assertRaises(DatensatzFehler):
            self.model.regel_anlegen(
                "Schnitt", "2027-03-15", "jaehrlich",
                pflanzen_id=plant["id"], pflegefeld="shell",
            )


    def test_frostwetterhinweis_einmalig_und_keine_schnittanweisung(self):
        a = self.model.frostpruefung_anlegen("2026-11-03", -1.4, 2)
        self.assertEqual(a["herkunft"], "wetterprognose")
        self.assertIn("kontrollieren", a["name"])
        self.assertNotIn("schneiden", a["name"].lower())
        self.assertIsNone(self.model.frostpruefung_anlegen("2026-11-03", -1.4, 2))
        restarted = GartenDaten(self.model.snapshot())
        self.assertIsNone(restarted.frostpruefung_anlegen("2026-11-03", -1.4, 2))

    def test_wetterhinweis_bei_unterschrittener_schwelle(self):
        with self.assertRaises(DatensatzFehler):
            self.model.frostpruefung_anlegen("2026-11-03", 8, 2)
        self.assertEqual(self.model.snapshot()["aufgaben"], [])


    def test_ortstag_bei_utc_mitternacht_im_winter(self):
        utc = datetime(2026, 10, 30, 23, 15, tzinfo=timezone.utc)
        self.assertEqual(lokaler_kalendertag(utc, "Europe/Berlin"), date(2026, 10, 31))
        self.assertEqual(lokaler_kalendertag(utc, "UTC"), date(2026, 10, 30))

    def test_ortstag_bei_sommerzeit(self):
        utc = datetime(2026, 6, 15, 22, 30, tzinfo=timezone.utc)
        self.assertEqual(lokaler_kalendertag(utc, "Europe/Berlin"), date(2026, 6, 16))

    def test_ohne_zeitzone_keine_stille_verschiebung(self):
        with self.assertRaises(ValueError):
            lokaler_kalendertag(datetime(2026, 10, 30, 22, 30), "Europe/Berlin")


if __name__ == "__main__":
    unittest.main()
