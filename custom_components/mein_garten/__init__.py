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

    async def async_pflegeplan_aktualisieren(self) -> int:
        """Transaktionales, idempotentes Erzeugen benutzerdefinierter Termine."""
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        async with self._lock:
            neu = GartenDaten(self._modell.snapshot())
            from datetime import datetime, timezone
            from .recurrence import lokaler_kalendertag

            tz = getattr(getattr(self.hass, "config", None), "time_zone", "UTC")
            heute = lokaler_kalendertag(datetime.now(timezone.utc), tz)
            anzahl = neu.pflegeplan_aktualisieren(heute)
            if anzahl:
                await self._store.async_save(neu.snapshot())
                self._modell = neu
        if anzahl:
            async_dispatcher_send(self.hass, SIGNAL_UPDATED)
        return anzahl

    async def async_frostpruefung_anlegen(
        self, datum: str, temperatur_c: float, schwelle_c: float,
    ) -> bool:
        """Wetterwarnung nur bei neuen Terminen dauerhaft registrieren."""
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        async with self._lock:
            neuer_stand = GartenDaten(self._modell.snapshot())
            aufgabe = neuer_stand.frostpruefung_anlegen(datum, temperatur_c, schwelle_c)
            if aufgabe is None:
                return False
            await self._store.async_save(neuer_stand.snapshot())
            self._modell = neuer_stand
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)
        return True

    async def async_aendern(self, methode: str, **parameter) -> dict:
        """Nur vollständig validierten Zustand schreiben, danach publizieren."""
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        erlaubte = {
            "bereich_anlegen", "bereich_umbenennen", "bereich_entfernen",
            "pflanze_anlegen", "pflanze_bearbeiten", "pflanze_entfernen",
            "aufgabe_anlegen", "aufgabe_erledigen", "aufgabe_wieder_oeffnen",
            "aufgabe_entfernen",
            "regel_anlegen", "regel_aktiv_setzen", "regel_entfernen",
            "saisonpruefung_anlegen",
            "beobachtung_anlegen", "beobachtung_entfernen",
        }
        if methode not in erlaubte:
            raise ValueError("Nicht erlaubte Datenoperation")
        if methode == "beobachtung_anlegen":
            # Benutzerbeobachtungen auf dem vom HA-Betreiber eingestellten
            # Ortsdatum validieren (UTC-Mitternacht darf keinen Fehler erzeugen).
            from datetime import datetime, timezone
            from .recurrence import lokaler_kalendertag

            tz = getattr(getattr(self.hass, "config", None), "time_zone", "UTC")
            parameter["heute"] = lokaler_kalendertag(
                datetime.now(timezone.utc), tz
            )
        async with self._lock:
            neuer_stand = GartenDaten(self._modell.snapshot())
            objekt = getattr(neuer_stand, methode)(**parameter)
            await self._store.async_save(neuer_stand.snapshot())
            self._modell = neuer_stand
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)
        if methode == "regel_anlegen" or (methode == "regel_aktiv_setzen" and parameter.get("aktiv")):
            await self.async_pflegeplan_aktualisieren()
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
    from .care import PflegeService

    suche = Pflanzensuche(hass)
    try:
        await suche.async_laden()
    except Exception as exc:
        raise ConfigEntryNotReady(
            "Mein Garten: Pflanzennamen konnten nicht sicher geladen werden"
        ) from exc

    pflege = PflegeService(hass)
    try:
        await pflege.async_laden()
    except Exception as exc:
        raise ConfigEntryNotReady("Mein Garten: Pflegecache konnte nicht sicher gelesen werden") from exc

    from .hinweise import GartenHinweise

    hinweise = GartenHinweise(hass, backend)
    try:
        await hinweise.async_laden()
    except Exception as exc:
        raise ConfigEntryNotReady(
            "Mein Garten: Benachrichtigungseinstellungen nicht sicher lesbar"
        ) from exc

    hass.data.setdefault(DOMAIN, {})["backend"] = backend
    hass.data[DOMAIN]["suche"] = suche
    hass.data[DOMAIN]["pflege"] = pflege
    from .season import SaisonService

    saison = SaisonService(hass, backend)
    try:
        await saison.async_laden()
    except Exception as exc:
        raise ConfigEntryNotReady(
            "Mein Garten: Saisonkalender konnte nicht sicher geladen werden"
        ) from exc

    hass.data[DOMAIN]["hinweise"] = hinweise
    hass.data[DOMAIN]["saison"] = saison

    from .dwd_reference import DwdPhaenologie

    # Externe Klimastationsdaten sind ein rein informativer Zusatz.
    # Ein beschädigter optionaler Snapshot darf weder die lokale
    # Gartenverwaltung noch den manuellen Pflegekalender blockieren.
    dwd = DwdPhaenologie(hass)
    try:
        await dwd.async_laden()
        hass.data[DOMAIN]["dwd_phaenologie"] = dwd
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Mein Garten: optionale DWD-Phänologiereferenz konnte nicht geladen werden"
        )
        hass.data[DOMAIN].pop("dwd_phaenologie", None)

    from homeassistant.helpers.event import async_track_time_change
    from homeassistant.core import callback

    async def _plan_pruefen():
        try:
            await backend.async_pflegeplan_aktualisieren()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Mein Garten: Pflegeplanprüfung fehlgeschlagen")

    @callback
    def _tageswechsel(_now):
        hass.async_create_task(_plan_pruefen())

    async def _freitagsbericht(jetzt):
        try:
            await hinweise.async_freitagsbericht(jetzt)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Mein Garten: Wochenbericht fehlgeschlagen")

    async def _frost_pruefen(jetzt):
        try:
            await hinweise.async_frost_pruefen(jetzt)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Mein Garten: Frostprüfung fehlgeschlagen")

    @callback
    def _wochentermin(jetzt):
        hass.async_create_task(_freitagsbericht(jetzt))

    @callback
    def _frosttermin(jetzt):
        hass.async_create_task(_frost_pruefen(jetzt))

    entry.async_on_unload(
        async_track_time_change(hass, _tageswechsel, hour=0, minute=5, second=0)
    )
    entry.async_on_unload(
        async_track_time_change(hass, _wochentermin, hour=16, minute=0, second=0)
    )
    for hour in (6, 18):
        entry.async_on_unload(
            async_track_time_change(hass, _frosttermin, hour=hour, minute=15, second=0)
        )
    hass.async_create_task(_plan_pruefen())
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Entfernt den Backend-Verweis; gespeicherte Daten bleiben erhalten."""
    hass.data.get(DOMAIN, {}).pop("backend", None)
    hass.data.get(DOMAIN, {}).pop("suche", None)
    hass.data.get(DOMAIN, {}).pop("pflege", None)
    hass.data.get(DOMAIN, {}).pop("hinweise", None)
    hass.data.get(DOMAIN, {}).pop("saison", None)
    hass.data.get(DOMAIN, {}).pop("dwd_phaenologie", None)
    return True
