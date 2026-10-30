"""Dynamische Pflanzensuche für Home Assistant mit deutschen Namen.

iNaturalist validiert die botanischen Arten in der Pflanzentaxonomie.
Wikidata ergänzt deutsche Aliase. Keine private Benutzerdatenweitergabe
außer dem Suchbegriff; kein API-Schlüssel notwendig.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from time import monotonic
import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)
_INAT = "https://api.inaturalist.org/v1/taxa/autocomplete"
_WIKIDATA = "https://www.wikidata.org/w/api.php"
_GBIF = "https://api.gbif.org/v1/species/suggest"
_TTL = 900.0
_MAX_CACHE = 100
_DISK_CACHE = 300
_LOCAL_TTL_DAYS = 365
_LOCAL_STORAGE_KEY = "mein_garten_namen_v1.data"
_PLANT_TAXON = 47126
_SPECIES_RANKS = {"species", "hybrid", "subspecies", "variety", "form"}
_QID = re.compile(r"^Q[1-9][0-9]*$")
_NAME = re.compile(r"^[A-Z][a-zA-Z×-]+(?: [a-z×-]+){1,4}$")
_WS = re.compile(r"\s+")


def _norm(name: str) -> str:
    """Normalisiert Schreibvarianten, setzt aber keine Taxon-Synonyme gleich."""
    return _WS.sub(" ", name.replace("×", " x ").casefold()).strip()


def _plant_name(name: str) -> bool:
    return isinstance(name, str) and bool(_NAME.fullmatch(name.strip()))


def _dedupe(candidates: list[dict]) -> list[dict]:
    result = {}
    for candidate in candidates:
        key = _norm(candidate["wissenschaftlich"])
        if key not in result:
            result[key] = dict(candidate)
            continue
        previous = result[key]
        # Bestätigte Taxa haben Vorrang; alle Quellen bleiben nachvollziehbar.
        if candidate["bestaetigt"] and not previous["bestaetigt"]:
            replacement = dict(candidate)
            if not replacement["deutsch"]:
                replacement["deutsch"] = previous["deutsch"]
            replacement["quellen"] = sorted(set(
                previous["quellen"] + candidate["quellen"]
            ))
            result[key] = replacement
        else:
            if not previous["deutsch"] and candidate["deutsch"]:
                previous["deutsch"] = candidate["deutsch"]
            previous["quellen"] = sorted(set(
                previous["quellen"] + candidate["quellen"]
            ))
    return list(result.values())


def _inat_results(payload: Any) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Unerwartete iNaturalist-Antwort")
    result = []
    for taxon in payload["results"][:18]:
        if not isinstance(taxon, dict):
            continue
        latin = taxon.get("name")
        if not _plant_name(latin) or taxon.get("rank") not in _SPECIES_RANKS:
            continue
        common = taxon.get("preferred_common_name") or ""
        result.append({
            "wissenschaftlich": latin[:160],
            "deutsch": common[:120] if isinstance(common, str) else "",
            "bestaetigt": True,
            "quellen": ["iNaturalist"],
            "id_inaturalist": taxon.get("id"),
        })
    return result


def _wikidata_taxa(search: Any, entities: Any, query: str) -> list[dict]:
    if not isinstance(search, dict) or not isinstance(search.get("search"), list):
        raise ValueError("Unerwartete Wikidata-Suche")
    if not isinstance(entities, dict) or not isinstance(entities.get("entities"), dict):
        raise ValueError("Unerwartete Wikidata-Daten")
    candidates = []
    for hit in search["search"][:8]:
        if not isinstance(hit, dict):
            continue
        qid = hit.get("id")
        if not isinstance(qid, str) or not _QID.fullmatch(qid):
            continue
        ent = entities["entities"].get(qid, {})
        if not isinstance(ent, dict):
            continue
        taxon = None
        for claim in ent.get("claims", {}).get("P225", [])[:5]:
            if not isinstance(claim, dict):
                continue
            maybe = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if _plant_name(maybe):
                taxon = maybe
                break
        if not taxon:
            continue
        common = hit.get("label") or query
        candidates.append({
            "wissenschaftlich": taxon[:160],
            "deutsch": common[:120] if isinstance(common, str) else query,
            "bestaetigt": False,
            "quellen": ["Wikidata"],
            "wikidata_id": qid,
        })
    return candidates


def _gbif_results(payload: Any) -> list[dict]:
    """Nur echte botanische Artvorschläge, niemals beliebige GBIF-Freitexttreffer."""
    if not isinstance(payload, list):
        raise ValueError("Unerwartete GBIF-Antwort")
    plants = []
    for taxon in payload[:25]:
        if not isinstance(taxon, dict):
            continue
        rank = str(taxon.get("rank", "")).upper()
        kingdom = str(taxon.get("kingdom", "")).casefold()
        latin = taxon.get("scientificName", "")
        canonical = taxon.get("canonicalName")
        if rank not in {"SPECIES", "SUBSPECIES", "VARIETY"} or kingdom != "plantae":
            continue
        if isinstance(canonical, str) and _plant_name(canonical):
            plants.append({
                "wissenschaftlich": canonical[:160],
                "deutsch": "",
                "bestaetigt": True,
                "quellen": ["GBIF"],
                "id_gbif": taxon.get("key"),
            })
    return plants


class Pflanzensuche:
    """15-Minuten-RAM-Cache und persistente, nur positive deutsche Namenstreffer."""

    def __init__(self, hass):
        self.hass = hass
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = asyncio.Lock()
        self._store = None
        self._lokale_queries: dict[str, dict] = {}

    async def async_laden(self) -> None:
        """Positive Artentaxa sind offline verfügbar, ohne eine feste Artenliste."""
        from homeassistant.helpers.storage import Store

        store = Store(self.hass, 1, _LOCAL_STORAGE_KEY)
        saved = await store.async_load()
        if saved is not None:
            if (not isinstance(saved, dict) or saved.get("version") != 1
                    or not isinstance(saved.get("queries"), dict)):
                raise ValueError("Unbekanntes Format des Garten-Namenscaches")
            for key, record in saved["queries"].items():
                if (not isinstance(key, str) or not isinstance(record, dict)
                        or not isinstance(record.get("zeit"), str)
                        or not isinstance(record.get("pflanzen"), list)):
                    continue
                try:
                    when = datetime.fromisoformat(record["zeit"])
                except ValueError:
                    continue
                if when.tzinfo is None or datetime.now(timezone.utc) - when > timedelta(days=_LOCAL_TTL_DAYS):
                    continue
                items = [
                    deepcopy(p) for p in record["pflanzen"][:15]
                    if isinstance(p, dict)
                    and _plant_name(p.get("wissenschaftlich"))
                    and len(p["wissenschaftlich"]) <= 160
                    and isinstance(p.get("deutsch"), str)
                    and len(p["deutsch"]) <= 120
                    and isinstance(p.get("bestaetigt"), bool)
                    and isinstance(p.get("quellen"), list)
                    and len(p["quellen"]) <= 5
                    and all(isinstance(q, str) and len(q) <= 40 for q in p["quellen"])
                ]
                if items:
                    self._lokale_queries[key] = {"zeit": record["zeit"], "pflanzen": items}
                if len(self._lokale_queries) >= _DISK_CACHE:
                    break
        self._store = store

    def _lokale_treffer(self, query: str) -> list[dict]:
        """Frühere exakte Treffer und längere Namensvarianten als Fallback."""
        term = _norm(query)
        result = []
        for key, rec in self._lokale_queries.items():
            if key != term and not (len(term) >= 4 and key.startswith(term)):
                continue
            result.extend(deepcopy(rec["pflanzen"]))
            if len(result) >= 50:
                break
        return _dedupe(result)

    async def _sichere_treffer(self, key: str, candidates: list[dict]) -> None:
        if self._store is None or not candidates:
            return
        # Keine Negativantworten, privaten Notizen oder Zugangsdaten persistieren.
        items = [{
            "wissenschaftlich": p["wissenschaftlich"],
            "deutsch": p["deutsch"],
            "bestaetigt": p["bestaetigt"],
            "quellen": list(p["quellen"]),
        } for p in candidates[:15]]
        neu = deepcopy(self._lokale_queries)
        neu[key] = {
            "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pflanzen": items,
        }
        if len(neu) > _DISK_CACHE:
            oldest = min(neu, key=lambda k: neu[k]["zeit"])
            del neu[oldest]
        try:
            await self._store.async_save({"version": 1, "queries": neu})
        except Exception:
            _LOGGER.exception("Mein Garten: Namenscache konnte nicht geschrieben werden")
            return
        self._lokale_queries = neu

    async def _json(self, url: str, **params: Any) -> Any:
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(9):
            async with session.get(
                url, params=params, headers={
                    "User-Agent": "MeinGarten/1.0 (private Home Assistant integration)",
                    "Accept": "application/json",
                }
            ) as resp:
                resp.raise_for_status()
                if int(resp.headers.get("Content-Length") or 0) > 1_000_000:
                    raise ValueError("API-Antwort zu groß")
                raw = await resp.content.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ValueError("API-Antwort zu groß")
                import json
                return json.loads(raw)

    async def _i_nat(self, query: str) -> list[dict]:
        data = await self._json(
            _INAT, q=query, locale="de", per_page=18, taxon_id=_PLANT_TAXON
        )
        return _inat_results(data)

    async def _gbif(self, query: str) -> list[dict]:
        return _gbif_results(await self._json(_GBIF, q=query, limit=25))

    async def _wikidata(self, query: str) -> list[dict]:
        search = await self._json(
            _WIKIDATA, action="wbsearchentities", search=query,
            language="de", uselang="de", type="item", limit=8, format="json"
        )
        if not isinstance(search, dict) or not isinstance(search.get("search"), list):
            raise ValueError("Wikidata-Suche lieferte keine gültige Liste")
        ids = [h.get("id") for h in search["search"] if isinstance(h, dict)
               and isinstance(h.get("id"), str) and _QID.fullmatch(h["id"])]
        if not ids:
            return []
        entities = await self._json(
            _WIKIDATA, action="wbgetentities", ids="|".join(ids),
            props="claims", format="json"
        )
        return _wikidata_taxa(search, entities, query)

    async def _verify_wikidata(self, items: list[dict]) -> list[dict]:
        """Validiert höchstens sechs Wikidata-Vorschläge als Pflanzentaxa."""
        limit = asyncio.Semaphore(3)

        async def validate(item: dict):
            async with limit:
                try:
                    plants = await self._i_nat(item["wissenschaftlich"])
                except Exception:
                    # Drittanbieterfehler (auch HTTP 429/503) dürfen die gesamte
                    # Pflanzensuche nicht abbrechen. Ein Kandidat bleibt unbestätigt.
                    _LOGGER.debug("Wikidata-Taxon konnte nicht botanisch bestätigt werden")
                    return item
                if any(_norm(p["wissenschaftlich"]) ==
                       _norm(item["wissenschaftlich"]) for p in plants):
                    item["bestaetigt"] = True
                    item["quellen"].append("iNaturalist")
                return item

        return list(await asyncio.gather(*(validate(x) for x in items[:6])))

    async def async_suchen(self, query: str) -> dict:
        if not isinstance(query, str):
            raise ValueError("Bitte einen Pflanzennamen eingeben")
        query = _WS.sub(" ", query.strip())
        if not 2 <= len(query) <= 80:
            raise ValueError("Der Suchbegriff muss 2 bis 80 Zeichen enthalten")
        key = _norm(query)
        cached = self._cache.get(key)
        if cached and monotonic() - cached[0] < _TTL:
            return dict(cached[1])

        async with self._lock:
            cached = self._cache.get(key)
            if cached and monotonic() - cached[0] < _TTL:
                return dict(cached[1])

            results = await asyncio.gather(
                self._i_nat(query), self._wikidata(query), self._gbif(query),
                return_exceptions=True
            )
            notes = []
            inat, wikidata, gbif = [], [], []
            for label, data in zip(("iNaturalist", "Wikidata", "GBIF"), results):
                if isinstance(data, BaseException):
                    _LOGGER.debug("Gartenpflanzensuche: Quelle %s nicht erreichbar", label)
                    notes.append(label + " vorübergehend nicht verfügbar")
                elif label == "iNaturalist":
                    inat = data
                elif label == "Wikidata":
                    wikidata = data
                else:
                    gbif = data
            if wikidata:
                wikidata = await self._verify_wikidata(wikidata)
            netz_treffer = _dedupe(inat + wikidata + gbif)
            offline_treffer = self._lokale_treffer(query)
            all_items = _dedupe(netz_treffer + offline_treffer)
            if offline_treffer and notes:
                notes.append("Vorhandene Pflanzennamen aus lokalem Cache ergänzt")
            # Botanisch validierte Kandidaten und treffende deutsche Namen zuerst.
            all_items.sort(key=lambda x: (
                not x["bestaetigt"],
                x["deutsch"].casefold() != key,
                x["wissenschaftlich"].casefold() != key,
                x["wissenschaftlich"].casefold(),
            ))
            result = {
                "suchbegriff": query,
                "pflanzen": all_items[:15],
                "quellenstatus": notes,
                "hinweis": "Die Art vor dem Übernehmen prüfen; ähnliche Arten können andere Pflege benötigen.",
            }
            if all_items or not notes:
                self._cache[key] = (monotonic(), result)
                if len(self._cache) > _MAX_CACHE:
                    self._cache.pop(next(iter(self._cache)))
            if netz_treffer:
                await self._sichere_treffer(key, all_items)
            return dict(result)
