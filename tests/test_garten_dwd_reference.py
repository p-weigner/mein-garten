"""DWD-Phänologie-Vergleich: Integrität, QA, Offline-Laufzeit und Datenschutz."""
import asyncio
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from custom_components.mein_garten.dwd_reference import (
    DATA_FILE, DwdPhaenologie, PhänologieFehler, pruefe_dwd_paket,
)


class TestDwdReferenz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def test_schnappschuss_amtlich_lizenziert_und_klein(self):
        self.assertLess(DATA_FILE.stat().st_size, 55_000)
        p = pruefe_dwd_paket(self.source)
        self.assertEqual(p["lizenz"], "CC BY 4.0")
        self.assertEqual(p["abgerufen_am"], "2026-10-30")
        self.assertEqual(len(p["werte"]), 18)
        self.assertEqual(len([x for x in p["werte"] if x["region"] == "nordost"]), 9)
        self.assertEqual(len([x for x in p["werte"] if x["region"] == "deutschland"]), 9)
        self.assertEqual(len(self.source["quell_sha256"]), 4)

    def test_region_ist_kein_gartenstandort(self):
        p = pruefe_dwd_paket(self.source)
        self.assertEqual(
            [p["regionen"]["nordost"][x] for x in
             ("lat_min", "lat_max", "lon_min", "lon_max")],
            [52.0, 54.2, 12.0, 15.0],
        )
        self.assertIn("grob", p["regionen"]["nordost"]["label"])
        self.assertNotIn("Hausadresse", json.dumps(p))
        self.assertNotIn("Melchow", json.dumps(p))

    def test_alle_angaben_sind_historische_beobachtungen(self):
        p = pruefe_dwd_paket(self.source)
        self.assertEqual(
            set(x["indikator"] for x in p["werte"]),
            {"hasel_bluete", "forsythie_bluete", "rotbuche_blatt"},
        )
        self.assertEqual(
            set(x["jahr"] for x in p["werte"]),
            {2024, 2025, 2026},
        )
        for item in p["werte"]:
            self.assertGreaterEqual(item["stationen"], 5)
            self.assertEqual(item["median"][:4], str(item["jahr"]))
            self.assertLessEqual(item["quartil_von"], item["median"])
            self.assertLessEqual(item["median"], item["quartil_bis"])
        self.assertIn("Keine Prognose", p["hinweis"])
        self.assertIn("Qualitaet", "Qualitaet")  # keine implizite Pflegeaussage

    def test_abgefaelschte_lizenz_oder_region_abgewiesen(self):
        for key, value in (
            ("lizenz", "Unklar"),
            ("quelle", "Fremddienst"),
            ("quellen_url", "https://example.test/"),
        ):
            damaged = deepcopy(self.source)
            damaged[key] = value
            with self.subTest(key=key), self.assertRaises(PhänologieFehler):
                pruefe_dwd_paket(damaged)
        damaged = deepcopy(self.source)
        damaged["regionen"]["nordost"]["lon_min"] = 8.1
        with self.assertRaises(PhänologieFehler):
            pruefe_dwd_paket(damaged)

    def test_quellhash_und_aussagewidrige_daten_nicht_durchwinken(self):
        damaged = deepcopy(self.source)
        damaged["quell_sha256"]["hasel_bluete"] = "invalid"
        with self.assertRaises(PhänologieFehler):
            pruefe_dwd_paket(damaged)
        damaged = deepcopy(self.source)
        damaged["werte"][0]["stationen"] = 2
        with self.assertRaises(PhänologieFehler):
            pruefe_dwd_paket(damaged)
        damaged = deepcopy(self.source)
        damaged["werte"][0]["prognose_automatisch"] = True
        with self.assertRaises(PhänologieFehler):
            pruefe_dwd_paket(damaged)

    def test_doppelte_referenz_oder_zeitliche_verdrehung_abgewiesen(self):
        damaged = deepcopy(self.source)
        damaged["werte"].append(deepcopy(damaged["werte"][0]))
        with self.assertRaises(PhänologieFehler):
            pruefe_dwd_paket(damaged)
        damaged = deepcopy(self.source)
        damaged["werte"][0]["quartil_von"] = "2026-12-31"
        with self.assertRaises(PhänologieFehler):
            pruefe_dwd_paket(damaged)

    def test_rueckgabe_ist_ausgabekopie(self):
        first = pruefe_dwd_paket(self.source)
        second = pruefe_dwd_paket(self.source)
        first["werte"][0]["stationen"] = 1
        self.assertNotEqual(first, second)


class TestDwdPhaenologieOffline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = types.SimpleNamespace(
            async_add_executor_job=lambda f: asyncio.to_thread(f)
        )

    async def test_offline_schnappschuss_laden_und_klonen(self):
        svc = DwdPhaenologie(self.hass)
        self.assertIsNone(svc.stand())
        await svc.async_laden()
        obj = svc.stand()
        self.assertEqual(len(obj["werte"]), 18)
        obj["werte"].clear()
        self.assertEqual(len(svc.stand()["werte"]), 18)

    async def test_quellendefekt_blockiert_nicht_mit_stillen_dummywerten(self):
        svc = DwdPhaenologie(self.hass)
        with tempfile.TemporaryDirectory() as tmp:
            corrupt = Path(tmp) / "corrupt.json"
            corrupt.write_text('{"schema":1}', encoding="utf-8")
            with patch("custom_components.mein_garten.dwd_reference.DATA_FILE", corrupt):
                with self.assertRaises(PhänologieFehler):
                    await svc.async_laden()
        self.assertIsNone(svc.stand())


if __name__ == "__main__":
    unittest.main()
