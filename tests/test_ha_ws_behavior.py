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
        probatio = types.ModuleType("probatio")
        probatio.Required = lambda key, **kwargs: key
        probatio.Optional = lambda key, **kwargs: key
        probatio.Any = lambda *args, **kwargs: args
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
        self.sent_signals = []
        dispatcher.async_dispatcher_send = lambda hass, signal: self.sent_signals.append(signal)
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.dispatcher = dispatcher
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.components = components
        homeassistant.core = core
        homeassistant.helpers = helpers
        self.modules = patch.dict(sys.modules, {
            "probatio": probatio,
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


    async def test_automatik_optionen_ueber_ws_speichern_ohne_push(self):
        options = {
            "weather_entity": "", "notify_target": "",
            "freitag_aktiv": False, "frost_aktiv": False, "frost_grenze_c": 2.0,
        }
        async def speichern(neu):
            options.update(neu)
            return dict(options)
        service = types.SimpleNamespace(
            einstellungen=lambda: dict(options),
            async_einstellungen_speichern=speichern,
        )
        self.hass.data["mein_garten"]["hinweise"] = service
        await self.api.ws_automatik_speichern(self.hass, self.connection, {
            "id": 15, "weather_entity": "weather.home",
            "notify_target": "notify.mobile_app_angelina",
            "freitag_aktiv": True, "frost_aktiv": True, "frost_grenze_c": 2.0,
        })
        self.assertEqual(self.connection.errors, [])
        self.assertTrue(self.connection.results[0][1]["automatik"]["frost_aktiv"])
        self.assertEqual(self.sent_signals, ["mein_garten_updated"])

    async def test_automatik_fehlermeldung_enthaelt_keine_geheimnisse(self):
        async def speichern(_neu):
            raise ValueError("Ungültige Wetterentität")
        self.hass.data["mein_garten"]["hinweise"] = types.SimpleNamespace(
            einstellungen=lambda: {},
            async_einstellungen_speichern=speichern,
        )
        await self.api.ws_automatik_speichern(self.hass, self.connection, {
            "id": 16, "weather_entity": "script.schlafenszeit",
            "notify_target": "notify.mobile_app_angelina",
            "freitag_aktiv": True, "frost_aktiv": True, "frost_grenze_c": 2.0,
        })
        self.assertEqual(self.connection.errors[0][1], "ungueltige_eingabe")
        self.assertFalse(self.connection.results)


    async def test_giessentscheidung_ueber_websocket_als_historie(self):
        task = self.backend.model.aufgabe_anlegen(
            "Tomate kontrollieren", aufgabentyp="giesskontrolle"
        )
        await self.api.ws_aufgabe_erledigen(self.hass, self.connection, {
            "id": 20, "aufgaben_id": task["id"], "ergebnis": "kontrolliert_kein_wasser",
        })
        self.assertEqual(self.connection.errors, [])
        self.assertEqual(self.connection.results[0][1]["objekt"]["ergebnis"],
                         "kontrolliert_kein_wasser")
        self.assertEqual(self.backend.model.snapshot()["historie"][-1]["person"], "Angelina")

    async def test_giesskontrolle_braucht_auswahl_auch_bei_ws(self):
        task = self.backend.model.aufgabe_anlegen(
            "Tomate kontrollieren", aufgabentyp="giesskontrolle"
        )
        await self.api.ws_aufgabe_erledigen(self.hass, self.connection, {
            "id": 21, "aufgaben_id": task["id"],
        })
        self.assertEqual(self.connection.errors[0][1], "ungueltige_eingabe")
        self.assertEqual(self.backend.model.snapshot()["aufgaben"][0]["status"], "offen")


    async def test_saison_ws_stand_zeigt_anker_und_vorschlaege(self):
        class FakeSeason:
            def stand(self):
                return {
                    "anker": {"last_frost": "2027-05-15", "first_frost": ""},
                    "vorschlaege": [], "katalog_arten": 152,
                }
        self.hass.data["mein_garten"]["saison"] = FakeSeason()
        self.api.ws_get(self.hass, self.connection, {"id": 30})
        self.assertEqual(self.connection.results[0][1]["saison"]["katalog_arten"], 152)
        self.assertEqual(self.connection.results[0][1]["saison"]["anker"]["last_frost"],
                         "2027-05-15")

    async def test_saisonanker_ws_valide_speicherung_und_synchronisation(self):
        options = {"last_frost": "", "first_frost": ""}
        async def save(data):
            options.update(data)
            return dict(options)
        self.hass.data["mein_garten"]["saison"] = types.SimpleNamespace(
            stand=lambda: {"anker": dict(options), "vorschlaege": []},
            async_anker_speichern=save,
        )
        await self.api.ws_saisonanker_speichern(self.hass, self.connection, {
            "id": 31, "last_frost": "2027-05-15", "first_frost": "2027-10-15",
        })
        self.assertEqual(self.connection.errors, [])
        self.assertEqual(self.connection.results[0][1]["saison"]["anker"]["first_frost"],
                         "2027-10-15")
        self.assertEqual(self.sent_signals, ["mein_garten_updated"])

    async def test_saisonplanung_ws_nimmt_nur_id_und_datum_an(self):
        plant = self.backend.model.pflanze_anlegen("Tomate", "Solanum lycopersicum")
        expected = {"pflanzen_id": plant["id"], "katalog_id": "tomato",
                    "datum": "2027-03-25"}
        async def plan(plant_id, rule_id, when):
            self.assertEqual({
                "pflanzen_id": plant_id, "katalog_id": rule_id, "datum": when,
            }, expected)
            return {"id": "task1", "name": "Vorziehen prüfen"}
        self.hass.data["mein_garten"]["saison"] = types.SimpleNamespace(
            stand=lambda: {"anker": {}, "vorschlaege": []},
            async_vormerken=plan,
        )
        await self.api.ws_saison_vormerken(self.hass, self.connection, {
            "id": 32, **expected,
        })
        self.assertEqual(self.connection.errors, [])
        self.assertEqual(self.connection.results[0][1]["objekt"]["id"], "task1")

    async def test_saisonplanung_ws_blockiert_manipulierten_termin(self):
        from custom_components.mein_garten.season import SaisonFehler
        async def reject(*_args):
            raise SaisonFehler("Termin liegt außerhalb des gespeicherten Saisonfensters")
        self.hass.data["mein_garten"]["saison"] = types.SimpleNamespace(
            stand=lambda: {"anker": {}, "vorschlaege": []},
            async_vormerken=reject,
        )
        await self.api.ws_saison_vormerken(self.hass, self.connection, {
            "id": 33, "pflanzen_id": "p1", "katalog_id": "tomato",
            "datum": "2050-01-01",
        })
        self.assertEqual(self.connection.errors[0][1], "ungueltige_eingabe")
        self.assertFalse(self.connection.results)


    async def test_entwicklungsphase_per_websocket_speichert_ha_benutzer(self):
        plant = self.backend.model.pflanze_anlegen(
            "Bauernhortensie", "Hydrangea macrophylla"
        )
        await self.api.ws_beobachtung_anlegen(self.hass, self.connection, {
            "id": 41,
            "pflanzen_id": plant["id"],
            "phase": "bluete_beginn",
            "beobachtet_am": "2025-05-11",
            "notiz": "Erste Blüten am Südbeet",
        })
        self.assertFalse(self.connection.errors)
        res = self.connection.results[0][1]
        record = res["objekt"]
        self.assertEqual(record["quelle"], "eigene_beobachtung")
        self.assertEqual(record["person"], "Angelina")
        self.assertEqual(record["wissenschaftlich"], "Hydrangea macrophylla")
        self.assertEqual(res["daten"]["beobachtungen"][0]["id"], record["id"])
        self.assertEqual(self.backend.model.snapshot()["aufgaben"], [])

    async def test_entwicklungsphase_unzulaessig_ohne_neue_art_zu_erfinden(self):
        plant = self.backend.model.pflanze_anlegen("Lavendel", "Lavandula angustifolia")
        await self.api.ws_beobachtung_anlegen(self.hass, self.connection, {
            "id": 42,
            "pflanzen_id": plant["id"],
            "phase": "automatisch_schneiden",
            "beobachtet_am": "2025-05-11",
            "notiz": "",
        })
        self.assertEqual(self.connection.errors[0][1], "ungueltige_eingabe")
        self.assertEqual(self.backend.model.snapshot()["beobachtungen"], [])

    async def test_entwicklungskorrektur_entfernt_beobachtung_und_protokolleintrag(self):
        plant = self.backend.model.pflanze_anlegen("Felsenbirne")
        record = self.backend.model.beobachtung_anlegen(
            plant["id"], "laubfaerbung", "2025-10-11",
            person="Angelina",
        )
        await self.api.ws_beobachtung_entfernen(self.hass, self.connection, {
            "id": 43, "beobachtung_id": record["id"],
        })
        self.assertEqual(self.connection.errors, [])
        self.assertEqual(self.backend.model.snapshot()["beobachtungen"], [])
        self.assertEqual(self.backend.model.snapshot()["historie"], [])

    async def test_beobachtungsdaten_auch_im_live_snapshot(self):
        plant = self.backend.model.pflanze_anlegen("Hortensie")
        self.backend.model.beobachtung_anlegen(
            plant["id"], "austrieb", "2025-04-05"
        )
        self.api.ws_get(self.hass, self.connection, {"id": 44})
        snapshot = self.connection.results[0][1]["daten"]
        self.assertEqual(len(snapshot["beobachtungen"]), 1)
        self.assertIn("beobachtungen", snapshot)
        self.api.registriere_ws_befehle(self.hass)
        self.assertIn(self.api.ws_beobachtung_anlegen, self.registered)
        self.assertIn(self.api.ws_beobachtung_entfernen, self.registered)


    async def test_dwd_phaenologie_ist_reiner_lesewert_im_ws_snapshot(self):
        dwd_data = {
            "quelle": "Deutscher Wetterdienst",
            "lizenz": "CC BY 4.0",
            "werte": [{
                "indikator": "hasel_bluete", "region": "nordost",
                "jahr": 2026, "median": "2026-02-20",
                "stationen": 18,
            }],
        }
        self.hass.data["mein_garten"]["dwd_phaenologie"] = types.SimpleNamespace(
            stand=lambda: dwd_data
        )
        self.api.ws_get(self.hass, self.connection, {"id": 55})
        response = self.connection.results[0][1]
        self.assertEqual(response["dwd_phaenologie"], dwd_data)
        self.assertFalse(self.connection.errors)
        self.api.registriere_ws_befehle(self.hass)
        self.assertFalse(any("dwd" in handler.__name__
                             for handler in self.registered))
        self.assertEqual(self.backend.model.snapshot()["aufgaben"], [])

    async def test_ohne_dwd_quelle_bleibt_garten_ws_verwendbar(self):
        self.api.ws_get(self.hass, self.connection, {"id": 56})
        response = self.connection.results[0][1]
        self.assertIsNone(response["dwd_phaenologie"])
        self.assertEqual(response["daten"]["pflanzen"], [])

    async def test_standort_daten_nur_fuer_eigene_pflanzen_und_read_only(self):
        plant = self.backend.model.pflanze_anlegen(
            "Hundsrose", "Rosa canina"
        )
        captured = []
        def stand_fuer(plants):
            captured.append(plants)
            return {
                "profile": {
                    plant["id"]: {
                        "wissenschaftlich": "Rosa canina",
                        "merkmale": {"sun": "full", "water": "low"},
                    }
                },
                "katalog_arten": 10642,
                "quelle": "OpenPlantDB",
                "lizenz": "CC0 1.0",
            }
        self.hass.data["mein_garten"]["standort"] = types.SimpleNamespace(
            stand_fuer=stand_fuer
        )
        self.api.ws_get(self.hass, self.connection, {"id": 60})
        data = self.connection.results[0][1]["standort"]
        self.assertEqual(data["katalog_arten"], 10642)
        self.assertEqual(data["profile"][plant["id"]]["merkmale"]["sun"], "full")
        self.assertEqual(captured[0], self.backend.snapshot()["pflanzen"])
        self.api.registriere_ws_befehle(self.hass)
        self.assertFalse(any("standort" in handler.__name__
                             for handler in self.registered))
        self.assertEqual(self.backend.snapshot()["aufgaben"], [])

    async def test_ohne_cc0_standortdienst_bleibt_garten_funktionsfaehig(self):
        self.api.ws_get(self.hass, self.connection, {"id": 61})
        response = self.connection.results[0][1]
        self.assertIsNone(response["standort"])
        self.assertEqual(response["daten"]["pflanzen"], [])

if __name__ == "__main__":
    unittest.main()
