"""Mein Garten: vollständig lokale Backend-Speicherung.

Vorinstallations-Prototyp: Home-Assistant-Laufzeittest und UI noch ausstehend.
Die neue Speicherung verwendet absichtlich einen anderen Schlüssel als
die früheren Garten-Prototypen. Das Dashboard "Zuhause" wird nicht berührt.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, SIGNAL_UPDATED, STORAGE_KEY, STORAGE_VERSION
from .model import GartenDaten

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class GartenBackend:
    """Einzelner HA-Store mit serialisierten, atomaren Zustandsänderungen."""

    def __init__(self, hass: Any):
        from homeassistant.helpers.storage import Store

        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._lock = asyncio.Lock()
        self._modell = GartenDaten()

    async def async_laden(self) -> None:
        """Bei beschädigtem Format niemals den bestehenden Inhalt überschreiben."""
        data = await self._store.async_load()
        if data is not None:
            self._modell = GartenDaten(data)

    def snapshot(self) -> dict:
        return self._modell.snapshot()

    async def async_aendern(self, methode: str, **parameter) -> dict:
        """Nur vollständig validierten Zustand schreiben, danach publizieren."""
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        erlaubte = {
            "bereich_anlegen", "bereich_umbenennen", "bereich_entfernen",
            "pflanze_anlegen", "pflanze_bearbeiten", "pflanze_entfernen",
            "aufgabe_anlegen", "aufgabe_erledigen", "aufgabe_wieder_oeffnen",
            "aufgabe_entfernen",
        }
        if methode not in erlaubte:
            raise ValueError("Nicht erlaubte Datenoperation")
        async with self._lock:
            neuer_stand = GartenDaten(self._modell.snapshot())
            objekt = getattr(neuer_stand, methode)(**parameter)
            await self._store.async_save(neuer_stand.snapshot())
            self._modell = neuer_stand
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)
        return objekt


async def async_setup(hass, config) -> bool:
    """Home-Assistant-WebSocket-API einmalig einrichten."""
    from .api import registriere_ws_befehle

    bucket = hass.data.setdefault(DOMAIN, {})
    if not bucket.get("_websocket_aktiv", False):
        registriere_ws_befehle(hass)
        bucket["_websocket_aktiv"] = True

    if not bucket.get("_frontend_aktiv", False):
        from homeassistant.components.http import StaticPathConfig

        frontend = Path(__file__).parent / "frontend" / "mein-garten-card.js"
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                "/api/mein_garten/mein-garten-v1-card.js",
                str(frontend),
                cache_headers=False,
            ),
        ])
        bucket["_frontend_aktiv"] = True
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Lädt persönliche Pflanzendaten nur lokal in Home Assistant."""
    from homeassistant.exceptions import ConfigEntryNotReady

    backend = GartenBackend(hass)
    try:
        await backend.async_laden()
    except Exception as exc:
        # Speicherdefekte dürfen keinesfalls durch leere Neudaten überschrieben werden.
        raise ConfigEntryNotReady(
            "Mein Garten: Daten konnten nicht sicher gelesen werden"
        ) from exc
    from .search import Pflanzensuche

    hass.data.setdefault(DOMAIN, {})["backend"] = backend
    hass.data[DOMAIN]["suche"] = Pflanzensuche(hass)
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Entfernt den Backend-Verweis; gespeicherte Daten bleiben erhalten."""
    hass.data.get(DOMAIN, {}).pop("backend", None)
    hass.data.get(DOMAIN, {}).pop("suche", None)
    return True
