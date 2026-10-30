"""Isolierte Tests der deutschen Pflanzensuche ohne Home Assistant und Netzwerk."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from custom_components.mein_garten.search import (
    Pflanzensuche, _dedupe, _inat_results, _norm, _plant_name,
    _wikidata_taxa, _gbif_results,
)


class TestTaxonParsing(unittest.TestCase):
    def test_botanische_arten_und_hybride(self):
        self.assertTrue(_plant_name("Hydrangea macrophylla"))
        self.assertTrue(_plant_name("Fragaria × ananassa"))
        self.assertFalse(_plant_name("Hydrangea"))
        self.assertFalse(_plant_name("Bauernhortensie"))

    def test_gattung_oder_familie_nicht_als_art(self):
        result = _inat_results({"results": [
            {"name": "Hydrangea", "rank": "genus", "id": 1},
            {"name": "Hydrangeaceae", "rank": "family", "id": 2},
            {"name": "Hydrangea macrophylla", "rank": "species", "id": 3,
             "preferred_common_name": "Bauernhortensie"},
        ]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["wissenschaftlich"], "Hydrangea macrophylla")
        self.assertTrue(result[0]["bestaetigt"])

    def test_hybrid_spezies(self):
        result = _inat_results({"results": [
            {"name": "Fragaria × ananassa", "rank": "hybrid", "id": 5}
        ]})
        self.assertEqual(result[0]["wissenschaftlich"], "Fragaria × ananassa")

    def test_gbif_nur_pflanzenarten(self):
        values = _gbif_results([
            {"rank": "SPECIES", "kingdom": "Plantae",
             "canonicalName": "Hydrangea macrophylla", "key": 12},
            {"rank": "GENUS", "kingdom": "Plantae", "canonicalName": "Hydrangea"},
            {"rank": "SPECIES", "kingdom": "Animalia",
             "canonicalName": "Vespa crabro"},
        ])
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["wissenschaftlich"], "Hydrangea macrophylla")

    def test_ungueltige_api_antwort(self):
        with self.assertRaises(ValueError):
            _inat_results({"error": "rate limit"})
        with self.assertRaises(ValueError):
            _inat_results([])

    def test_wikidata_bauernhortensie(self):
        search = {"search": [
            {"id": "Q123", "label": "Gartenhortensie", "match": {
                "type": "alias", "text": "Bauernhortensie",
            }},
            {"id": "Q456", "label": "Tomatenminiermotte"},
        ]}
        entities = {"entities": {
            "Q123": {"claims": {"P225": [
                {"mainsnak": {"datavalue": {"value": "Hydrangea macrophylla"}}}
            ]}},
            "Q456": {"claims": {"P225": [
                {"mainsnak": {"datavalue": {"value": "Tuta absoluta"}}}
            ]}},
        }}
        result = _wikidata_taxa(search, entities, "Bauernhortensie")
        self.assertEqual(len(result), 2)
        self.assertFalse(result[0]["bestaetigt"])
        self.assertEqual(result[0]["wissenschaftlich"], "Hydrangea macrophylla")

    def test_duplikate_quellen_vereinen(self):
        one = {"wissenschaftlich": "Hydrangea macrophylla",
               "deutsch": "", "bestaetigt": True, "quellen": ["iNaturalist"]}
        two = {"wissenschaftlich": "Hydrangea macrophylla",
               "deutsch": "Gartenhortensie", "bestaetigt": False,
               "quellen": ["Wikidata"]}
        result = _dedupe([one, two])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["deutsch"], "Gartenhortensie")
        self.assertEqual(result[0]["quellen"], ["Wikidata", "iNaturalist"])

    def test_quellen_bei_spaeter_bestaetigtem_treffer_erhalten(self):
        zuerst = {"wissenschaftlich": "Hydrangea macrophylla",
                  "deutsch": "Gartenhortensie", "bestaetigt": False,
                  "quellen": ["Wikidata"]}
        danach = {"wissenschaftlich": "Hydrangea macrophylla",
                  "deutsch": "", "bestaetigt": True,
                  "quellen": ["iNaturalist"]}
        result = _dedupe([zuerst, danach])
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["bestaetigt"])
        self.assertEqual(result[0]["deutsch"], "Gartenhortensie")
        self.assertEqual(result[0]["quellen"], ["Wikidata", "iNaturalist"])

    def test_falsche_arten_nicht_vereinen(self):
        result = _dedupe([
            {"wissenschaftlich": "Hydrangea paniculata",
             "deutsch": "", "bestaetigt": True, "quellen": ["iNaturalist"]},
            {"wissenschaftlich": "Hydrangea macrophylla",
             "deutsch": "", "bestaetigt": True, "quellen": ["iNaturalist"]},
        ])
        self.assertEqual(len(result), 2)


class TestDynamischeSuche(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = Pflanzensuche(object())
        self.service._gbif = AsyncMock(return_value=[])

    async def test_deutsche_suche_ueber_wikidata_mit_verifikation(self):
        self.service._i_nat = AsyncMock(side_effect=[
            [],
            [{"wissenschaftlich": "Hydrangea macrophylla",
              "deutsch": "Bauernhortensie", "bestaetigt": True,
              "quellen": ["iNaturalist"]}],
        ])
        self.service._wikidata = AsyncMock(return_value=[
            {"wissenschaftlich": "Hydrangea macrophylla",
             "deutsch": "Gartenhortensie", "bestaetigt": False,
             "quellen": ["Wikidata"], "wikidata_id": "Q123"}
        ])
        result = await self.service.async_suchen("Bauernhortensie")
        self.assertEqual(result["pflanzen"][0]["wissenschaftlich"],
                         "Hydrangea macrophylla")
        self.assertTrue(result["pflanzen"][0]["bestaetigt"])
        self.assertEqual(
            set(result["pflanzen"][0]["quellen"]), {"Wikidata", "iNaturalist"}
        )

    async def test_rueckfall_wenn_ein_anbieter_ausfaellt(self):
        self.service._i_nat = AsyncMock(return_value=[
            {"wissenschaftlich": "Solanum lycopersicum",
             "deutsch": "Tomate", "bestaetigt": True,
             "quellen": ["iNaturalist"]}
        ])
        self.service._wikidata = AsyncMock(side_effect=OSError("offline"))
        result = await self.service.async_suchen("Tomate")
        self.assertEqual(len(result["pflanzen"]), 1)
        self.assertIn("Wikidata vorübergehend nicht verfügbar",
                      result["quellenstatus"])

    async def test_keine_art_erfinden_bei_komplettausfall(self):
        self.service._i_nat = AsyncMock(side_effect=OSError("offline"))
        self.service._wikidata = AsyncMock(side_effect=RuntimeError("offline"))
        result = await self.service.async_suchen("Bauernhortensie")
        self.assertEqual(result["pflanzen"], [])
        self.assertEqual(len(result["quellenstatus"]), 2)

    async def test_cache_verhindert_unnoetige_requests(self):
        self.service._i_nat = AsyncMock(return_value=[])
        self.service._wikidata = AsyncMock(return_value=[])
        await self.service.async_suchen("Tomate")
        await self.service.async_suchen("tomate")
        self.service._i_nat.assert_awaited_once()
        self.service._wikidata.assert_awaited_once()

    async def test_zu_kurze_und_zu_lange_queries_werden_blockiert(self):
        for term in ("a", "x" * 81, ""):
            with self.subTest(term=term), self.assertRaises(ValueError):
                await self.service.async_suchen(term)

    async def test_unbestätigter_wikidata_kandidat_bleibt_unbestätigt(self):
        self.service._i_nat = AsyncMock(side_effect=[
            [],
            [{"wissenschaftlich": "Hydrangea paniculata",
              "deutsch": "Rispenhortensie", "bestaetigt": True,
              "quellen": ["iNaturalist"]}],
        ])
        self.service._wikidata = AsyncMock(return_value=[
            {"wissenschaftlich": "Hydrangea macrophylla",
             "deutsch": "Gartenhortensie", "bestaetigt": False,
             "quellen": ["Wikidata"]}
        ])
        result = await self.service.async_suchen("Bauernhortensie")
        self.assertFalse(result["pflanzen"][0]["bestaetigt"])

    async def test_parallele_queries_gleiche_art_ohne_doppelte_anfragen(self):
        self.service._i_nat = AsyncMock(return_value=[])
        self.service._wikidata = AsyncMock(return_value=[])
        await asyncio.gather(
            self.service.async_suchen("Tomate"),
            self.service.async_suchen("Tomate"),
        )
        self.service._i_nat.assert_awaited_once()

    async def test_wikidata_validierungsfehler_bricht_gesamtsuche_nicht_ab(self):
        self.service._i_nat = AsyncMock(side_effect=[[], OSError("offline")])
        self.service._wikidata = AsyncMock(return_value=[
            {"wissenschaftlich": "Hydrangea macrophylla",
             "deutsch": "Gartenhortensie", "bestaetigt": False,
             "quellen": ["Wikidata"]}
        ])
        result = await self.service.async_suchen("Bauernhortensie")
        self.assertEqual(result["pflanzen"][0]["wissenschaftlich"],
                         "Hydrangea macrophylla")
        self.assertFalse(result["pflanzen"][0]["bestaetigt"])




class TestLokalerNamenscache(unittest.IsolatedAsyncioTestCase):
    async def test_erfolgreicher_deutscher_name_ueberlebt_neustart_und_apiausfall(self):
        import sys
        import types
        from copy import deepcopy

        class FakeStore:
            saved = None

            def __init__(self, *_args):
                pass

            async def async_load(self):
                return deepcopy(type(self).saved)

            async def async_save(self, data):
                type(self).saved = deepcopy(data)

        storage = types.ModuleType("homeassistant.helpers.storage")
        storage.Store = FakeStore
        FakeStore.saved = None
        with patch.dict(sys.modules, {"homeassistant.helpers.storage": storage}):
            first = Pflanzensuche(object())
            await first.async_laden()
            first._i_nat = AsyncMock(return_value=[{
                "wissenschaftlich": "Hydrangea macrophylla",
                "deutsch": "Bauernhortensie", "bestaetigt": True,
                "quellen": ["iNaturalist"],
            }])
            first._wikidata = AsyncMock(return_value=[])
            first._gbif = AsyncMock(return_value=[])
            resultat = await first.async_suchen("Bauernhortensie")
            self.assertEqual(len(resultat["pflanzen"]), 1)
            self.assertIsNotNone(FakeStore.saved)

            second = Pflanzensuche(object())
            await second.async_laden()
            second._i_nat = AsyncMock(side_effect=OSError("offline"))
            second._wikidata = AsyncMock(side_effect=OSError("offline"))
            second._gbif = AsyncMock(side_effect=OSError("offline"))
            offline = await second.async_suchen("bauernhor")
            self.assertEqual(offline["pflanzen"][0]["wissenschaftlich"],
                             "Hydrangea macrophylla")
            self.assertIn("lokalem Cache", " ".join(offline["quellenstatus"]))

    async def test_fehlsuche_wird_nicht_persistent_gespeichert(self):
        import sys
        import types

        class FakeStore:
            saved = None
            def __init__(self, *_args):
                pass
            async def async_load(self):
                return None
            async def async_save(self, value):
                type(self).saved = value

        FakeStore.saved = None
        storage = types.ModuleType("homeassistant.helpers.storage")
        storage.Store = FakeStore
        with patch.dict(sys.modules, {"homeassistant.helpers.storage": storage}):
            service = Pflanzensuche(object())
            await service.async_laden()
            service._i_nat = AsyncMock(side_effect=OSError("offline"))
            service._wikidata = AsyncMock(side_effect=OSError("offline"))
            service._gbif = AsyncMock(side_effect=OSError("offline"))
            self.assertEqual((await service.async_suchen("nichtgefunden"))["pflanzen"], [])
            self.assertIsNone(FakeStore.saved)


if __name__ == "__main__":
    unittest.main()
