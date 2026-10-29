"""Getrennte API-Adapter. Nur öffentliche Fachtexte, keine personenbezogenen Garteninformationen.

Ein API-Schlüssel gehört in Umgebungsvariablen / GitHub Secrets, nie in Quellcode.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from tools.pflegewissen import artnorm, gleiche_art, LokalerUebersetzungscache

PERMAPEOPLE_API = "https://permapeople.org/api/search"
AZURE_API = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to=de"


class AnbieterFehler(RuntimeError):
    pass


class KontingentErschoepft(RuntimeError):
    pass


def _json_request(req: urllib.request.Request, timeout: int = 16):
    # HTTP-Fehlermeldungen niemals mit Headern/Schlüsseln protokollieren.
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                raise AnbieterFehler("Anbieter antwortet nicht mit HTTP 200")
            raw = response.read(400_001)
            if len(raw) > 400_000:
                raise AnbieterFehler("Anbieterantwort zu groß")
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AnbieterFehler("HTTP " + str(exc.code)) from None
    except urllib.error.URLError:
        raise AnbieterFehler("API nicht erreichbar") from None
    except (ValueError, UnicodeError):
        raise AnbieterFehler("Ungültige JSON-Antwort") from None


def permapeople_suche(art: str, key_id: str, key_secret: str) -> list[dict]:
    """Liest nur die erste Seite, akzeptiert aber ausschließlich exakte wissenschaftliche Namen."""
    if not art.strip() or not key_id or not key_secret:
        raise ValueError("Art oder API-Zugang fehlt")
    url = PERMAPEOPLE_API + "?" + urllib.parse.urlencode({"q": art, "per_page": 50})
    req = urllib.request.Request(url, headers={
        "User-Agent": "MeinGarten-PrivateGardenTest/1.0",
        "Accept": "application/json",
        "x-permapeople-key-id": key_id,
        "x-permapeople-key-secret": key_secret,
    })
    data = _json_request(req)
    pflanzen = data.get("plants")
    if not isinstance(pflanzen, list):
        raise AnbieterFehler("Ungültige Pflanzenliste")
    return [p for p in pflanzen if isinstance(p, dict)
            and gleiche_art(art, str(p.get("scientific_name") or ""))]


class Monatsbudget:
    """Lokales, konservatives Vorab-Zeichenbudget; keine Abrechnungsgarantie für ein Azure-Konto."""
    def __init__(self, datei: str | Path, limit: int = 100_000):
        if limit <= 0 or limit > 1_000_000:
            raise ValueError("Ungültiges Sicherheitslimit")
        self.limit = limit
        self.cache = LokalerUebersetzungscache(datei)

    def reservieren(self, text: str):
        monat = datetime.now(timezone.utc).strftime("%Y-%m")
        # UTF-16 ist eine konservative Näherung des Azure-Zeichenverbrauchs.
        n = len(text.encode("utf-16-le")) // 2
        if n > 10_000:
            raise KontingentErschoepft("Einzeltext zu lang")
        aktuell = self.cache.daten.get("zeichen", {})
        bisher = int(aktuell.get("anzahl", 0)) if aktuell.get("monat") == monat else 0
        if bisher + n > self.limit:
            raise KontingentErschoepft("Eigenes Monatsbudget erschöpft")
        # Vor der Netzwerkaktion reservieren; bei Fehlern lieber zu wenig als zu viel senden.
        self.cache.daten["zeichen"] = {"monat": monat, "anzahl": bisher + n}
        self.cache._sichern()


class AzureUebersetzer:
    """Azure Translator F0, standardmäßig DEAKTIVIERT, bis ein Key eingerichtet wird."""
    def __init__(self, schluessel: str, region: str, budget: Monatsbudget):
        if not schluessel:
            raise ValueError("Azure-Zugang fehlt")
        self.schluessel = schluessel
        self.region = region.strip()
        self.budget = budget

    def __call__(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ungültiger Übersetzungstext")
        self.budget.reservieren(text)
        header = {
            "Content-Type": "application/json; charset=UTF-8",
            "Ocp-Apim-Subscription-Key": self.schluessel,
            "User-Agent": "MeinGarten-PrivateGardenTest/1.0",
        }
        if self.region:
            header["Ocp-Apim-Subscription-Region"] = self.region
        data = json.dumps([{"Text": text}], ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(AZURE_API, data=data, headers=header, method="POST")
        antwort = _json_request(req)
        try:
            value = antwort[0]["translations"][0]["text"]
            if not isinstance(value, str) or not value.strip():
                raise ValueError()
            return value
        except (TypeError, KeyError, IndexError, ValueError):
            raise AnbieterFehler("Übersetzung fehlt in der Antwort") from None
