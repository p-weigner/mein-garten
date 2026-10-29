"""Mein Garten – authentifizierte WebSocket-Schnittstelle für die HA-Oberfläche.

Keine externen Zugänge, keine fremden Pflegefreitexte.
Aktuell reine Stammdaten- und Pflegeaufgabenverwaltung.
"""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATED
from .model import DatensatzFehler, PFLANZENGRUPPEN

_LOGGER = logging.getLogger(__name__)


def _backend(hass):
    return hass.data.get(DOMAIN, {}).get("backend")


def _snapshot(backend) -> dict:
    return {
        "daten": backend.snapshot(),
        "gruppen": list(PFLANZENGRUPPEN),
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
    connection.send_result(msg["id"], {"objekt": objekt, **_snapshot(backend)})


@websocket_api.websocket_command({vol.Required("type"): "mein_garten/get"})
@callback
def ws_get(hass, connection, msg):
    backend = _backend(hass)
    if backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    connection.send_result(msg["id"], _snapshot(backend))


@websocket_api.websocket_command({vol.Required("type"): "mein_garten/subscribe"})
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
            connection.send_event(msg["id"], _snapshot(current))

    unsubscriber = async_dispatcher_connect(hass, SIGNAL_UPDATED, _updated)
    connection.subscriptions[msg["id"]] = unsubscriber
    connection.send_result(msg["id"])
    _updated()


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/bereich_anlegen",
    vol.Required("name"): str,
})
@websocket_api.async_response
async def ws_bereich_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "bereich_anlegen", {"name": msg["name"]})


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/bereich_umbenennen",
    vol.Required("bereich_id"): str,
    vol.Required("name"): str,
})
@websocket_api.async_response
async def ws_bereich_umbenennen(hass, connection, msg):
    await _aendern(hass, connection, msg, "bereich_umbenennen", {
        "bereich_id": msg["bereich_id"], "name": msg["name"],
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/bereich_entfernen",
    vol.Required("bereich_id"): str,
})
@websocket_api.async_response
async def ws_bereich_entfernen(hass, connection, msg):
    await _aendern(hass, connection, msg, "bereich_entfernen", {
        "bereich_id": msg["bereich_id"],
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/pflanze_anlegen",
    vol.Required("name"): str,
    vol.Optional("wissenschaftlich", default=""): str,
    vol.Optional("bereich_id"): vol.Any(None, str),
    vol.Optional("gruppe"): vol.Any(None, str),
    vol.Optional("notizen", default=""): str,
})
@websocket_api.async_response
async def ws_pflanze_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "pflanze_anlegen", {
        key: msg[key] for key in (
            "name", "wissenschaftlich", "bereich_id", "gruppe", "notizen"
        ) if key in msg
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/pflanze_bearbeiten",
    vol.Required("pflanzen_id"): str,
    vol.Optional("name"): str,
    vol.Optional("wissenschaftlich"): str,
    vol.Optional("bereich_id"): vol.Any(None, str),
    vol.Optional("gruppe"): vol.Any(None, str),
    vol.Optional("notizen"): str,
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
    vol.Required("type"): "mein_garten/pflanze_entfernen",
    vol.Required("pflanzen_id"): str,
})
@websocket_api.async_response
async def ws_pflanze_entfernen(hass, connection, msg):
    await _aendern(hass, connection, msg, "pflanze_entfernen", {
        "pflanzen_id": msg["pflanzen_id"],
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/aufgabe_anlegen",
    vol.Required("name"): str,
    vol.Optional("faellig_am"): vol.Any(None, str),
    vol.Optional("pflanzen_id"): vol.Any(None, str),
    vol.Optional("bereich_id"): vol.Any(None, str),
})
@websocket_api.async_response
async def ws_aufgabe_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_anlegen", {
        key: msg[key] for key in (
            "name", "faellig_am", "pflanzen_id", "bereich_id"
        ) if key in msg
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/aufgabe_erledigen",
    vol.Required("aufgaben_id"): str,
})
@websocket_api.async_response
async def ws_aufgabe_erledigen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_erledigen", {
        "aufgaben_id": msg["aufgaben_id"],
        "person": connection.user.name or connection.user.id,
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/aufgabe_wieder_oeffnen",
    vol.Required("aufgaben_id"): str,
})
@websocket_api.async_response
async def ws_aufgabe_wieder_oeffnen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_wieder_oeffnen", {
        "aufgaben_id": msg["aufgaben_id"],
        "person": connection.user.name or connection.user.id,
    })


@websocket_api.websocket_command({
    vol.Required("type"): "mein_garten/aufgabe_entfernen",
    vol.Required("aufgaben_id"): str,
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
        ws_get, ws_subscribe,
        ws_bereich_anlegen, ws_bereich_umbenennen, ws_bereich_entfernen,
        ws_pflanze_anlegen, ws_pflanze_bearbeiten, ws_pflanze_entfernen,
        ws_aufgabe_anlegen, ws_aufgabe_erledigen,
        ws_aufgabe_wieder_oeffnen, ws_aufgabe_entfernen,
    ):
        websocket_api.async_register_command(hass, handler)
