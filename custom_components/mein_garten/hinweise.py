"""Optionale Wetterhinweise und Wochenübersicht für Mein Garten.

Verwendet ausschließlich Home-Assistant-Wetterentitäten sowie bereits vorhandene
Notify-Dienste oder Notify-Entitäten. Kein zusätzlicher API-Schlüssel und kein
unaufgefordertes Senden: Beide Funktionen sind standardmäßig ausgeschaltet.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
import math
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)

_STORAGE_KEY = "mein_garten_hinweise_v1.data"
_TARGET = re.compile(r"^notify\.[a-z0-9_]{1,90}$")
_WEATHER = re.compile(r"^weather\.[a-z0-9_]{1,90}$")
_DEFAULT = {
    "weather_entity": "",
    "notify_target": "",
    "freitag_aktiv": False,
    "frost_aktiv": False,
    "frost_grenze_c": 2.0,
}
_FROST_HOURS = 48


def pruefe_einstellungen(raw: Any) -> dict:
    """Auf wenige und vollständig validierte, lokal speicherbare Werte begrenzen."""
    if not isinstance(raw, dict) or set(raw) != set(_DEFAULT):
        raise ValueError("Ungültige Benachrichtigungseinstellungen")
    weather = raw["weather_entity"]
    notify = raw["notify_target"]
    if not isinstance(weather, str) or (weather and not _WEATHER.fullmatch(weather)):
        raise ValueError("Ungültige Wetterentität")
    if (not isinstance(notify, str)
            or (notify and not _TARGET.fullmatch(notify))
            or notify in {"notify.notify", "notify.send_message"}):
        raise ValueError("Bitte einen konkreten iPhone-Benachrichtigungsempfänger wählen")
    if type(raw["freitag_aktiv"]) is not bool or type(raw["frost_aktiv"]) is not bool:
        raise ValueError("Ungültiger Benachrichtigungsstatus")
    limit = raw["frost_grenze_c"]
    if type(limit) not in (float, int) or not math.isfinite(limit) or not -5 <= limit <= 8:
        raise ValueError("Die Frostgrenze muss zwischen -5 und +8 °C liegen")
    if (raw["freitag_aktiv"] or raw["frost_aktiv"]) and not notify:
        raise ValueError("Für Benachrichtigungen muss ein iPhone-Empfänger ausgewählt sein")
    if raw["frost_aktiv"] and not weather:
        raise ValueError("Für Frostwarnungen muss eine Wetterentität ausgewählt sein")
    return {**raw, "frost_grenze_c": float(limit)}


def prognose_minimum(
    daten: Any, wetter_id: str, jetzt: datetime, einheit: str = "°C",
    typ: str = "hourly",
) -> tuple[datetime, float] | None:
    """Minimale vorhergesagte Temperatur innerhalb der nächsten 48 Stunden.

    Veraltete, zeitlich fehlerhafte oder unplausible Einträge werden verworfen.
    Beim Tagesforecast verwenden wir ausschließlich die Tiefsttemperatur,
    nie die Tageshöchsttemperatur als Frostindikator.
    """
    if not isinstance(daten, dict) or not isinstance(daten.get(wetter_id), dict):
        return None
    eintraege = daten[wetter_id].get("forecast")
    if not isinstance(eintraege, list) or jetzt.tzinfo is None:
        return None
    gefundene = []
    utc_jetzt = jetzt.astimezone(timezone.utc)
    ende = utc_jetzt + timedelta(hours=_FROST_HOURS)
    for eintrag in eintraege[:100]:
        if not isinstance(eintrag, dict):
            continue
        stamp = eintrag.get("datetime")
        if not isinstance(stamp, str):
            continue
        try:
            zeit = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if zeit.tzinfo is None:
            continue
        zeit_utc = zeit.astimezone(timezone.utc)
        if not utc_jetzt <= zeit_utc <= ende:
            continue
        wert = eintrag.get("templow" if typ == "daily" else "temperature")
        if type(wert) not in (int, float) or not math.isfinite(wert):
            continue
        wert = float(wert)
        if einheit in ("°F", "F", "fahrenheit"):
            wert = (wert - 32.0) * (5.0 / 9.0)
        elif einheit not in ("°C", "C", "celsius"):
            continue
        if -60 <= wert <= 60:
            gefundene.append((zeit_utc, wert))
    return min(gefundene, key=lambda x: (x[1], x[0])) if gefundene else None


_BEOBACHTUNGSTEXTE = {
    "austrieb": "Austrieb",
    "knospenbildung": "Knospenbildung",
    "bluete_beginn": "Blütebeginn",
    "fruchtansatz": "Fruchtansatz",
    "fruchtreife": "Fruchtreife",
    "laubfaerbung": "Laubfärbung",
    "blattfall": "Blattfall",
}


def wochen_text(daten: dict, heute) -> str:
    """Kompakter Bericht ohne private Standortdaten, Notizen oder Quellfreitexte."""
    aufgaben = daten.get("aufgaben", [])
    pflanzen = {p["id"]: p["name"] for p in daten.get("pflanzen", [])}
    ende = (heute + timedelta(days=7)).isoformat()
    offen = sorted(
        (t for t in aufgaben
         if t.get("status") != "erledigt"
         and (not t.get("faellig_am") or t["faellig_am"] <= ende)),
        key=lambda t: t.get("faellig_am") or "9999-99-99",
    )
    aktuell = [t for t in offen if t.get("faellig_am") and t["faellig_am"] <= heute.isoformat()]
    meldung = [
        "Dein Garten: Wochenübersicht",
        f"{len(offen)} offene Aufgaben bis einschließlich {ende} oder ohne Termin,"
        f" davon {len(aktuell)} bereits fällig.",
    ]
    for aufgabe in offen[:6]:
        pflanzenname = pflanzen.get(aufgabe.get("pflanzen_id"))
        titel = aufgabe.get("name", "Aufgabe")[:100]
        zeile = f"• {titel}"
        if pflanzenname:
            zeile += f" – {pflanzenname[:65]}"
        if aufgabe.get("faellig_am"):
            zeile += f" ({aufgabe['faellig_am']})"
        meldung.append(zeile)
    if len(offen) > 6:
        meldung.append(f"… und {len(offen) - 6} weitere Aufgaben.")
    if not offen:
        meldung.append("Für die nächsten sieben Tage ist nichts eingetragen.")
    # Nur wenn die Nutzerin von sich aus Entwicklungsphasen erfasst hat.
    # Es werden keine externen DWD-Phänodaten und keine privaten Freitextnotizen
    # an den iPhone-Empfänger verschickt.
    beginn = (heute - timedelta(days=6)).isoformat()
    beobachtet = sorted(
        (o for o in daten.get("beobachtungen", [])
         if isinstance(o, dict)
         and o.get("quelle") == "eigene_beobachtung"
         and o.get("phase") in _BEOBACHTUNGSTEXTE
         and isinstance(o.get("beobachtet_am"), str)
         and beginn <= o["beobachtet_am"] <= heute.isoformat()
         and o.get("pflanzen_id") in pflanzen),
        key=lambda o: o["beobachtet_am"], reverse=True,
    )
    if beobachtet:
        meldung.append(
            f"{len(beobachtet)} eigene Pflanzenbeobachtungen der letzten sieben Tage:"
        )
        for o in beobachtet[:3]:
            name = pflanzen[o["pflanzen_id"]][:65]
            phase = _BEOBACHTUNGSTEXTE[o["phase"]]
            meldung.append(f"• {name}: {phase} ({o['beobachtet_am']})")
        if len(beobachtet) > 3:
            meldung.append(f"… und {len(beobachtet) - 3} weitere Beobachtungen.")
    meldung.append("Weitere Informationen im Dashboard „Mein Garten“.")
    return "\n".join(meldung)


class GartenHinweise:
    """Eigenständiger Store; Gartenpflanzen und Benutzerregeln bleiben unabhängig."""

    def __init__(self, hass: Any, backend: Any):
        from homeassistant.helpers.storage import Store

        self.hass = hass
        self.backend = backend
        self._store = Store(hass, 1, _STORAGE_KEY)
        self._daten = {
            "version": 1,
            "einstellungen": deepcopy(_DEFAULT),
            "letzte_woche": "",
            "letzter_frost_tag": "",
        }
        self._lock = asyncio.Lock()

    async def async_laden(self) -> None:
        saved = await self._store.async_load()
        if saved is None:
            return
        if not isinstance(saved, dict) or saved.get("version") != 1:
            raise ValueError("Unbekanntes Garten-Benachrichtigungsformat")
        validated = pruefe_einstellungen(saved.get("einstellungen"))
        if not all(isinstance(saved.get(k), str)
                   for k in ("letzte_woche", "letzter_frost_tag")):
            raise ValueError("Ungültiger Benachrichtigungsstatus im Speicher")
        self._daten = {**saved, "einstellungen": validated}

    def einstellungen(self) -> dict:
        return deepcopy(self._daten["einstellungen"])

    async def async_einstellungen_speichern(self, raw: dict) -> dict:
        neue = pruefe_einstellungen(raw)
        async with self._lock:
            kandidaten = deepcopy(self._daten)
            kandidaten["einstellungen"] = neue
            await self._store.async_save(kandidaten)
            self._daten = kandidaten
        return deepcopy(neue)

    async def _senden(self, titel: str, nachricht: str, empfaenger: str) -> bool:
        """Nur explizit freigegebene Notify-Ziele, kein generischer Action-Runner."""
        if not _TARGET.fullmatch(empfaenger):
            return False
        _, service = empfaenger.split(".", 1)
        try:
            if self.hass.states.get(empfaenger) is not None:
                if not self.hass.services.has_service("notify", "send_message"):
                    return False
                await self.hass.services.async_call(
                    "notify", "send_message",
                    {"title": titel, "message": nachricht},
                    target={"entity_id": empfaenger}, blocking=True,
                )
            else:
                if not self.hass.services.has_service("notify", service):
                    return False
                await self.hass.services.async_call(
                    "notify", service, {"title": titel, "message": nachricht},
                    blocking=True,
                )
            return True
        except Exception:
            _LOGGER.exception("Mein Garten: Push konnte nicht versendet werden")
            return False

    async def async_freitagsbericht(self, jetzt: datetime) -> bool:
        """Maximal ein Wochenbericht je ISO-Kalenderwoche; nur freitags."""
        from homeassistant.util import dt as dt_util

        heute = dt_util.as_local(jetzt).date()
        if heute.weekday() != 4:
            return False
        jahr, woche, _ = heute.isocalendar()
        kennung = f"{jahr}-KW{woche:02}"
        async with self._lock:
            optionen = self._daten["einstellungen"]
            if not optionen["freitag_aktiv"] or self._daten["letzte_woche"] == kennung:
                return False
            nachricht = wochen_text(self.backend.snapshot(), heute)
            if not await self._senden("Mein Garten – Wochenpflege", nachricht,
                                      optionen["notify_target"]):
                return False
            neu = deepcopy(self._daten)
            neu["letzte_woche"] = kennung
            await self._store.async_save(neu)
            self._daten = neu
            return True

    async def _frostprognose(self, wetter_id: str, jetzt: datetime):
        """Stündliche Prognose bevorzugen, Tagesprognose nur als Fallback."""
        zustand = self.hass.states.get(wetter_id)
        if zustand is None or zustand.state in ("unknown", "unavailable"):
            return None
        einheit = zustand.attributes.get("temperature_unit", "°C")
        for typ in ("hourly", "daily"):
            try:
                ergebnis = await self.hass.services.async_call(
                    "weather", "get_forecasts",
                    {"type": typ}, target={"entity_id": wetter_id},
                    blocking=True, return_response=True,
                )
            except Exception:
                _LOGGER.debug("Mein Garten: Prognose %s für %s nicht verfügbar", typ, wetter_id)
                continue
            minimum = prognose_minimum(ergebnis, wetter_id, jetzt, einheit, typ)
            if minimum is not None:
                return minimum
        return None

    async def async_frost_pruefen(self, jetzt: datetime) -> bool:
        """Warnung nur für vorhergesagte Temperatur, keine Pflegeanweisung."""
        from homeassistant.util import dt as dt_util

        async with self._lock:
            optionen = self._daten["einstellungen"]
            if not optionen["frost_aktiv"]:
                return False
            minimum = await self._frostprognose(optionen["weather_entity"], jetzt)
            if minimum is None or minimum[1] > optionen["frost_grenze_c"]:
                return False
            zeit, temperatur = minimum
            tag = dt_util.as_local(zeit).date().isoformat()
            if self._daten["letzter_frost_tag"] == tag:
                return False
            # Der Wetterhinweis erscheint unabhängig vom Push-Versand im Kalender.
            # Die Modellschicht verhindert Dubletten auch über Neustarts hinweg.
            await self.backend.async_frostpruefung_anlegen(
                tag, temperatur, optionen["frost_grenze_c"]
            )
            message = (
                f"Für {tag} werden innerhalb der nächsten 48 Stunden "
                f"etwa {temperatur:.1f} °C vorhergesagt "
                f"(Warnschwelle {optionen['frost_grenze_c']:.1f} °C).\n"
                "Empfindliche Kübelpflanzen und junge Pflanzen bitte prüfen. "
                "Eine Temperaturprognose ist keine bestätigte Frostwarnung."
            )
            if not await self._senden("Mein Garten – mögliche Frostgefahr", message,
                                      optionen["notify_target"]):
                return False
            neu = deepcopy(self._daten)
            neu["letzter_frost_tag"] = tag
            await self._store.async_save(neu)
            self._daten = neu
            return True
