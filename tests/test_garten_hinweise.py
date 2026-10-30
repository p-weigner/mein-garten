"""Isolierte Tests der optionalen Garten-Frost- und Wochenbenachrichtigungen."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import sys
import types
import unittest
from unittest.mock import patch

from custom_components.mein_garten.hinweise import (
    GartenHinweise, prognose_minimum, pruefe_einstellungen, wochen_text,
)


class TestWetterUndEinstellungen(unittest.TestCase):
    def test_schalter_ohne_empfaenger_verboten(self):
        with self.assertRaisesRegex(ValueError, "Empfänger"):
            pruefe_einstellungen({
                "weather_entity": "weather.garten",
                "notify_target": "",
                "freitag_aktiv": True,
                "frost_aktiv": False,
                "frost_grenze_c": 2,
            })

    def test_nur_notify_und_weather_als_ziel(self):
        for wrong in ("script.turn_on", "notify.abc;rm", "notify.foo/bar", "http://local"):
            with self.subTest(target=wrong), self.assertRaises(ValueError):
                pruefe_einstellungen({
                    "weather_entity": "weather.home", "notify_target": wrong,
                    "freitag_aktiv": False, "frost_aktiv": False, "frost_grenze_c": 2,
                })

    def test_grenzwert_und_booleans(self):
        valid = {
            "weather_entity": "weather.home",
            "notify_target": "notify.angelinas_iphone_15_pro",
            "freitag_aktiv": False,
            "frost_aktiv": True,
            "frost_grenze_c": 2.0,
        }
        self.assertEqual(pruefe_einstellungen(valid)["frost_grenze_c"], 2.0)
        for invalid in (float("nan"), 10.0, -6, "2", True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                pruefe_einstellungen({**valid, "frost_grenze_c": invalid})
        with self.assertRaises(ValueError):
            pruefe_einstellungen({**valid, "frost_aktiv": 1})

    def test_stuendliche_48h_prognose(self):
        now = datetime.fromisoformat("2026-10-30T12:00:00+01:00")
        payload = {"weather.home": {"forecast": [
            {"datetime": "2026-10-30T10:00:00+01:00", "temperature": -15},  # vorbei
            {"datetime": "2026-10-30T21:00:00+01:00", "temperature": 0.5},
            {"datetime": "2026-11-05T21:00:00+01:00", "temperature": -20},
            {"datetime": "2026-10-31T08:00:00+01:00", "temperature": 1},
        ]}}
        result = prognose_minimum(payload, "weather.home", now)
        self.assertAlmostEqual(result[1], 0.5)

    def test_fahrenheit_umrechnung(self):
        now = datetime.fromisoformat("2026-10-30T12:00:00+01:00")
        payload = {"weather.home": {"forecast": [
            {"datetime": "2026-10-30T21:00:00+01:00", "temperature": 32},
        ]}}
        self.assertAlmostEqual(prognose_minimum(
            payload, "weather.home", now, "°F",
        )[1], 0)

    def test_tages_minimum_statt_tagesmaximum(self):
        now = datetime.fromisoformat("2026-10-30T12:00:00+01:00")
        payload = {"weather.home": {"forecast": [
            {"datetime": "2026-10-31T00:00:00+01:00", "temperature": 13, "templow": -2},
        ]}}
        self.assertEqual(prognose_minimum(
            payload, "weather.home", now, typ="daily",
        )[1], -2)

    def test_ungueltige_daten_erzeugen_keine_warnung(self):
        now = datetime.fromisoformat("2026-10-30T12:00:00+01:00")
        self.assertIsNone(prognose_minimum({
            "weather.home": {"forecast": [
                {"datetime": "2026-10-31T00:00:00", "temperature": -1},
                {"datetime": "2026-10-31T01:00:00+01:00", "temperature": True},
                {"datetime": "2026-10-31T02:00:00+01:00", "temperature": "1.0"},
            ]}
        }, "weather.home", now))

    def test_wochenbericht_aus_gespeicherten_aufgaben(self):
        daten = {
            "pflanzen": [{"id": "p1", "name": "Lavendel"}],
            "aufgaben": [
                {"name": "Zustand prüfen", "pflanzen_id": "p1",
                 "status": "offen", "faellig_am": "2026-11-02"},
                {"name": "Langfristig", "status": "offen", "faellig_am": "2027-12-01"},
                {"name": "Fertig", "status": "erledigt", "faellig_am": "2026-11-01"},
            ],
        }
        text = wochen_text(daten, date(2026, 10, 30))
        self.assertIn("Zustand prüfen", text)
        self.assertIn("Lavendel", text)
        self.assertNotIn("Langfristig", text)
        self.assertNotIn("Fertig", text)


class MemoryStore:
    saved = None
    def __init__(self, *_args):
        pass
    async def async_load(self):
        return deepcopy(self.saved)
    async def async_save(self, value):
        self.saved = deepcopy(value)


class FakeServices:
    def __init__(self):
        self.calls = []
        self.available = {("notify", "send_message"), ("notify", "mobile_app_angelina"),
                          ("weather", "get_forecasts")}
        self.forecast = {"weather.home": {"forecast": [
            {"datetime": "2026-10-30T20:00:00+01:00", "temperature": -1.0},
        ]}}

    def has_service(self, domain, service):
        return (domain, service) in self.available

    async def async_call(self, domain, service, data, **kwargs):
        self.calls.append((domain, service, deepcopy(data), kwargs))
        if domain == "weather":
            return deepcopy(self.forecast)
        return None


class TestBenachrichtigungen(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        storage = types.ModuleType("homeassistant.helpers.storage")
        storage.Store = MemoryStore
        dt = types.ModuleType("homeassistant.util.dt")
        dt.as_local = lambda value: value.astimezone(timezone.utc)
        util = types.ModuleType("homeassistant.util")
        util.dt = dt
        self.modules = patch.dict(sys.modules, {
            "homeassistant.helpers.storage": storage,
            "homeassistant.util": util,
            "homeassistant.util.dt": dt,
        })
        self.modules.start()
        self.services = FakeServices()
        self.states = {
            "weather.home": types.SimpleNamespace(
                state="cloudy", attributes={"temperature_unit": "°C"}),
            "notify.angelina": types.SimpleNamespace(state="2026-10-30", attributes={}),
        }
        self.hass = types.SimpleNamespace(
            states=types.SimpleNamespace(get=self.states.get),
            services=self.services,
        )
        self.geplante_frostpruefungen = []
        async def registrieren(datum, temperatur, schwelle):
            self.geplante_frostpruefungen.append((datum, temperatur, schwelle))
            return True
        self.backend = types.SimpleNamespace(
            snapshot=lambda: {"pflanzen": [], "aufgaben": []},
            async_frostpruefung_anlegen=registrieren,
        )
        self.hinweise = GartenHinweise(self.hass, self.backend)
        MemoryStore.saved = None
        self.jetzt = datetime.fromisoformat("2026-10-30T15:00:00+00:00")

    async def asyncTearDown(self):
        self.modules.stop()

    async def test_ab_werk_ausgeschaltet(self):
        self.assertFalse(await self.hinweise.async_frost_pruefen(self.jetzt))
        self.assertFalse(await self.hinweise.async_freitagsbericht(self.jetzt))
        self.assertEqual(self.services.calls, [])

    async def test_freitag_genau_einmal(self):
        await self.hinweise.async_einstellungen_speichern({
            "weather_entity": "", "notify_target": "notify.angelina",
            "freitag_aktiv": True, "frost_aktiv": False, "frost_grenze_c": 2,
        })
        self.assertTrue(await self.hinweise.async_freitagsbericht(self.jetzt))
        self.assertFalse(await self.hinweise.async_freitagsbericht(self.jetzt))
        self.assertEqual(len(self.services.calls), 1)
        self.assertEqual(self.services.calls[0][1], "send_message")
        self.assertEqual(self.services.calls[0][3]["target"], {"entity_id": "notify.angelina"})

    async def test_frost_prognose_48h_und_duplikate(self):
        await self.hinweise.async_einstellungen_speichern({
            "weather_entity": "weather.home",
            "notify_target": "notify.mobile_app_angelina",
            "freitag_aktiv": False, "frost_aktiv": True, "frost_grenze_c": 2,
        })
        self.assertTrue(await self.hinweise.async_frost_pruefen(self.jetzt))
        self.assertFalse(await self.hinweise.async_frost_pruefen(self.jetzt))
        actions = [c for c in self.services.calls if c[0] == "notify"]
        self.assertEqual(len(actions), 1)
        self.assertIn("etwa -1.0 °C", actions[0][2]["message"])
        self.assertEqual(len(self.geplante_frostpruefungen), 1)
        self.assertEqual(self.geplante_frostpruefungen[0][1], -1)
        weather_calls = [c for c in self.services.calls if c[0] == "weather"]
        self.assertEqual(weather_calls[0][3]["target"], {"entity_id": "weather.home"})

    async def test_neustart_keine_erneute_frostwarnung(self):
        await self.hinweise.async_einstellungen_speichern({
            "weather_entity": "weather.home", "notify_target": "notify.mobile_app_angelina",
            "freitag_aktiv": False, "frost_aktiv": True, "frost_grenze_c": 2,
        })
        await self.hinweise.async_frost_pruefen(self.jetzt)
        reloaded = GartenHinweise(self.hass, self.backend)
        reloaded._store = self.hinweise._store
        await reloaded.async_laden()
        self.assertFalse(await reloaded.async_frost_pruefen(self.jetzt))

    async def test_nicht_verfuegbare_wetterquelle_sendet_nichts(self):
        await self.hinweise.async_einstellungen_speichern({
            "weather_entity": "weather.fehlt", "notify_target": "notify.mobile_app_angelina",
            "freitag_aktiv": False, "frost_aktiv": True, "frost_grenze_c": 2,
        })
        self.assertFalse(await self.hinweise.async_frost_pruefen(self.jetzt))
        self.assertEqual(self.services.calls, [])


if __name__ == "__main__":
    unittest.main()
