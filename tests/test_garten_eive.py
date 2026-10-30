"""EIVE CC-BY-Standortwissen: Quelle, Taxonomie, HA-Green-Offlinebetrieb."""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from custom_components.mein_garten.eive import (
    FILE, B64_SHA256, GZIP_SHA256, JSON_SHA256, SOURCE_MD5,
    DOI, LICENSE, EiveFehler, EiveEuropaService, _lade_offline, pruefe_eive_katalog,
)


class TestEiveAuthentizitaet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base64_bytes = FILE.read_bytes().strip()
        cls.compressed = base64.b64decode(cls.base64_bytes, validate=True)
        cls.rawbytes = gzip.decompress(cls.compressed)
        cls.data = json.loads(cls.rawbytes)
        cls.index = pruefe_eive_katalog(cls.data)

    def test_europa_datensatz_original_hash_und_lizenz(self):
        self.assertLess(FILE.stat().st_size, 300000)
        self.assertEqual(hashlib.sha256(self.base64_bytes).hexdigest(), B64_SHA256)
        self.assertEqual(hashlib.sha256(self.compressed).hexdigest(), GZIP_SHA256)
        self.assertEqual(hashlib.sha256(self.rawbytes).hexdigest(), JSON_SHA256)
        self.assertEqual(self.data["original_md5"], SOURCE_MD5)
        self.assertEqual(self.data["lizenz"], LICENSE)
        self.assertEqual(self.data["doi"], DOI)
        self.assertEqual(len(self.index), 10683)
        self.assertEqual(len(_lade_offline()), 10683)

    def test_exakte_heimische_gehoelze_ohne_ersatzart(self):
        for name in ("carpinus betulus", "corylus avellana", "rubus idaeus",
                     "amelanchier lamarckii", "lavandula angustifolia"):
            with self.subTest(name=name):
                self.assertIn(name, self.index)
                self.assertIn("L", self.index[name])
                self.assertIn("M", self.index[name])
        self.assertNotIn("hydrangea macrophylla", self.index)
        self.assertNotIn("rosa", self.index)

    def test_fuer_50_typische_pflanzen_mindestens_30_echte_europawerte(self):
        benchmark = json.loads(
            (Path(__file__).resolve().parent.parent / "daten" /
             "pflanzensuche_50_de.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(benchmark), 50)
        found = [self.index.get(p["wissenschaftlich"].casefold())
                 for p in benchmark]
        # Im exakt geprüften, finalen CC-BY-Snapshot sind 36 von 50 Arten
        # direkt und ohne Synonymerkennung oder Sonderfalllisten enthalten.
        self.assertEqual(sum(x is not None for x in found), 36)

    def test_widerspruechliche_belege_daten_und_lizenzen_werden_abgewiesen(self):
        cases = [
            lambda raw: raw.__setitem__("lizenz", "geschlossen"),
            lambda raw: raw.__setitem__("doi", "andere-doi"),
            lambda raw: raw["arten"][0].__setitem__(0, "Rosa"),
            lambda raw: raw["arten"][0].__setitem__(1, 99),
            lambda raw: raw["arten"][0].__setitem__(2, 0),
            lambda raw: raw["arten"].append(deepcopy(raw["arten"][0])),
            lambda raw: raw.__setitem__("pflegeaufgaben", True),
        ]
        for change in cases:
            with self.subTest(change=str(change)):
                raw = deepcopy(self.data)
                change(raw)
                with self.assertRaises(EiveFehler):
                    pruefe_eive_katalog(raw)

    def test_manipuliertes_dateiarchiv_ausdruecklich_gesperrt(self):
        with tempfile.TemporaryDirectory() as td:
            damaged = Path(td) / "eive.b64"
            damaged.write_bytes(b"not-a-valid-archive")
            with patch("custom_components.mein_garten.eive.FILE", damaged):
                with self.assertRaises(EiveFehler):
                    _lade_offline()


class TestEiveOfflineService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = types.SimpleNamespace(
            async_add_executor_job=lambda f: asyncio.to_thread(f)
        )
        self.service = EiveEuropaService(self.hass)
        await self.service.async_laden()

    async def test_nur_eigene_pflanzen_und_keine_automatischen_pflegevorschlaege(self):
        plants = [
            {"id": "p1", "wissenschaftlich": "Corylus avellana", "notizen": "privat!"},
            {"id": "p2", "wissenschaftlich": "Hydrangea macrophylla"},
            {"id": "p3", "wissenschaftlich": "Corylus"},
        ]
        result = self.service.stand_fuer(plants)
        self.assertEqual(set(result["profile"]), {"p1"})
        self.assertEqual(result["katalog_arten"], 10683)
        self.assertEqual(result["lizenz"], LICENSE)
        self.assertFalse(result["automatische_aufgaben"])
        self.assertTrue(result["profile"]["p1"]["indikatoren"]["L"]["quellsysteme"] >= 1)
        self.assertNotIn("privat!", json.dumps(result))
        self.assertNotIn("pflegeauftrag", json.dumps(result))
        result["profile"]["p1"]["indikatoren"]["L"]["wert"] = -4
        fresh = self.service.stand_fuer(plants)
        self.assertGreaterEqual(fresh["profile"]["p1"]["indikatoren"]["L"]["wert"], 0)

    async def test_exakte_art_prueft_keine_sorten_und_keine_html_eingaben(self):
        plants = [
            {"id": "p1", "wissenschaftlich": "Corylus avellana 'Contorta'"},
            {"id": "p2", "wissenschaftlich": "Corylus avellana<script>"},
            {"id": "p3", "wissenschaftlich": "Corylus avellana"},
        ]
        result = self.service.stand_fuer(plants)
        self.assertEqual(set(result["profile"]), {"p3"})


if __name__ == "__main__":
    unittest.main()
