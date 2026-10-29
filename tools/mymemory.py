"""MyMemory-Übersetzung für den privaten Garten: kostenlos, ohne API-Schlüssel.

Nur vom Nutzer zur Übersetzung freigegebene Fachtexte übertragen.
Keinesfalls eigene private Notizen, Fotos, Adressen, Schlüssel übertragen.
API-Regeln: höchstens ein Absatz/Segment pro Request, höchstens 500 UTF-8-Byte.
Die Übersetzung ist sprachlich, NICHT fachlich validiert.
"""
from __future__ import annotations

from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

from tools.anbieter import AnbieterFehler, KontingentErschoepft
from tools.pflegewissen import LokalerUebersetzungscache

API_URL = "https://api.mymemory.translated.net/get"
MAX_REQUEST_BYTES = 500
ANON_LIMIT_PER_DAY = 5_000


def segmente(text: str) -> list[str]:
    """Zerlegt an Absatz-/Satz-/Wortgrenzen in maximal 500-Byte-Abschnitte."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Leerer Fachtext")
    if len(text) > 12_000:
        raise ValueError("Ein Pflegefeld ist zu lang")
    parts: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        # Satzende und Semikolon bevorzugen, damit der fachliche Bezug erhalten bleibt.
        sentences = re.split(r"(?<=[.!?;])\s+", " ".join(paragraph.split()))
        for sentence in sentences:
            if not sentence:
                continue
            if len(sentence.encode("utf-8")) <= MAX_REQUEST_BYTES:
                parts.append(sentence)
                continue
            current = ""
            for word in sentence.split():
                if len(word.encode("utf-8")) > MAX_REQUEST_BYTES:
                    raise ValueError("Einzelwort länger als API-Limit")
                proposal = (current + " " + word).strip()
                if len(proposal.encode("utf-8")) > MAX_REQUEST_BYTES:
                    if current:
                        parts.append(current)
                    current = word
                else:
                    current = proposal
            if current:
                parts.append(current)
    return parts


class Tagesbudget:
    """Konservatives anonymes Limit, vor dem Senden lokal reserviert.

    Das Limit des API-Anbieters kann unabhängig davon bereits erreicht sein,
    beispielsweise durch andere Nutzer derselben ausgehenden IP-Adresse.
    """

    def __init__(self, datei: str | Path, limit: int = ANON_LIMIT_PER_DAY):
        if not (1 <= limit <= ANON_LIMIT_PER_DAY):
            raise ValueError("Für anonymen Betrieb maximal 5.000 Zeichen/Tag")
        self.limit = limit
        self.cache = LokalerUebersetzungscache(datei)

    def reservieren(self, text: str) -> None:
        if not text or len(text.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise ValueError("Text über dem MyMemory-Limit")
        heute = datetime.now(timezone.utc).date().isoformat()
        previous = self.cache.daten.get("mymemory_tagesbudget", {})
        used = int(previous.get("zeichen", 0)) if previous.get("tag") == heute else 0
        if used + len(text) > self.limit:
            raise KontingentErschoepft("Lokales Tagesbudget ausgeschöpft")
        self.cache.daten["mymemory_tagesbudget"] = {
            "tag": heute,
            "zeichen": used + len(text),
        }
        self.cache._sichern()


class MyMemoryUebersetzer:
    """Anonymer öffentlicher Dienst. Kein Schlüssel, kein kostenpflichtiger Fallback.

    Achtung: Nur für selbst verfasste Beispieltexte oder zulässig abgerufene
    fachliche Quelltexte verwenden. Antworten können maschinell übersetzt sein.
    """

    def __init__(self, budget: Tagesbudget):
        self.budget = budget

    def _abschnitt(self, text: str) -> str:
        self.budget.reservieren(text)
        query = urllib.parse.urlencode({"q": text, "langpair": "en|de", "mt": "1"})
        request = urllib.request.Request(
            f"{API_URL}?{query}",
            headers={
                "User-Agent": "MeinGarten/1.0 (personal gardening; limited anonymous API test)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise AnbieterFehler("MyMemory: HTTP-Status ungleich 200")
                raw = response.read(50_001)
                if len(raw) > 50_000:
                    raise AnbieterFehler("MyMemory: Antwort zu groß")
            data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise AnbieterFehler("MyMemory HTTP " + str(exc.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise AnbieterFehler("MyMemory momentan nicht erreichbar") from None
        except (UnicodeError, ValueError):
            raise AnbieterFehler("MyMemory: Antwort ist kein gültiges JSON") from None

        if not isinstance(data, dict) or data.get("responseStatus") != 200:
            raise AnbieterFehler("MyMemory: Kontingent oder Übersetzung nicht verfügbar")
        value = data.get("responseData")
        if not isinstance(value, dict):
            raise AnbieterFehler("MyMemory: fehlende Übersetzungsdaten")
        result = value.get("translatedText")
        if not isinstance(result, str) or not result.strip():
            raise AnbieterFehler("MyMemory: leere Übersetzung")
        cleaned = html.unescape(result).strip()
        # Fehlerseiten / rohe HTML-Fragmente dürfen nicht als Pflegehinweise erscheinen.
        if re.search(r"<[/!]?[a-z][^>]*>", cleaned, re.I):
            raise AnbieterFehler("MyMemory: unerwartetes HTML")
        return cleaned

    def __call__(self, text: str) -> str:
        chunks = segmente(text)
        return " ".join(self._abschnitt(chunk) for chunk in chunks).strip()
