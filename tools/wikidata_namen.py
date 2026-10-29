"""Freie deutsche Pflanzen-Aliassuche über Wikidata.

Wikidata liefert Taxonomie-Namenskandidaten, KEINE Pflegeanleitungen.
Es wird nur der taxonomische Name P225 als Kandidat akzeptiert.
Die Zuordnung zur konkreten Art ist weiterhin zu verifizieren.
"""
import json
import re
import urllib.parse
import urllib.request

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
_WD_ID = re.compile(r"^Q[1-9][0-9]*$")


def _get(params: dict):
    url = WIKIDATA_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "MeinGartenResearch/1.0 (github.com/p-weigner/mein-garten; noncommercial)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RuntimeError("Wikidata-Antwort zu groß")
    return json.loads(raw)


def _taxon_name(entity: dict) -> str | None:
    """Extrahiert nur botanische Taxonbezeichnung – keine unbelegten Synonyme."""
    claims = entity.get("claims", {})
    for statement in claims.get("P225", [])[:6]:
        value = (
            statement.get("mainsnak", {})
            .get("datavalue", {})
            .get("value")
        )
        if isinstance(value, str) and 2 < len(value) <= 160:
            return value
    return None


def suchname_de(query: str, max_results: int = 8) -> list[dict]:
    """Fragt Wikidata nach deutschen Namen/Aliasen und P225 ab."""
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 120:
        raise ValueError("Ungültiger deutscher Suchbegriff")
    if not 1 <= max_results <= 15:
        raise ValueError("Ungültiges Abfragelimit")
    result = _get({
        "action": "wbsearchentities",
        "search": query.strip(),
        "language": "de",
        "uselang": "de",
        "type": "item",
        "limit": max_results,
        "format": "json",
    })
    hits = result.get("search", [])
    if not isinstance(hits, list):
        raise ValueError("Ungültige Wikidata-Suchliste")
    ids = [p.get("id") for p in hits if isinstance(p, dict)
           and isinstance(p.get("id"), str) and _WD_ID.fullmatch(p["id"])]
    if not ids:
        return []
    details = _get({
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "claims",
        "format": "json",
    })
    ents = details.get("entities", {})
    if not isinstance(ents, dict):
        raise ValueError("Ungültige Wikidata-Entitäten")
    plants = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        qid = hit.get("id")
        entity = ents.get(qid, {})
        if not isinstance(entity, dict):
            continue
        name = _taxon_name(entity)
        if not name:
            # Freitext/Ortsname ohne taxonomischen Namen ist keine Pflanzenart.
            continue
        plants.append({
            "wissenschaftlich": name,
            "deutscher_treffer": str(hit.get("label") or "")[:150],
            "alias": str((hit.get("match") or {}).get("text") or "")[:150],
            "wikidata_id": qid,
            "quelle": f"https://www.wikidata.org/wiki/{qid}",
            "status": "taxonomischer_vorschlag_nicht_verifiziert",
        })
    return plants
