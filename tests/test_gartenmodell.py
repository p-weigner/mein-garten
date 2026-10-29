import unittest
from datetime import datetime

from custom_components.mein_garten.model import (
    DatensatzFehler, GartenDaten, PFLANZENGRUPPEN, SCHEMA_VERSION,
)


class TestGartenStammdaten(unittest.TestCase):
    def setUp(self):
        self.db = GartenDaten()

    def test_start_leer(self):
        s = self.db.snapshot()
        self.assertEqual(s["version"], SCHEMA_VERSION)
        self.assertEqual((s["pflanzen"], s["bereiche"], s["aufgaben"]), ([], [], []))

    def test_bereiche_dynamisch_anlegen_und_umbenennen(self):
        a = self.db.bereich_anlegen("Hochbeet")
        b = self.db.bereich_anlegen("Vorgarten")
        self.assertNotEqual(a["id"], b["id"])
        c = self.db.bereich_umbenennen(a["id"], "Kräuterbeet")
        self.assertEqual(c["name"], "Kräuterbeet")

    def test_keine_doppelten_bereichsnamen(self):
        self.db.bereich_anlegen("Vorgarten")
        with self.assertRaises(DatensatzFehler):
            self.db.bereich_anlegen("  vorgarten ")

    def test_pflanze_beliebige_art_ohne_programmcode(self):
        obj = self.db.pflanze_anlegen(
            "Japanische Pfingstrose", "Paeonia lactiflora", gruppe=PFLANZENGRUPPEN[0]
        )
        self.assertEqual(obj["wissenschaftlich"], "Paeonia lactiflora")

    def test_pflanze_darf_ohne_bereich_angelegt_werden(self):
        plant = self.db.pflanze_anlegen("Unbekannte neue Sorte")
        self.assertIsNone(plant["bereich_id"])
        self.assertEqual(plant["wissenschaftlich"], "")

    def test_freie_gartenbereiche_ohne_gruppenzwang(self):
        area = self.db.bereich_anlegen("Wintergarten rechts")
        plant = self.db.pflanze_anlegen("Olive", bereich_id=area["id"])
        self.assertEqual(plant["bereich_id"], area["id"])

    def test_pflanze_umsortieren(self):
        a = self.db.bereich_anlegen("Garten").get("id")
        b = self.db.bereich_anlegen("Terrasse").get("id")
        p = self.db.pflanze_anlegen("Hortensie", bereich_id=a)
        changed = self.db.pflanze_bearbeiten(p["id"], bereich_id=b, name="Bauernhortensie")
        self.assertEqual(changed["bereich_id"], b)
        self.assertEqual(changed["name"], "Bauernhortensie")

    def test_bereich_loeschen_pflanzen_erhalten(self):
        area = self.db.bereich_anlegen("Garten")
        plant = self.db.pflanze_anlegen("Hortensie", bereich_id=area["id"])
        task = self.db.aufgabe_anlegen("Gießen", bereich_id=area["id"])
        self.db.bereich_entfernen(area["id"])
        snap = self.db.snapshot()
        self.assertEqual(len(snap["pflanzen"]), 1)
        self.assertEqual(snap["pflanzen"][0]["id"], plant["id"])
        self.assertIsNone(snap["pflanzen"][0]["bereich_id"])
        self.assertIsNone(snap["aufgaben"][0]["bereich_id"])
        self.assertEqual(task["name"], "Gießen")

    def test_pflanze_loeschen_entfernt_zugeordnete_aufgaben(self):
        p = self.db.pflanze_anlegen("Rose")
        q = self.db.pflanze_anlegen("Lavendel")
        task = self.db.aufgabe_anlegen("Schneiden", pflanzen_id=p["id"])
        self.db.aufgabe_anlegen("Gießen", pflanzen_id=q["id"])
        self.db.aufgabe_erledigen(task["id"], person="angelina")
        self.db.pflanze_entfernen(p["id"])
        result = self.db.snapshot()
        self.assertEqual(len(result["pflanzen"]), 1)
        self.assertEqual(len(result["aufgaben"]), 1)
        self.assertFalse(result["historie"])

    def test_notizen_und_gruppe_aenderbar(self):
        p = self.db.pflanze_anlegen("Olive")
        updated = self.db.pflanze_bearbeiten(
            p["id"], gruppe=PFLANZENGRUPPEN[4], notizen="Überwinterung im Haus"
        )
        self.assertEqual(updated["gruppe"], PFLANZENGRUPPEN[4])
        self.assertEqual(updated["notizen"], "Überwinterung im Haus")

    def test_unbekannte_gruppe_abgelehnt(self):
        with self.assertRaises(DatensatzFehler):
            self.db.pflanze_anlegen("Olive", gruppe="Unbekannt")
        self.assertEqual(len(self.db.snapshot()["pflanzen"]), 0)

    def test_bereich_referenz_validieren(self):
        with self.assertRaises(DatensatzFehler):
            self.db.pflanze_anlegen("Olive", bereich_id="gibt-es-nicht")
        self.assertEqual(len(self.db.snapshot()["pflanzen"]), 0)

    def test_aufgabe_beliebige_pflege_manuell(self):
        p = self.db.pflanze_anlegen("Pfingstrose")
        task = self.db.aufgabe_anlegen(
            "Verblühtes entfernen", "2027-07-01", pflanzen_id=p["id"]
        )
        self.assertEqual(task["status"], "offen")
        self.assertEqual(task["herkunft"], "manuell")
        self.assertEqual(task["faellig_am"], "2027-07-01")

    def test_ungueltiges_datum_abgelehnt(self):
        with self.assertRaises(DatensatzFehler):
            self.db.aufgabe_anlegen("Gießen", "2027-02-31")
        with self.assertRaises(DatensatzFehler):
            self.db.aufgabe_anlegen("Gießen", "01.07.2027")

    def test_aufgabe_erledigung_in_history(self):
        task = self.db.aufgabe_anlegen("Gießen", "2027-05-01")
        result = self.db.aufgabe_erledigen(task["id"], person="angelina")
        self.assertEqual(result["status"], "erledigt")
        self.assertIsNotNone(result["erledigt_utc"])
        log = self.db.snapshot()["historie"]
        self.assertEqual(log[0]["art"], "aufgabe_erledigt")
        self.assertEqual(log[0]["person"], "angelina")

    def test_erledigung_idempotent(self):
        task = self.db.aufgabe_anlegen("Gießen")
        self.db.aufgabe_erledigen(task["id"])
        self.db.aufgabe_erledigen(task["id"])
        self.assertEqual(len(self.db.snapshot()["historie"]), 1)

    def test_wieder_oeffnen_und_history(self):
        task = self.db.aufgabe_anlegen("Gießen")
        self.db.aufgabe_erledigen(task["id"])
        self.db.aufgabe_wieder_oeffnen(task["id"])
        data = self.db.snapshot()
        self.assertEqual(data["aufgaben"][0]["status"], "offen")
        self.assertIsNone(data["aufgaben"][0]["erledigt_utc"])
        self.assertEqual([x["art"] for x in data["historie"]],
                         ["aufgabe_erledigt", "aufgabe_wieder_geoeffnet"])

    def test_aufgabe_entfernen_entfernt_ihre_history(self):
        task = self.db.aufgabe_anlegen("Gießen")
        self.db.aufgabe_erledigen(task["id"])
        self.db.aufgabe_entfernen(task["id"])
        self.assertEqual(self.db.snapshot()["aufgaben"], [])
        self.assertEqual(self.db.snapshot()["historie"], [])

    def test_keine_automatischen_aufgaben_aus_englischen_freitexten(self):
        self.db.pflanze_anlegen("Hortensie")
        self.assertEqual(self.db.snapshot()["aufgaben"], [])

    def test_snapshot_unabhaengige_kopie(self):
        self.db.snapshot()["pflanzen"].append({"id": "fake"})
        self.assertEqual(self.db.snapshot()["pflanzen"], [])

    def test_neustart_kann_snapshot_laden(self):
        area = self.db.bereich_anlegen("Hochbeet")
        self.db.pflanze_anlegen("Tomate", bereich_id=area["id"])
        second = GartenDaten(self.db.snapshot())
        self.assertEqual(second.snapshot(), self.db.snapshot())

    def test_unbekannte_datenversion_ueberschreibt_nicht(self):
        data = self.db.snapshot()
        data["version"] = 999
        with self.assertRaises(DatensatzFehler):
            GartenDaten(data)

    def test_beschaedigte_daten_ueberschreiben_nicht(self):
        with self.assertRaises(DatensatzFehler):
            GartenDaten({"version": 1, "pflanzen": []})

    def test_id_konflikte_werden_abgelehnt(self):
        a = self.db.bereich_anlegen("Hochbeet")
        data = self.db.snapshot()
        data["bereiche"].append(dict(a))
        with self.assertRaises(DatensatzFehler):
            GartenDaten(data)

    def test_gartenbereich_ungueltige_zeichen(self):
        with self.assertRaises(DatensatzFehler):
            self.db.bereich_anlegen("Haustür\u0000")

    def test_zu_lange_notizen_abgelehnt(self):
        with self.assertRaises(DatensatzFehler):
            self.db.pflanze_anlegen("Hortensie", notizen="a" * 4001)

    def test_unbekanntes_update_feld_abgelehnt(self):
        obj = self.db.pflanze_anlegen("Rose")
        with self.assertRaises(DatensatzFehler):
            self.db.pflanze_bearbeiten(obj["id"], critical_flag="true")

    def test_fuenf_benutzergruppen_unabhaengig_von_pflanzenarten(self):
        self.assertEqual(len(PFLANZENGRUPPEN), 5)
        self.db.pflanze_anlegen("Beliebige neu gezüchtete Pflanze")
        self.assertEqual(len(self.db.snapshot()["pflanzen"]), 1)


if __name__ == "__main__":
    unittest.main()
