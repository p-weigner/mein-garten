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


@websocket_api.websocket_command({probatio.Required("type"): "mein_garten/get"})
@callback
def ws_get(hass, connection, msg):
    backend = _backend(hass)
    if backend is None:
        connection.send_error(msg["id"], "nicht_eingerichtet", "Mein Garten ist nicht eingerichtet")
        return
    connection.send_result(msg["id"], _snapshot(backend))


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
            connection.send_event(msg["id"], _snapshot(current))

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
    probatio.Required("type"): "mein_garten/regel_anlegen",
    probatio.Required("name"): str,
    probatio.Required("startdatum"): str,
    probatio.Required("rhythmus"): str,
    probatio.Optional("intervall_tage"): probatio.Any(None, int),
    probatio.Optional("pflanzen_id"): probatio.Any(None, str),
    probatio.Optional("bereich_id"): probatio.Any(None, str),
})
@websocket_api.async_response
async def ws_regel_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "regel_anlegen", {
        key: msg[key] for key in (
            "name", "startdatum", "rhythmus", "intervall_tage",
            "pflanzen_id", "bereich_id"
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
    connection.send_result(msg["id"], _snapshot(backend))


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
    probatio.Required("type"): "mein_garten/aufgabe_anlegen",
    probatio.Required("name"): str,
    probatio.Optional("faellig_am"): probatio.Any(None, str),
    probatio.Optional("pflanzen_id"): probatio.Any(None, str),
    probatio.Optional("bereich_id"): probatio.Any(None, str),
})
@websocket_api.async_response
async def ws_aufgabe_anlegen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_anlegen", {
        key: msg[key] for key in (
            "name", "faellig_am", "pflanzen_id", "bereich_id"
        ) if key in msg
    })


@websocket_api.websocket_command({
    probatio.Required("type"): "mein_garten/aufgabe_erledigen",
    probatio.Required("aufgaben_id"): str,
})
@websocket_api.async_response
async def ws_aufgabe_erledigen(hass, connection, msg):
    await _aendern(hass, connection, msg, "aufgabe_erledigen", {
        "aufgaben_id": msg["aufgaben_id"],
        "person": connection.user.name or connection.user.id,
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
        ws_regel_anlegen, ws_regel_aktiv_setzen, ws_regel_entfernen,
        ws_pflegeplan_aktualisieren,
        ws_bereich_anlegen, ws_bereich_umbenennen, ws_bereich_entfernen,
        ws_pflanze_anlegen, ws_pflanze_bearbeiten, ws_pflanze_entfernen,
        ws_aufgabe_anlegen, ws_aufgabe_erledigen,
        ws_aufgabe_wieder_oeffnen, ws_aufgabe_entfernen,
    ):
        websocket_api.async_register_command(hass, handler)
