"""Integrationsnaher HA-Store-Test ohne importiertes Home Assistant.

Mockt ausschließlich Storage und Dispatcher; prüft die echte Backend-Klasse
samt atomarem Speichervorgang und Schreibfehler-Rollback.
"""
import asyncio
from copy import deepcopy
import sys
import types
import unittest
from unittest.mock import patch

from custom_components.mein_garten import GartenBackend
from custom_components.mein_garten.const import SIGNAL_UPDATED
from custom_components.mein_garten.model import DatensatzFehler, GartenDaten


class FakeStore:
    persistent = None
    should_fail = False

    def __init__(self, hass, version, key):
        self.hass = hass
        self.version = version
        self.key = key

    async def async_load(self):
        return deepcopy(type(self).persistent)

    async def async_save(self, value):
        await asyncio.sleep(0)
        if type(self).should_fail:
            raise OSError("Beabsichtigter Schreibfehler im Test")
        type(self).persistent = deepcopy(value)


class TestHABackendAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeStore.persistent = None
        FakeStore.should_fail = False
        self.signale = []

        storage = types.ModuleType("homeassistant.helpers.storage")
        storage.Store = FakeStore
        dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
        signals = self.signale
        dispatcher.async_dispatcher_send = lambda hass, signal: signals.append(signal)
        helpers = types.ModuleType("homeassistant.helpers")
        ha = types.ModuleType("homeassistant")

        self.modules = patch.dict(sys.modules, {
            "homeassistant": ha,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.storage": storage,
            "homeassistant.helpers.dispatcher": dispatcher,
        })
        self.modules.start()
        self.backend = GartenBackend(object())
        await self.backend.async_laden()

    async def asyncTearDown(self):
        self.modules.stop()

    async def test_persistente_pflanzen_und_bereiche(self):
        area = await self.backend.async_aendern("bereich_anlegen", name="Gemüsebeet")
        plant = await self.backend.async_aendern(
            "pflanze_anlegen",
            name="Tomate",
            wissenschaftlich="Solanum lycopersicum",
            bereich_id=area["id"],
        )
        self.assertEqual(len(FakeStore.persistent["pflanzen"]), 1)
        self.assertEqual(plant["bereich_id"], area["id"])
        restarted = GartenBackend(object())
        await restarted.async_laden()
        self.assertEqual(self.backend.snapshot(), restarted.snapshot())

    async def test_ungueltige_aenderung_schreibt_nichts(self):
        old = self.backend.snapshot()
        with self.assertRaises(DatensatzFehler):
            await self.backend.async_aendern("pflanze_anlegen", name="")
        self.assertEqual(self.backend.snapshot(), old)
        self.assertIsNone(FakeStore.persistent)
        self.assertEqual(self.signale, [])

    async def test_speicherfehler_keine_halbfertigen_daten(self):
        await self.backend.async_aendern("bereich_anlegen", name="Garten")
        old = self.backend.snapshot()
        FakeStore.should_fail = True
        with self.assertRaises(OSError):
            await self.backend.async_aendern("bereich_anlegen", name="Terrasse")
        self.assertEqual(self.backend.snapshot(), old)
        self.assertEqual(FakeStore.persistent, old)
        self.assertEqual(self.signale, [SIGNAL_UPDATED])

    async def test_nicht_erlaubte_operation(self):
        with self.assertRaises(ValueError):
            await self.backend.async_aendern("__class__")
        self.assertIsNone(FakeStore.persistent)

    async def test_live_signal_nach_speichern(self):
        await self.backend.async_aendern("bereich_anlegen", name="Hochbeet")
        self.assertEqual(self.signale, [SIGNAL_UPDATED])

    async def test_beschaedigtes_altformat_wird_nicht_ueberschrieben(self):
        FakeStore.persistent = {"version": 99}
        other = GartenBackend(object())
        with self.assertRaises(DatensatzFehler):
            await other.async_laden()
        self.assertEqual(FakeStore.persistent, {"version": 99})

    async def test_parallele_aenderungen_werden_serialisiert(self):
        async def add(i):
            return await self.backend.async_aendern("bereich_anlegen", name=f"Bereich {i}")
        await asyncio.gather(*(add(i) for i in range(12)))
        self.assertEqual(len(self.backend.snapshot()["bereiche"]), 12)
        self.assertEqual(len(FakeStore.persistent["bereiche"]), 12)


if __name__ == "__main__":
    unittest.main()
