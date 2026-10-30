"""Europäische ökologische Standortindikatoren aus einem geprüften EIVE-Offlinekatalog.

NICHT die Daten des eigenen Gartens: nur ein öffentlicher, komprimierter
CC-BY-Wissenschaftsdatensatz. Kein Live-Download, keine Interpretation zu
Gießintervallen, Dünger, Schnitt oder Frostgefahr.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
from typing import Any

DOI = "10.5281/zenodo.7534792"
SOURCE_URL = "https://zenodo.org/records/7534792"
SOURCE = "EIVE 1.0"
LICENSE = "CC BY 4.0"
SOURCE_MD5 = "0f0ce19cd2a781eeed027d8b0acadbcb"
B64_SHA256 = "a3664ea1050ef01b4fd93374e49e5205154b9965c17e9a1505b52dc2d949e240"
GZIP_SHA256 = "de23e69eb4c5853c64a14ac0a2108990cc3d09bd7960353a28eb1e7a77de9e55"
JSON_SHA256 = "8d8e4f831e5723fa2504813a9b50099b33ecf70115a5e06e3b35079d6c233ec2"
FILE = Path(__file__).parent / "data" / "eive_europa_ccby_v1.json.gz.b64"
MAX_B64_BYTES = 300_000
MAX_JSON_BYTES = 800_000
DIMENSIONS = ("M", "N", "R", "L", "T")
STATUS = "wissenschaftliche_standortindikatoren_ohne_pflegefreigabe"
BINOMIAL = re.compile(r"^[A-Z][A-Za-z-]+ [a-z-]+$")
NOTICE = (
    "Wissenschaftliche europäische Zeigerwerte von 0 bis 10, keine absoluten "
    "Messwerte für den eigenen Garten. Keine regionale Kalibrierung für "
    "Brandenburg und keine konkreten Gieß-, Dünge-, Schnitt- oder Frostregeln."
)


class EiveFehler(ValueError):
    """Die statische EIVE-Quelle ist ungültig oder unvollständig."""


def pruefe_eive_katalog(raw: Any) -> dict[str, dict[str, dict[str, float | int]]]:
    """Fail-closed bei anderen Metadaten, fehlenden Belegen oder Mehrdeutigkeit."""
    if (
        not isinstance(raw, dict)
        or set(raw) != {
            "schema", "quelle", "lizenz", "doi", "herkunft",
            "original_md5", "arten", "felder", "pruefstatus",
            "ausgeschlossene_arten_nach_taxonquelle",
        }
        or type(raw["schema"]) is not int or raw["schema"] != 1
        or raw["quelle"] != SOURCE or raw["lizenz"] != LICENSE
        or raw["doi"] != DOI or raw["herkunft"] != SOURCE_URL
        or raw["original_md5"] != SOURCE_MD5
        or raw["felder"] != list(DIMENSIONS)
        or raw["pruefstatus"] != STATUS
        or not isinstance(raw["ausgeschlossene_arten_nach_taxonquelle"], dict)
        or not isinstance(raw["arten"], list)
        or len(raw["arten"]) != 10683
    ):
        raise EiveFehler("Unbekannter oder unvollständiger EIVE-Katalog")

    indexed = {}
    for row in raw["arten"]:
        if (
            not isinstance(row, list)
            or len(row) != 1 + 2 * len(DIMENSIONS)
            or not isinstance(row[0], str)
            or not 3 <= len(row[0]) <= 160
            or not BINOMIAL.fullmatch(row[0])
        ):
            raise EiveFehler("Ungültige EIVE-Artenzuordnung")
        key = row[0].casefold()
        if key in indexed:
            raise EiveFehler("Doppelter EIVE-Artenname")
        values = {}
        for dim, v, n in zip(DIMENSIONS, row[1::2], row[2::2]):
            if v is None and n is None:
                continue
            if (
                type(v) not in (int, float) or not math.isfinite(v)
                or not 0 <= v <= 10
                or type(n) is not int or not 1 <= n <= 31
            ):
                raise EiveFehler("Ungeeigneter oder unbelegter EIVE-Indikator")
            values[dim] = {"wert": float(v), "quellsysteme": n}
        if not values:
            raise EiveFehler("EIVE-Art ohne belegten Wert")
        indexed[key] = values
    return indexed


def _lade_offline() -> dict:
    if not FILE.is_file() or not 0 < FILE.stat().st_size <= MAX_B64_BYTES:
        raise EiveFehler("EIVE-Offlinekatalog fehlt oder ist zu groß")
    b64 = FILE.read_bytes().strip()
    if hashlib.sha256(b64).hexdigest() != B64_SHA256:
        raise EiveFehler("EIVE-Katalogprüfsumme stimmt nicht")
    try:
        archive = base64.b64decode(b64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise EiveFehler("EIVE-Katalog ist nicht korrekt kodiert") from exc
    if hashlib.sha256(archive).hexdigest() != GZIP_SHA256:
        raise EiveFehler("EIVE-Archivprüfsumme stimmt nicht")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive)) as inp:
            data = inp.read(MAX_JSON_BYTES + 1)
    except OSError as exc:
        raise EiveFehler("EIVE-Archiv konnte nicht gelesen werden") from exc
    if len(data) > MAX_JSON_BYTES or hashlib.sha256(data).hexdigest() != JSON_SHA256:
        raise EiveFehler("EIVE-Kataloginhalt ist zu groß oder wurde verändert")
    return pruefe_eive_katalog(json.loads(data))


class EiveEuropaService:
    """Ökologische Daten nur für gespeicherte eigene Pflanzen an das UI geben."""

    def __init__(self, hass: Any) -> None:
        self.hass = hass
        self._profiles: dict = {}

    async def async_laden(self) -> None:
        # Schwere Dekompression nur im HA-Executor, nicht im Event-Loop.
        self._profiles = await self.hass.async_add_executor_job(_lade_offline)

    def stand_fuer(self, pflanzen: list[dict]) -> dict:
        result = {}
        for plant in pflanzen[:250]:
            if not isinstance(plant, dict) or not isinstance(plant.get("id"), str):
                continue
            scientific = plant.get("wissenschaftlich", "")
            if not isinstance(scientific, str) or not BINOMIAL.fullmatch(scientific):
                continue
            entry = self._profiles.get(scientific.casefold())
            if entry is not None:
                result[plant["id"]] = {
                    "wissenschaftlich": scientific,
                    "indikatoren": deepcopy(entry),
                }
        return {
            "profile": result,
            "abgedeckte_pflanzen": len(result),
            "katalog_arten": len(self._profiles),
            "quelle": SOURCE,
            "lizenz": LICENSE,
            "doi": DOI,
            "quell_url": SOURCE_URL,
            "hinweis": NOTICE,
            "automatische_aufgaben": False,
        }
