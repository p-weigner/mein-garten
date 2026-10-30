"""CC0-Standortwissen: botanisch konsistente, quellgebundene Grundmerkmale."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from custom_components.mein_garten.standort import (
    FILE, COMMIT, CATALOG_SHA256, SOURCE_SHA256, StandortFehler,
    StandortService, pruefe_standortdaten,
)


class TestStandortdaten(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bytes_ = FILE.read_bytes()
        cls.raw = json.loads(cls.bytes_)
        cls.index = pruefe_standortdaten(cls.raw)

    def test_fester_cc0_quelldatensatz_vorhanden_und_hashidentisch(self):
        self.assertLessEqual(FILE.stat().st_size, 900000)
        self.assertEqual(hashlib.sha256(self.bytes_).hexdigest(), CATALOG_SHA256)
        self.assertEqual(self.raw["lizenz"], "CC0 1.0")
        self.assertEqual(self.raw["ausgangs_commit"], COMMIT)
        self.assertEqual(self.raw["quelle_sha256"], SOURCE_SHA256)
        self.assertEqual(len(self.index), 10642)

    def test_licht_wasser_und_frost_bei_typischen_gehoelzen_und_rosen(self):
        self.assertEqual(self.index["rosa canina"]["sun"], "full")
        self.assertEqual(self.index["rosa rugosa"]["season"], "perennial")
        self.assertEqual(self.index["buddleja davidii"]["water"], "low")
        self.assertEqual(self.index["alchemilla mollis"]["sun"], "partial")
        self.assertEqual(self.index["taxus baccata"]["frost_tolerance"], "hardy")

    def test_unsichere_hortensien_wasserwerte_bleiben_ausgespart(self):
        pflege = self.index["hydrangea macrophylla"]
        self.assertEqual(pflege["sun"], "partial")
        self.assertNotIn("water", pflege)
        self.assertEqual(pflege["season"], "perennial")

    def test_50_stichproben_zeigen_reale_abdeckung_ohne_sonderfallliste(self):
        path = Path(__file__).resolve().parent.parent / "daten" / "pflanzensuche_50_de.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        records = [self.index.get(x["wissenschaftlich"].casefold()) for x in cases]
        self.assertEqual(len(cases), 50)
        self.assertEqual(sum(bool(x) for x in records), 46)
        self.assertEqual(sum(bool(x and x.get("sun") and x.get("water"))
                             for x in records), 37)

    def test_unbelegte_sorten_nicht_automatisch_auf_andere_arten_uebertragen(self):
        self.assertNotIn("amelanchier lamarckii", self.index)
        self.assertNotIn("fragaria × ananassa", self.index)
        self.assertIn("rosa canina", self.index)

    def test_angepasste_und_widerspruechliche_felder_abgelehnt(self):
        for change in (
            lambda obj: obj["arten"][0].__setitem__(1, "halbsonnig"),
            lambda obj: obj["arten"][0].__setitem__(0, "Rosa"),
            lambda obj: obj["arten"][0].append("unbekannt"),
            lambda obj: obj["arten"].append(deepcopy(obj["arten"][0])),
            lambda obj: obj.__setitem__("quelle", "unbekannt"),
            lambda obj: obj.__setitem__("lizenz", "Nur privat"),
            lambda obj: obj.__setitem__("quelle_sha256", "a"*64),
            lambda obj: obj.__setitem__("ausgangs_commit", "b"*40),
            lambda obj: obj.__setitem__("felder", ["water", "sun"]),
            lambda obj: obj.__setitem__("automatische_aufgaben", True),
        ):
            damaged = deepcopy(self.raw)
            change(damaged)
            with self.subTest(change=str(change)), self.assertRaises(StandortFehler):
                pruefe_standortdaten(damaged)


class TestStandortService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = types.SimpleNamespace(
            async_add_executor_job=lambda f: asyncio.to_thread(f)
        )
        self.svc = StandortService(self.hass)
        await self.svc.async_laden()

    async def test_keine_externe_api_und_nur_eigene_pflanzen_im_snapshot(self):
        plants = [
            {"id": "1", "name": "Hundsrose", "wissenschaftlich": "Rosa canina"},
            {"id": "2", "name": "Hortensie",
             "wissenschaftlich": "Hydrangea macrophylla"},
            {"id": "3", "name": "Felsenbirne",
             "wissenschaftlich": "Amelanchier lamarckii"},
            {"id": "4", "name": "Privat", "wissenschaftlich": ""},
        ]
        result = self.svc.stand_fuer(plants)
        self.assertEqual(set(result["profile"]), {"1", "2"})
        self.assertEqual(result["abgedeckte_pflanzen"], 2)
        self.assertEqual(result["katalog_arten"], 10642)
        self.assertEqual(result["quell_commit"], COMMIT)
        self.assertEqual(result["quelle"], "OpenPlantDB")
        self.assertIn("keine automatische", result["hinweis"])
        self.assertNotIn("Felsenbirne", json.dumps(result))
        self.assertLess(len(json.dumps(result)), 1800)

    async def test_ausgabe_ist_kopie_und_enthaelt_keine_automatischen_pflegebefehle(self):
        plants = [{"id": "p1", "wissenschaftlich": "Rosa canina"}]
        result = self.svc.stand_fuer(plants)
        result["profile"]["p1"]["merkmale"]["sun"] = "shade"
        after = self.svc.stand_fuer(plants)
        self.assertEqual(after["profile"]["p1"]["merkmale"]["sun"], "full")
        self.assertEqual(set(after["profile"]["p1"]), {"wissenschaftlich", "merkmale"})
        self.assertNotIn("pflegeauftrag", after)
        self.assertNotIn("giessintervall", after)

    async def test_exakt_botanisch_statt_falsche_familienzuordnung(self):
        plants = [
            {"id": "p1", "wissenschaftlich": "Rosa canina"},
            {"id": "p2", "wissenschaftlich": "Rosa canina 'Alba'"},
            {"id": "p3", "wissenschaftlich": "Rosa"},
            {"id": "p4", "wissenschaftlich": "Rosa gallica"},
        ]
        result = self.svc.stand_fuer(plants)
        self.assertEqual(set(result["profile"]), {"p1", "p4"})

    async def test_beschaedigte_offlinedatei_ist_harter_fehler_und_keine_fakewerte(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "standort.json"
            bad.write_text('{"schema":1}', encoding="utf-8")
            obj = StandortService(self.hass)
            with patch("custom_components.mein_garten.standort.FILE", bad):
                with self.assertRaises(StandortFehler):
                    await obj.async_laden()
            self.assertEqual(obj.stand_fuer([{
                "id": "p1", "wissenschaftlich": "Rosa canina"
            }])["profile"], {})


if __name__ == "__main__":
    unittest.main()
