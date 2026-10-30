"""Mein Garten – authentifizierte WebSocket-Schnittstelle für die HA-Oberfläche.

Keine externen Zugänge, keine fremden Pflegefreitexte.
Aktuell reine Stammdaten- und Pflegeaufgabenverwaltung.
"""
from __future__ import annotations

import logging
import probatio

from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATED
from .model import DatensatzFehler, PFLANZENGRUPPEN

_LOGGER = logging.getLogger(__name__)


def _backend(hass):
    return hass.data.get(DOMAIN, {}).get("backend")


def _snapshot(backend, hass=None) -> dict:
    data = hass.data.get(DOMAIN, {}) if hass is not None else {}
    hinweise = data.get("hinweise")
    saison = data.get("saison")
    return {
        "daten": backend.snapshot(),
        "gruppen": list(PFLANZENGRUPPEN),
        "automatik": hinweise.einstellungen() if hinweise is not None else None,
        "saison": saison.stand() if saison is not None else None,
        "version": 1,
    }


async def _aendern(hass, connection, msg, methode, parameter):
    backend = _backend(hass)
    if backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    try:
        objekt = await backend.async_aendern(methode, **parameter)
    except (DatensatzFehler, ValueError, TypeError) as exc:
        connection.send_error(msg["id"], "ungueltige_eingabe", str(exc))
        return
    except Exception:
        _LOGGER.exception("Mein Garten: Speichern fehlgeschlagen")
        connection.send_error(msg["id"], "speicherfehler", "Gartendaten konnten nicht gespeichert werden")
        return
    connection.send_result(msg["id"], {"objekt": objekt, **_snapshot(backend, hass)})


@websocket_api.websocket_command({probatio.Required("type"): "mein_garten/get"})
@callback
def ws_get(hass, connection, msg):
    backend = _backend(hass)
    if backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    connection.send_result(msg["id"], _snapshot(backend, hass))


@websocket_api.websocket_command({probatio.Required("type"): "mein_garten/subscribe"})
@callback
def ws_subscribe(hass, connection, msg):
    """Live-Aktualisierung für mehrere Geräte, ohne Polling."""
    backend = _backend(hass)
    if backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return

    @callback
    def _updated():
        current = _backend(hass)
        if current is not None:
            connection.send_event(msg["id"], _snapshot(current, hass))

    unsubscriber = async_dispatcher_connect(hass, SIGNAL_UPDATED, _updated)
    connection.subscriptions[msg["id"]] = unsubscriber
    connection.send_result(msg["id"])
    _updated()


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/pflanzen_suchen",
    probatio.Required("suchbegriff"): str,
})
@websocket_api.async_response
async def ws_pflanzen_suchen(hass, connection, msg):
    """Suche nach deutschen und wissenschaftlichen Pflanzennamen."""
    backend = _backend(hass)
    service = hass.data.get(DOMAIN, {}).get("suche")
    if backend is None or service is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    try:
        result = await service.async_suchen(msg["suchbegriff"])
    except ValueError as exc:
        connection.send_error(msg["id"], "ungueltige_eingabe", str(exc))
        return
    except Exception:
        _LOGGER.exception("Mein Garten: externe Pflanzensuche fehlgeschlagen")
        connection.send_error(msg["id"], "suchfehler", "Pflanzensuche momentan nicht verfügbar")
        return
    connection.send_result(msg["id"], result)



@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/pflegeprofil",
    probatio.Required("pflanzen_id"): str,
})
@websocket_api.async_response
async def ws_pflegeprofil(hass, connection, msg):
    """Nur eine tatsächlich gespeicherte Pflanze abfragen."""
    backend = _backend(hass)
    pflege = hass.data.get(DOMAIN, {}).get("pflege")
    if backend is None or pflege is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    plant = next((p for p in backend.snapshot()["pflanzen"]
                  if p["id"] == msg["pflanzen_id"]), None)
    if plant is None:
        connection.send_error(msg["id"], "pflanze_nicht_gefunden", "Pflanze nicht gefunden")
        return
    try:
        result = await pflege.async_profil(plant)
    except Exception:
        _LOGGER.exception("Mein Garten: Pflegeprofil konnte nicht geladen werden")
        connection.send_error(msg["id"], "pflegefehler", "Pflegeprofil derzeit nicht verfügbar")
        return
    connection.send_result(msg["id"], result)



@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/saisonanker_speichern",
    probatio.Required("last_frost"): str,
    probatio.Required("first_frost"): str,
})
@websocket_api.async_response
async def ws_saisonanker_speichern(hass, connection, msg):
    """Frostanker sind Benutzerentscheidungen, keine US-Klimazonenübertragung."""
    service = hass.data.get(DOMAIN, {}).get("saison")
    backend = _backend(hass)
    if service is None or backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Saisonkalender nicht eingerichtet")
        return
    try:
        await service.async_anker_speichern({
            "last_frost": msg["last_frost"],
            "first_frost": msg["first_frost"],
        })
    except ValueError as exc:
        connection.send_error(msg["id"], "ungueltige_eingabe", str(exc))
        return
    except Exception:
        _LOGGER.exception("Mein Garten: Saisonanker nicht gespeichert")
        connection.send_error(msg["id"], "speicherfehler", "Saisonreferenz nicht gespeichert")
        return
    from homeassistant.helpers.dispatcher import async_dispatcher_send
    async_dispatcher_send(hass, SIGNAL_UPDATED)
    connection.send_result(msg["id"], _snapshot(backend, hass))


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/saison_vormerken",
    probatio.Required("pflanzen_id"): str,
    probatio.Required("katalog_id"): str,
    probatio.Required("datum"): str,
})
@websocket_api.async_response
async def ws_saison_vormerken(hass, connection, msg):
    """Nur Server-Katalog und bestätigtes Datum; keine freien Tätigkeitsfelder."""
    service = hass.data.get(DOMAIN, {}).get("saison")
    backend = _backend(hass)
    if service is None or backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Saisonkalender nicht eingerichtet")
        return
    try:
        task = await service.async_vormerken(
            msg["pflanzen_id"], msg["katalog_id"], msg["datum"]
        )
    except (ValueError, DatensatzFehler) as exc:
        connection.send_error(msg["id"], "ungueltige_eingabe", str(exc))
        return
    except Exception:
        _LOGGER.exception("Mein Garten: Saisonkontrolle nicht gespeichert")
        connection.send_error(msg["id"], "speicherfehler", "Saisonkontrolle nicht gespeichert")
        return
    connection.send_result(msg["id"], {"objekt": task, **_snapshot(backend, hass)})


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/automatik_speichern",
    probatio.Required("weather_entity"): str,
    probatio.Required("notify_target"): str,
    probatio.Required("freitag_aktiv"): bool,
    probatio.Required("frost_aktiv"): bool,
    probatio.Required("frost_grenze_c"): probatio.Any(int, float),
})
@websocket_api.async_response
async def ws_automatik_speichern(hass, connection, msg):
    """Nur validierte Wetter- und Pushkonfiguration ohne beliebige Actions."""
    service = hass.data.get(DOMAIN, {}).get("hinweise")
    backend = _backend(hass)
    if service is None or backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    options = {key: msg[key] for key in (
        "weather_entity", "notify_target", "freitag_aktiv",
        "frost_aktiv", "frost_grenze_c",
    )}
    try:
        await service.async_einstellungen_speichern(options)
    except ValueError as exc:
        connection.send_error(msg["id"], "ungueltige_eingabe", str(exc))
        return
    except Exception:
        _LOGGER.exception("Mein Garten: Benachrichtigungseinstellungen nicht gespeichert")
        connection.send_error(msg["id"], "speicherfehler", "Einstellungen konnten nicht gespeichert werden")
        return
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    async_dispatcher_send(hass, SIGNAL_UPDATED)
    connection.send_result(msg["id"], _snapshot(backend, hass))


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/regel_anlegen",
    probatio.Required("name"): str,
    probatio.Required("startdatum"): str,
    probatio.Required("rhythmus"): str,
    probatio.Optional("intervall_tage"): probatio.Any(None, int),
    probatio.Optional("pflanzen_id"): probatio.Any(None, str),
    probatio.Optional("bereich_id"): probatio.Any(None, str),
    probatio.Optional("pflegefeld"): probatio.Any(None, str),
    probatio.Optional("aufgabentyp"): str,
})
@websocket_api.async_response
async def ws_regel_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "regel_anlegen", {
        key: msg[key] for key in (
            "name", "startdatum", "rhythmus", "intervall_tage",
            "pflanzen_id", "bereich_id", "pflegefeld", "aufgabentyp"
        ) if key in msg
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/regel_aktiv_setzen",
    probatio.Required("regel_id"): str,
    probatio.Required("aktiv"): bool,
})
@websocket_api.async_response
async def ws_regel_aktiv_setzen(hass, connection, msg):
    await _aendern(hass, connection, msg, "regel_aktiv_setzen", {
        "regel_id": msg["regel_id"], "aktiv": msg["aktiv"]
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/regel_entfernen",
    probatio.Required("regel_id"): str,
})
@websocket_api.async_response
async def ws_regel_entfernen(hass, connection, msg):
    await _aendern(hass, connection, msg, "regel_entfernen", {
        "regel_id": msg["regel_id"]
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/pflegeplan_aktualisieren",
})
@websocket_api.async_response
async def ws_pflegeplan_aktualisieren(hass, connection, msg):
    backend = _backend(hass)
    if backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    try:
        await backend.async_pflegeplan_aktualisieren()
    except Exception:
        _LOGGER.exception("Mein Garten: Pflegeplan-Aktualisierung fehlgeschlagen")
        connection.send_error(msg["id"], "pflegeplanfehler", "Pflegeplan konnte nicht aktualisiert werden")
        return
    connection.send_result(msg["id"], _snapshot(backend, hass))


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/bereich_anlegen",
    probatio.Required("name"): str,
})
@websocket_api.async_response
async def ws_bereich_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "bereich_anlegen", {"name": msg["name"]})


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/bereich_umbenennen",
    probatio.Required("bereich_id"): str,
    probatio.Required("name"): str,
})
@websocket_api.async_response
async def ws_bereich_umbenennen(hass, connection, msg):
    await _aendern(hass, connection, msg, "bereich_umbenennen", {
        "bereich_id": msg["bereich_id"], "name": msg["name"],
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/bereich_entfernen",
    probatio.Required("bereich_id"): str,
})
@websocket_api.async_response
async def ws_bereich_entfernen(hass, connection, msg):
    await _aendern(hass, connection, msg, "bereich_entfernen", {
        "bereich_id": msg["bereich_id"],
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/pflanze_anlegen",
    probatio.Required("name"): str,
    probatio.Optional("wissenschaftlich", default=""): str,
    probatio.Optional("bereich_id"): probatio.Any(None, str),
    probatio.Optional("gruppe"): probatio.Any(None, str),
    probatio.Optional("notizen", default=""): str,
})
@websocket_api.async_response
async def ws_pflanze_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "pflanze_anlegen", {
        key: msg[key] for key in (
            "name", "wissenschaftlich", "bereich_id", "gruppe", "notizen"
        ) if key in msg
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/pflanze_bearbeiten",
    probatio.Required("pflanzen_id"): str,
    probatio.Optional("name"): str,
    probatio.Optional("wissenschaftlich"): str,
    probatio.Optional("bereich_id"): probatio.Any(None, str),
    probatio.Optional("gruppe"): probatio.Any(None, str),
    probatio.Optional("notizen"): str,
})
@websocket_api.async_response
async def ws_pflanze_bearbeiten(hass, connection, msg):
    felder = {
        key: msg[key] for key in (
            "name", "wissenschaftlich", "bereich_id", "gruppe", "notizen"
        ) if key in msg
    }
    await _aendern(hass, connection, msg, "pflanze_bearbeiten", {
        "pflanzen_id": msg["pflanzen_id"], **felder,
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/pflanze_entfernen",
    probatio.Required("pflanzen_id"): str,
})
@websocket_api.async_response
async def ws_pflanze_entfernen(hass, connection, msg):
    await _aendern(hass, connection, msg, "pflanze_entfernen", {
        "pflanzen_id": msg["pflanzen_id"],
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/beobachtung_anlegen",
    probatio.Required("pflanzen_id"): str,
    probatio.Required("phase"): str,
    probatio.Required("beobachtet_am"): str,
    probatio.Optional("notiz", default=""): str,
})
@websocket_api.async_response
async def ws_beobachtung_anlegen(hass, connection, msg):
    """Nur explizit vom HA-Nutzer erfasste Pflanzenentwicklung."""
    await _aendern(hass, connection, msg, "beobachtung_anlegen", {
        "pflanzen_id": msg["pflanzen_id"],
        "phase": msg["phase"],
        "beobachtet_am": msg["beobachtet_am"],
        "notiz": msg.get("notiz", ""),
        "person": connection.user.name or connection.user.id,
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/beobachtung_entfernen",
    probatio.Required("beobachtung_id"): str,
})
@websocket_api.async_response
async def ws_beobachtung_entfernen(hass, connection, msg):
    """Eigene Beobachtung einschließlich Aktivitätsbezug korrigierbar löschen."""
    await _aendern(hass, connection, msg, "beobachtung_entfernen", {
        "beobachtung_id": msg["beobachtung_id"],
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/aufgabe_anlegen",
    probatio.Required("name"): str,
    probatio.Optional("faellig_am"): probatio.Any(None, str),
    probatio.Optional("pflanzen_id"): probatio.Any(None, str),
    probatio.Optional("bereich_id"): probatio.Any(None, str),
    probatio.Optional("aufgabentyp"): str,
})
@websocket_api.async_response
async def ws_aufgabe_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_anlegen", {
        key: msg[key] for key in (
            "name", "faellig_am", "pflanzen_id", "bereich_id", "aufgabentyp"
        ) if key in msg
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/aufgabe_erledigen",
    probatio.Required("aufgaben_id"): str,
    probatio.Optional("ergebnis"): str,
})
@websocket_api.async_response
async def ws_aufgabe_erledigen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_erledigen", {
        "aufgaben_id": msg["aufgaben_id"],
        "person": connection.user.name or connection.user.id,
        **({"ergebnis": msg["ergebnis"]} if "ergebnis" in msg else {}),
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/aufgabe_wieder_oeffnen",
    probatio.Required("aufgaben_id"): str,
})
@websocket_api.async_response
async def ws_aufgabe_wieder_oeffnen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_wieder_oeffnen", {
        "aufgaben_id": msg["aufgaben_id"],
        "person": connection.user.name or connection.user.id,
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/aufgabe_entfernen",
    probatio.Required("aufgaben_id"): str,
})
@websocket_api.async_response
async def ws_aufgabe_entfernen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_entfernen", {
        "aufgaben_id": msg["aufgaben_id"],
    })


@callback
def registriere_ws_befehle(hass) -> None:
    """Registriert nur lokale Befehle für authentifizierte HA-Nutzer."""
    for handler in (
        ws_get, ws_subscribe, ws_pflanzen_suchen, ws_pflegeprofil,
        ws_saisonanker_speichern, ws_saison_vormerken,
        ws_automatik_speichern, ws_regel_anlegen, ws_regel_aktiv_setzen, ws_regel_entfernen,
        ws_pflegeplan_aktualisieren,
        ws_bereich_anlegen, ws_bereich_umbenennen, ws_bereich_entfernen,
        ws_pflanze_anlegen, ws_pflanze_bearbeiten, ws_pflanze_entfernen,
        ws_beobachtung_anlegen, ws_beobachtung_entfernen,
        ws_aufgabe_anlegen, ws_aufgabe_erledigen,
        ws_aufgabe_wieder_oeffnen, ws_aufgabe_entfernen,
    ):
        websocket_api.async_register_command(hass, handler)
