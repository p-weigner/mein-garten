"""WebSocket-Verhalten mit simuliertem Home Assistant (keine Live-Installation)."""
import asyncio
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from custom_components.mein_garten.model import GartenDaten


class FakeBackend:
    def __init__(self):
        self.model = GartenDaten()
        self.calls = []

    def snapshot(self):
        return self.model.snapshot()

    async def async_aendern(self, method, **params):
        self.calls.append((method, params))
        return getattr(self.model, method)(**params)


class FakeConnection:
    def __init__(self):
        self.results = []
        self.errors = []
        self.events = []
        self.subscriptions = {}
        self.user = types.SimpleNamespace(name="Angelina", id="user-1")

    def send_result(self, id, result=None):
        self.results.append((id, result))

    def send_error(self, id, code, message):
        self.errors.append((id, code, message))

    def send_event(self, id, event):
        self.events.append((id, event))


class TestGartenWebsocket(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        vol = types.ModuleType("voluptuous")
        vol.Required = lambda key, **kwargs: key
        vol.Optional = lambda key, **kwargs: key
        vol.Any = lambda *args, **kwargs: args
        ws = types.ModuleType("homeassistant.components.websocket_api")
        ws.websocket_command = lambda schema: (lambda f: f)
        ws.async_response = lambda f: f
        self.registered = []
        self.registered_ref = self.registered
        ws.async_register_command = lambda hass, handler: self.registered.append(handler)
        components = types.ModuleType("homeassistant.components")
        components.websocket_api = ws
        core = types.ModuleType("homeassistant.core")
        core.callback = lambda f: f
        dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
        self.dispatch = []
        def connect(hass, signal, callback):
            self.dispatch.append((signal, callback))
            return lambda: self.dispatch.remove((signal, callback))
        dispatcher.async_dispatcher_connect = connect
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.dispatcher = dispatcher
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.components = components
        homeassistant.core = core
        homeassistant.helpers = helpers
        self.modules = patch.dict(sys.modules, {
            "voluptuous": vol,
            "homeassistant": homeassistant,
            "homeassistant.components": components,
            "homeassistant.components.websocket_api": ws,
            "homeassistant.core": core,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.dispatcher": dispatcher,
        })
        self.modules.start()
        sys.modules.pop("custom_components.mein_garten.api", None)
        self.api = importlib.import_module("custom_components.mein_garten.api")
        self.backend = FakeBackend()
        self.search = types.SimpleNamespace(async_suchen=AsyncMock(return_value={
            "suchbegriff": "Bauernhortensie",
            "pflanzen": [{
                "wissenschaftlich": "Hydrangea macrophylla",
                "deutsch": "Gartenhortensie",
                "bestaetigt": True,
            }],
            "quellenstatus": [],
        }))
        self.hass = types.SimpleNamespace(
            data={"mein_garten": {"backend": self.backend, "suche": self.search}}
        )
        self.connection = FakeConnection()

    async def asyncTearDown(self):
        sys.modules.pop("custom_components.mein_garten.api", None)
        self.modules.stop()

    async def test_alle_befehle_registriert(self):
        self.api.registriere_ws_befehle(self.hass)
        self.assertGreaterEqual(len(self.registered), 13)
        self.assertIn(self.api.ws_pflanzen_suchen, self.registered)
        self.assertIn(self.api.ws_subscribe, self.registered)

    async def test_startzustand(self):
        self.api.ws_get(self.hass, self.connection, {"id": 1})
        self.assertEqual(self.connection.results[0][1]["version"], 1)
        self.assertEqual(self.connection.results[0][1]["daten"]["pflanzen"], [])

    async def test_deutsche_pflanzensuche_erfolgreich(self):
        await self.api.ws_pflanzen_suchen(self.hass, self.connection, {
            "id": 2, "suchbegriff": "Bauernhortensie",
        })
        self.search.async_suchen.assert_awaited_once_with("Bauernhortensie")
        self.assertEqual(
            self.connection.results[0][1]["pflanzen"][0]["wissenschaftlich"],
            "Hydrangea macrophylla",
        )

    async def test_ungueltige_suche_sendet_fehler(self):
        self.search.async_suchen.side_effect = ValueError("Suchbegriff zu kurz")
        await self.api.ws_pflanzen_suchen(self.hass, self.connection, {
            "id": 2, "suchbegriff": "a",
        })
        self.assertEqual(self.connection.errors[0][1], "ungueltige_eingabe")

    async def test_suche_ohne_backend_verweigert(self):
        self.hass.data["mein_garten"].pop("backend")
        await self.api.ws_pflanzen_suchen(self.hass, self.connection, {
            "id": 3, "suchbegriff": "Hortensie",
        })
        self.assertEqual(self.connection.errors[0][1], "nicht_eingerichtet")

    async def test_backendfehler_nicht_an_browser_weitergeben(self):
        self.search.async_suchen.side_effect = RuntimeError("Secret=veryprivate")
        await self.api.ws_pflanzen_suchen(self.hass, self.connection, {
            "id": 4, "suchbegriff": "Hortensie",
        })
        self.assertEqual(self.connection.errors[0][1], "suchfehler")
        self.assertNotIn("veryprivate", self.connection.errors[0][2])

    async def test_bereich_anlegen_als_lesbarer_datensatz(self):
        await self.api.ws_bereich_anlegen(self.hass, self.connection, {
            "id": 5, "name": "Hochbeet",
        })
        response = self.connection.results[0][1]
        self.assertEqual(response["objekt"]["name"], "Hochbeet")
        self.assertEqual(len(response["daten"]["bereiche"]), 1)

    async def test_doppelte_bereichsnamen_werden_abgelehnt(self):
        await self.api.ws_bereich_anlegen(self.hass, self.connection, {
            "id": 5, "name": "Hochbeet",
        })
        await self.api.ws_bereich_anlegen(self.hass, self.connection, {
            "id": 6, "name": "Hochbeet",
        })
        self.assertEqual(self.connection.errors[0][1], "ungueltige_eingabe")

    async def test_pflanze_anlegen_ohne_area(self):
        await self.api.ws_pflanze_anlegen(self.hass, self.connection, {
            "id": 7, "name": "Neue Pfingstrose",
            "wissenschaftlich": "Paeonia lactiflora",
        })
        self.assertEqual(
            self.connection.results[0][1]["objekt"]["wissenschaftlich"],
            "Paeonia lactiflora",
        )

    async def test_erledigung_zeichnet_benutzer_auf(self):
        task = self.backend.model.aufgabe_anlegen("Gießen")
        await self.api.ws_aufgabe_erledigen(self.hass, self.connection, {
            "id": 8, "aufgaben_id": task["id"],
        })
        self.assertEqual(
            self.backend.model.snapshot()["historie"][0]["person"],
            "Angelina",
        )

    async def test_live_subscription_und_unsubscribe(self):
        self.api.ws_subscribe(self.hass, self.connection, {"id": 9})
        self.assertEqual(len(self.connection.results), 1)
        self.assertEqual(len(self.connection.events), 1)
        self.assertIn(9, self.connection.subscriptions)
        self.backend.model.bereich_anlegen("Terrasse")
        _, callback = self.dispatch[0]
        callback()
        self.assertEqual(len(self.connection.events), 2)
        self.assertEqual(len(self.connection.events[-1][1]["daten"]["bereiche"]), 1)
        self.connection.subscriptions[9]()
        self.assertEqual(self.dispatch, [])


if __name__ == "__main__":
    unittest.main()
