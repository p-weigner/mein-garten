"""Deutsche Pflegeprofile für einzelne Pflanzen aus einer bestehenden OpenPlantbook-Integration.

Es werden ausschließlich bestätigte botanische Namen nachgeschlagen. Persönliche
Notizen und Gartenbereiche werden nie an externe Dienste gesendet. Originaltexte
werden nicht gespeichert; die lokal gespeicherten Übersetzungen haben einen
Quellennachweis und dürfen keine automatischen Pflegemaßnahmen auslösen.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import html
import hashlib
import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)
CARE_FIELDS = (
    ("watering", "Gießen"),
    ("sunlight", "Licht und Standort"),
    ("soil", "Boden"),
    ("pruning", "Schnitt"),
    ("fertilization", "Düngung"),
)
SOURCE_URL = "https://open.plantbook.io/"
TRANSLATE_URL = "https://api.mymemory.translated.net/get"
STORAGE_KEY = "mein_garten_pflege_v1.data"
DAILY_CHARS = 5000
SEGMENT_BYTES = 500
MAX_FIELD_CHARS = 1600
MAX_TEXT_CHARS = 12000
COMPLETE_CACHE_DAYS = 30
PARTIAL_CACHE_HOURS = 18
MANUAL_REFRESH_MINUTES = 5
TRANSIENT_SOURCE_ERRORS = {
    "quelle_nicht_erreichbar", "quelle_nicht_eingerichtet",
    "quellenantwort_ungueltig",
}
MAX_TRANSLATIONS = 1200
_NAME = re.compile(r"^[A-Z][A-Za-z-]+(?: [a-z×xA-Z.-]+){1,5}$")
_HTML_TAG = re.compile(r"<[/!]?[a-z][^>]*>", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _same_species(first: str, second: str) -> bool:
    def norm(text: str) -> str:
        return " ".join(text.replace("×", "x").split()).casefold()
    return bool(first and second) and norm(first) == norm(second)


def _valid_species(name: Any) -> bool:
    return isinstance(name, str) and 3 <= len(name) <= 160 and bool(_NAME.fullmatch(name))


def _segments(text: str) -> list[str]:
    """Satzweise, bei Bedarf wortweise; jedes Segment maximal 500 UTF-8-Bytes."""
    parts = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        for sentence in re.split(r"(?<=[.!?;])\s+", " ".join(paragraph.split())):
            current = ""
            for word in sentence.split():
                if len(word.encode("utf-8")) > SEGMENT_BYTES:
                    raise ValueError("Ein Wort überschreitet das Übersetzungslimit")
                candidate = (current + " " + word).strip()
                if len(candidate.encode("utf-8")) > SEGMENT_BYTES:
                    if current:
                        parts.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                parts.append(current)
    return parts


def _source_field(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if not text or len(text) > MAX_FIELD_CHARS or _HTML_TAG.search(text):
        return ""
    return text


class PflegeService:
    """On-demand-Abfrage mit persistentem privatem Übersetzungs- und Budgetcache."""

    def __init__(self, hass: Any) -> None:
        from homeassistant.helpers.storage import Store

        self.hass = hass
        self._store = Store(hass, 1, STORAGE_KEY)
        self._data = {"version": 1, "profile": {}, "budget": {"tag": "", "zeichen": 0}, "translations": {}}
        self._lock = asyncio.Lock()

    async def async_laden(self) -> None:
        saved = await self._store.async_load()
        if saved is None:
            return
        if (not isinstance(saved, dict) or saved.get("version") != 1
                or not isinstance(saved.get("profile"), dict)
                or not isinstance(saved.get("budget"), dict)
                or not isinstance(saved.get("translations", {}), dict)):
            raise ValueError("Unbekanntes Format des Pflegecaches; Daten nicht überschreiben")
        self._data = {**saved, "translations": saved.get("translations", {})}

    async def _json_translate(self, segment: str) -> str:
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(10):
            async with session.get(
                TRANSLATE_URL,
                params={"q": segment, "langpair": "en|de", "mt": "1"},
                headers={
                    "Accept": "application/json",
                    "User-Agent": "MeinGarten/1.0 (private plant care translation)",
                },
            ) as response:
                response.raise_for_status()
                raw = await response.content.read(25001)
        if len(raw) > 25000:
            raise ValueError("Übersetzungsantwort zu groß")
        import json
        payload = json.loads(raw)
        if not isinstance(payload, dict) or str(payload.get("responseStatus")) != "200":
            raise ValueError("Übersetzungsdienst hat keinen Text geliefert")
        value = payload.get("responseData")
        translated = value.get("translatedText") if isinstance(value, dict) else None
        if not isinstance(translated, str):
            raise ValueError("Ungültige Übersetzungsantwort")
        translated = html.unescape(translated).strip()
        if not translated or len(translated) > 5000 or _HTML_TAG.search(translated):
            raise ValueError("Ungeeignete Übersetzung")
        return translated

    async def _translate(self, text: str) -> str | None:
        try:
            pieces = _segments(text)
        except ValueError:
            return None
        result = []
        for piece in pieces:
            today = _now().date().isoformat()
            budget = self._data["budget"]
            used = budget.get("zeichen", 0) if budget.get("tag") == today else 0
            if not isinstance(used, int) or used < 0:
                raise ValueError("Ungültiger Übersetzungszähler")
            if used + len(piece) > DAILY_CHARS:
                return None
            # Vor jedem Request buchen, damit Neustarts keine Kontingente umgehen.
            self._data["budget"] = {"tag": today, "zeichen": used + len(piece)}
            await self._store.async_save(self._data)
            try:
                result.append(await self._json_translate(piece))
            except Exception as exc:
                _LOGGER.info("Mein Garten: Übersetzung fehlgeschlagen: %s", type(exc).__name__)
                return None
        return " ".join(result) if result else None

    def _translation_key(self, species: str, feld: str, original: str) -> str:
        """Nur der SHA-256-Identifikator wird zu den übersetzten Texten gespeichert."""
        value = species.casefold() + "\x00" + feld + "\x00" + original
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    async def _deutscher_text(self, species: str, feld: str, raw: str) -> str | None:
        key = self._translation_key(species, feld, raw)
        record = self._data["translations"].get(key)
        if isinstance(record, dict) and isinstance(record.get("text"), str):
            if record["text"] and len(record["text"]) <= 12000:
                return record["text"]
        translated = await self._translate(raw)
        if not translated:
            return None
        # Nur deutsche Zieltexte mit Quellenfingerabdruck, keine fremden Originaltexte.
        translations = self._data["translations"]
        translations[key] = {"text": translated, "zeit": _now().isoformat(timespec="seconds")}
        if len(translations) > MAX_TRANSLATIONS:
            oldest = min(translations, key=lambda k: translations[k].get("zeit", ""))
            del translations[oldest]
        await self._store.async_save(self._data)
        return translated

    def _result(self, species: str, status: str, fields: dict | None = None) -> dict:
        return {
            "art": species,
            "status": status,
            "felder": fields if fields is not None else {},
            "quelle": "OpenPlantbook",
            "quell_url": SOURCE_URL,
            "sprache": "de",
            "uebersetzung": "automatisch; nicht fachlich geprüft",
            "automatische_aufgaben_erlaubt": False,
            "abgerufen_utc": _now().isoformat(timespec="seconds"),
        }

    async def _fetch(self, species: str) -> dict:
        services = self.hass.services
        if not (services.has_service("openplantbook", "search")
                and services.has_service("openplantbook", "get")):
            return self._result(species, "quelle_nicht_eingerichtet")
        try:
            search = await services.async_call(
                "openplantbook", "search", {"alias": species},
                blocking=True, return_response=True,
            )
            # Die Schlüssel des Suchergebnisses sind die tatsächlichen PIDs.
            if not isinstance(search, dict):
                return self._result(species, "quellenantwort_ungueltig")
            pid = next((key for key in search
                        if isinstance(key, str) and _same_species(species, key)), None)
            if pid is None:
                return self._result(species, "art_nicht_gefunden")
            detail = await services.async_call(
                "openplantbook", "get", {"species": pid, "include": "care"},
                blocking=True, return_response=True,
            )
        except Exception as exc:
            _LOGGER.info("Mein Garten: OpenPlantbook-Abfrage fehlgeschlagen: %s",
                         type(exc).__name__)
            return self._result(species, "quelle_nicht_erreichbar")

        if (not isinstance(detail, dict)
                or not _same_species(species, str(detail.get("pid", "")))):
            return self._result(species, "art_nicht_bestaetigt")

        fields = {}
        source_fields = 0
        missing_translations = 0
        language = str(detail.get("lang") or detail.get("language") or "").casefold()
        for key, label in CARE_FIELDS:
            raw = _source_field(detail.get(key))
            if not raw:
                fields[key] = {"titel": label, "text": None,
                               "status": "keine_angabe", "quelle": "OpenPlantbook"}
                continue
            source_fields += 1
            if language == "de" or language.startswith("de-"):
                # Bereits eindeutig deutsch deklarierte Quellfelder nicht erneut
                # als englisch behandeln. Keine Spekulation per Wortheuristik.
                translated = raw
                fieldstatus = "original_deutsch"
            else:
                translated = await self._deutscher_text(species, key, raw)
                fieldstatus = "maschinenuebersetzt" if translated else "uebersetzung_ausstehend"
            if not translated:
                missing_translations += 1
            fields[key] = {
                "titel": label,
                "text": translated,
                "status": fieldstatus,
                "quelle": "OpenPlantbook",
            }
        if source_fields == 0:
            status = "kein_deutscher_text"
        elif missing_translations:
            status = "teilweise" if missing_translations < source_fields else "kein_deutscher_text"
        else:
            status = "ok"
        return self._result(species, status, fields)

    async def async_profil(self, plant: dict, *, aktualisieren: bool = False) -> dict:
        """Lädt das Pflegeprofil mit Cache und begrenzter manueller Wiederholungsprüfung.

        Eine Benutzeraktion darf einen unvollständigen 18-Stunden-Cache prüfen,
        aber keinesfalls den Übersetzungs-Tagesschutz umgehen oder die
        OpenPlantbook-Quelle durch wiederholtes Klicken überlasten.
        Vorhandene deutsche Profile bleiben bei vorübergehendem Ausfall sichtbar.
        """
        if type(aktualisieren) is not bool:
            raise ValueError("Aktualisieren muss wahr oder falsch sein")
        species = plant.get("wissenschaftlich", "")
        if not _valid_species(species):
            return self._result(str(species), "art_unbekannt")
        cache_key = species.replace("×", "x").casefold()
        async with self._lock:
            stored = self._data["profile"].get(cache_key)
            cached = (
                isinstance(stored, dict)
                and _same_species(species, stored.get("art", ""))
                and isinstance(stored.get("felder"), dict)
            )
            now = _now()
            if cached:
                try:
                    updated = datetime.fromisoformat(stored["abgerufen_utc"])
                    days = COMPLETE_CACHE_DAYS if stored["status"] == "ok" else 0
                    ttl = timedelta(days=days) if days else timedelta(hours=PARTIAL_CACHE_HOURS)
                    age = now - updated
                    # Ein vollständig übersetztes Profil ist für die
                    # normale Gültigkeitsdauer nicht erneut abzufragen.
                    if timedelta(0) <= age < ttl and not aktualisieren:
                        return deepcopy(stored)
                except (ValueError, KeyError, TypeError):
                    pass

            if aktualisieren:
                # Diese Versuche gelten nur in der laufenden HA-Instanz und
                # werden nach einem Neustart zurückgesetzt. Das tägliche
                # Übersetzungskontingent bleibt dauerhaft im Store geschützt.
                attempts = getattr(self, "_auffrischungen", None)
                if attempts is None:
                    attempts = {}
                    self._auffrischungen = attempts
                last = attempts.get(cache_key)
                if (last is not None and timedelta(0) <= now - last
                        < timedelta(minutes=MANUAL_REFRESH_MINUTES)):
                    result = deepcopy(stored) if cached else self._result(
                        species, "aktualisierung_zu_frueh"
                    )
                    result["aktualisierung"] = "wartezeit"
                    return result
                attempts[cache_key] = now
                if len(attempts) > 300:
                    del attempts[min(attempts, key=attempts.get)]

            result = await self._fetch(species)
            # Eine neue Quellantwort ohne brauchbare deutsche Hinweise darf
            # nicht die letzte tatsächlich vorhandene Übersetzung verdrängen.
            # Die Anzeige markiert in diesem Fall die alten Inhalte ausdrücklich
            # als zwischengespeichert und den letzten problematischen Abruf.
            if cached and (
                result["status"] in TRANSIENT_SOURCE_ERRORS
                or not any(
                    isinstance(field, dict) and isinstance(field.get("text"), str)
                    and field["text"].strip()
                    for field in result.get("felder", {}).values()
                )
            ):
                if any(
                    isinstance(field, dict) and isinstance(field.get("text"), str)
                    and field["text"].strip()
                    for field in stored["felder"].values()
                ):
                    previous = deepcopy(stored)
                    previous["aktualisierung"] = result["status"]
                    return previous

            if result["status"] in {
                "ok", "teilweise", "kein_deutscher_text", "art_nicht_gefunden"
            }:
                self._data["profile"][cache_key] = deepcopy(result)
                # Maximal 300 Arten im privaten Pflegecache; keine Benutzernotizen.
                if len(self._data["profile"]) > 300:
                    oldest = min(self._data["profile"],
                                 key=lambda k: self._data["profile"][k].get(
                                     "abgerufen_utc", ""))
                    del self._data["profile"][oldest]
                await self._store.async_save(self._data)
            return deepcopy(result)
