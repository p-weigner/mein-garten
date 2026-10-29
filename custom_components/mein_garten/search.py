"""Dynamische Pflanzensuche für Home Assistant mit deutschen Namen.

iNaturalist validiert die botanischen Arten in der Pflanzentaxonomie.
Wikidata ergänzt deutsche Aliase. Keine private Benutzerdatenweitergabe
außer dem Suchbegriff; kein API-Schlüssel notwendig.
"""
from __future__ import annotations

import asyncio
from time import monotonic
import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)
_INAT = "https://api.inaturalist.org/v1/taxa/autocomplete"
_WIKIDATA = "https://www.wikidata.org/w/api.php"
_TTL = 900.0
_MAX_CACHE = 100
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
        # Bestätigte botanische Treffer niemals durch schwächere Vorschläge ersetzen.
        if candidate["bestaetigt"] and not previous["bestaetigt"]:
            result[key] = dict(candidate)
        elif not previous["deutsch"] and candidate["deutsch"]:
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


class Pflanzensuche:
    """Kurzzeit-Cache verhindert unnötige API-Last beim Tippen."""

    def __init__(self, hass):
        self.hass = hass
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = asyncio.Lock()

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
                except (OSError, ValueError, TimeoutError, asyncio.TimeoutError):
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
        key = query.casefold()
        cached = self._cache.get(key)
        if cached and monotonic() - cached[0] < _TTL:
            return dict(cached[1])

        async with self._lock:
            cached = self._cache.get(key)
            if cached and monotonic() - cached[0] < _TTL:
                return dict(cached[1])

            results = await asyncio.gather(
                self._i_nat(query), self._wikidata(query),
                return_exceptions=True
            )
            notes = []
            inat, wikidata = [], []
            for label, data in zip(("iNaturalist", "Wikidata"), results):
                if isinstance(data, BaseException):
                    _LOGGER.debug("Gartenpflanzensuche: Quelle %s nicht erreichbar", label)
                    notes.append(label + " vorübergehend nicht verfügbar")
                elif label == "iNaturalist":
                    inat = data
                else:
                    wikidata = data
            if wikidata:
                wikidata = await self._verify_wikidata(wikidata)
            all_items = _dedupe(inat + wikidata)
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
            self._cache[key] = (monotonic(), result)
            if len(self._cache) > _MAX_CACHE:
                self._cache.pop(next(iter(self._cache)))
            return dict(result)
