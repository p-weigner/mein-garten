"""Regression: sichere, quellengebundene Saisonfenster für Home Assistant Green."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import asyncio
import json
import sys
import types
import unittest
from unittest.mock import patch

from custom_components.mein_garten.model import GartenDaten, DatensatzFehler
from custom_components.mein_garten.season import (
    CATALOG_FILE, SaisonFehler, SaisonService, pruefe_anker,
    pruefe_katalog, vorschlaege_fuer, fenster_fuer,
)


class TestSaisonKatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CATALOG_FILE.open(encoding="utf-8") as stream:
            cls.source = json.load(stream)
        cls.catalog = pruefe_katalog(cls.source)

    def test_daten_aus_versionierter_cc0_quelle(self):
        self.assertEqual(self.source["lizenz"], "CC0 1.0")
        self.assertEqual(len(self.catalog), 152)
        self.assertEqual(len(self.source["ausgangs_commit"]), 40)
        self.assertIn("solanum lycopersicum", self.catalog)

    def test_keine_automatischen_arbeiten_ohne_referenzdatum(self):
        pflanze = {"id": "p1", "name": "Meine Tomate",
                   "wissenschaftlich": "Solanum lycopersicum"}
        records = vorschlaege_fuer(self.catalog, {
            "last_frost": "", "first_frost": "",
        }, [pflanze], [])
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["fenster_von"])
        self.assertEqual(records[0]["fehlender_anker"], "last_frost")
        self.assertFalse(records[0]["vorgemerkt"])

    def test_tomate_aussaat_nur_als_pruefung_mit_datumsreferenz(self):
        expected = self.catalog["solanum lycopersicum"]
        self.assertEqual(expected["methode"], "indoor-start")
        self.assertEqual((expected["wochen_von"], expected["wochen_bis"]), (-8, -6))
        start, end = fenster_fuer(expected, {
            "last_frost": "2027-05-15", "first_frost": "",
        })
        self.assertEqual((start.isoformat(), end.isoformat()),
                         ("2027-03-20", "2027-04-03"))

    def test_anderer_wissenschaftlicher_name_ist_keine_gleiche_art(self):
        vals = vorschlaege_fuer(self.catalog, {
            "last_frost": "2027-05-15", "first_frost": "",
        }, [
            {"id": "p1", "name": "Nicht Tomate",
             "wissenschaftlich": "Solanum tuberosum"},
            {"id": "p2", "name": "Sorte", "wissenschaftlich": "Solanum lycopersicum x"},
            {"id": "p3", "name": "Ohne Art", "wissenschaftlich": ""},
        ], [])
        self.assertTrue(all(x["wissenschaftlich"] != "Solanum lycopersicum" for x in vals))

    def test_keine_ungeprueften_regeln_aus_freitext(self):
        bad = deepcopy(self.source)
        bad["regeln"][0]["hinweis"] = "Sofort düngen"
        with self.assertRaises(SaisonFehler):
            pruefe_katalog(bad)

    def test_doppelte_und_zuweite_intervalle_abgewiesen(self):
        d = deepcopy(self.source)
        d["regeln"].append(deepcopy(d["regeln"][0]))
        with self.assertRaises(SaisonFehler):
            pruefe_katalog(d)
        d = deepcopy(self.source)
        d["regeln"][0]["wochen_bis"] = 50
        with self.assertRaises(SaisonFehler):
            pruefe_katalog(d)

    def test_quellenstatus_im_vorschlag(self):
        rec = vorschlaege_fuer(self.catalog, {
            "last_frost": "2027-05-15", "first_frost": "",
        }, [{"id": "p1", "name": "Tomate",
             "wissenschaftlich": "Solanum lycopersicum"}], [])[0]
        self.assertEqual(rec["quelle"], "OpenPlantDB")
        self.assertEqual(rec["lizenz"], "CC0 1.0")
        self.assertEqual(rec["pruefstatus"], "unverbindliche_Planungshilfe")

    def test_frost_anker_validation(self):
        self.assertEqual(pruefe_anker({
            "last_frost": "2027-05-15", "first_frost": "2027-10-15",
        })["first_frost"], "2027-10-15")
        for vals in (
            {"last_frost": "2027-05-15", "first_frost": "2026-10-15"},
            {"last_frost": "2027-10-15", "first_frost": "2027-05-15"},
            {"last_frost": "2027-02-30", "first_frost": ""},
            {"last_frost": "2027-05-15", "first_frost": None},
            {"last_frost": "2027-05-15"},
            {"last_frost": "2050-05-12", "first_frost": "", "extra": "unsafe"},
        ):
            if "extra" in vals or vals.get("first_frost") is None:
                with self.assertRaises(SaisonFehler):
                    pruefe_anker(vals)
            elif vals["last_frost"] == "2050-05-12":
                pass
            else:
                with self.assertRaises(SaisonFehler):
                    pruefe_anker(vals)

    def test_einmal_vorgemerkte_saison_erkennbar(self):
        record = {
            "id": "t1", "pflanzen_id": "p1",
            "saisonbezug": {
                "katalog_id": "tomato", "anker_jahr": 2027,
            },
        }
        proposal = vorschlaege_fuer(self.catalog, {
            "last_frost": "2027-05-15", "first_frost": "",
        }, [{"id": "p1", "name": "Meine Tomate",
             "wissenschaftlich": "Solanum lycopersicum"}], [record])[0]
        self.assertTrue(proposal["vorgemerkt"])


class FakeStore:
    state = None
    def __init__(self, *_args):
        pass
    async def async_load(self):
        return deepcopy(self.state)
    async def async_save(self, data):
        self.state = deepcopy(data)


class FakeBackend:
    def __init__(self):
        self.model = GartenDaten()
        self.events = []
    def snapshot(self):
        return self.model.snapshot()
    async def async_aendern(self, method, **params):
        self.events.append((method, deepcopy(params)))
        return getattr(self.model, method)(**params)


class TestSaisonService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        storemod = types.ModuleType("homeassistant.helpers.storage")
        storemod.Store = FakeStore
        self.modules = patch.dict(sys.modules, {
            "homeassistant.helpers.storage": storemod,
        })
        self.modules.start()
        FakeStore.state = None
        self.hass = types.SimpleNamespace(async_add_executor_job=lambda f: asyncio.to_thread(f))
        self.backend = FakeBackend()
        self.service = SaisonService(self.hass, self.backend)
        await self.service.async_laden()
        self.tomate = self.backend.model.pflanze_anlegen(
            "Tomate", "Solanum lycopersicum",
        )

    async def asyncTearDown(self):
        self.modules.stop()

    async def test_laden_offline_und_ohne_netz(self):
        self.assertGreaterEqual(self.service.stand()["katalog_arten"], 100)
        self.assertEqual(self.service.stand()["anker"], {
            "last_frost": "", "first_frost": "",
        })

    async def test_erinnerung_erst_nach_eigenem_datum(self):
        with self.assertRaises(SaisonFehler):
            await self.service.async_vormerken(
                self.tomate["id"], "tomato", "2027-03-24",
            )
        self.assertFalse(self.backend.snapshot()["aufgaben"])
        await self.service.async_anker_speichern({
            "last_frost": "2027-05-15", "first_frost": "",
        })
        result = await self.service.async_vormerken(
            self.tomate["id"], "tomato", "2027-03-24",
        )
        self.assertEqual(result["faellig_am"], "2027-03-24")
        self.assertEqual(result["herkunft"], "saisonpruefung")
        self.assertIn("prüfen", result["name"].lower())
        self.assertEqual(result["saisonbezug"]["lizenz"], "CC0 1.0")
        self.assertTrue(self.service.stand()["vorschlaege"][0]["vorgemerkt"])

    async def test_keine_fernbefehle_oder_gefahrsachen_als_namen(self):
        await self.service.async_anker_speichern({
            "last_frost": "2027-05-15", "first_frost": "",
        })
        with self.assertRaises(SaisonFehler):
            await self.service.async_vormerken(
                self.tomate["id"], "evil-pruning", "2027-03-24",
            )
        with self.assertRaises(SaisonFehler):
            await self.service.async_vormerken(
                self.tomate["id"], "tomato", "2027-07-02",
            )
        self.assertEqual(self.backend.events, [])

    async def test_doppeltermin_verhindert_auch_nach_neustart(self):
        await self.service.async_anker_speichern({
            "last_frost": "2027-05-15", "first_frost": "",
        })
        await self.service.async_vormerken(self.tomate["id"], "tomato", "2027-03-24")
        restarted = FakeBackend()
        restarted.model = GartenDaten(self.backend.snapshot())
        next_service = SaisonService(self.hass, restarted)
        await next_service.async_laden()
        with self.assertRaises(DatensatzFehler):
            await next_service.async_vormerken(
                self.tomate["id"], "tomato", "2027-03-26",
            )

    async def test_speicherdefekt_wird_nicht_ueberschrieben(self):
        FakeStore.state = {"version": 999, "anker": {}}
        restarted = SaisonService(self.hass, self.backend)
        with self.assertRaises(SaisonFehler):
            await restarted.async_laden()
        self.assertEqual(FakeStore.state["version"], 999)


if __name__ == "__main__":
    unittest.main()
