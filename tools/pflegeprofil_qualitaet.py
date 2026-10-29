"""Metadatenprüfung der Permapeople-Pflanzendaten, ohne Quelltexte zu veröffentlichen.

Zweck: Prüfen, ob die API wirklich Schnitt-/Dünge- und saisonales
Pflegewissen anbietet, nicht nur vier von unserem Adapter verwendete Felder.
"""
from collections import Counter
import re

_SAFE_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9 /(),.+:_-]{0,63}$")
_PRUNING = re.compile(r"prun|trim|cutting back|schnitt", re.I)
_FERTILIZING = re.compile(r"fertili[sz]|düng|compost|kompost", re.I)
_SEASONAL = re.compile(r"sow|harvest|planting|season|aussaat|ernte|pflanzzeit", re.I)


def metadaten_profil(pflanze: dict) -> dict:
    """Keine Beschreibungs- und Attributwerte in öffentlichen Artefakten."""
    if not isinstance(pflanze, dict):
        raise ValueError("Ungültiges Pflanzenprofil")
    attribute = pflanze.get("data")
    if attribute is None:
        attribute = []
    if not isinstance(attribute, list):
        raise ValueError("data muss eine Liste sein")
    schluessel = []
    for item in attribute:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        value = item.get("value")
        if (isinstance(key, str) and _SAFE_KEY.fullmatch(key)
                and isinstance(value, (str, int, float, bool))
                and str(value).strip()):
            schluessel.append(key)
    beschreibung = pflanze.get("description")
    if not isinstance(beschreibung, str):
        beschreibung = ""
    unique = sorted(set(schluessel), key=str.casefold)
    return {
        "anzahl_attribute_mit_wert": len(schluessel),
        "attributnamen_ohne_werte": unique,
        "beschreibung_zeichen": len(beschreibung),
        "beschreibung_woerter": len(beschreibung.split()),
        "schnitt_als_strukturiertes_feld": any(_PRUNING.search(k) for k in unique),
        "duengung_als_strukturiertes_feld": any(_FERTILIZING.search(k) for k in unique),
        "saison_als_strukturiertes_feld": any(_SEASONAL.search(k) for k in unique),
    }


def zusammenfassen(profildaten: list[dict]) -> dict:
    # Nur die API-Profile mit tatsächlich ausgewerteter Metadatenanalyse.
    metadaten = [p["api_metadaten"] for p in profildaten if isinstance(p.get("api_metadaten"), dict)]
    keys = Counter(k for p in metadaten for k in p["attributnamen_ohne_werte"])
    return {
        "gepruefte_profile": len(metadaten),
        "api_attributnamen_haeufigkeit": dict(sorted(keys.items(), key=lambda x: (-x[1], x[0]))),
        "beschreibung_vorhanden": sum(p["beschreibung_zeichen"] > 0 for p in metadaten),
        "beschreibung_mehr_als_200_zeichen": sum(p["beschreibung_zeichen"] > 200 for p in metadaten),
        "strukturierte_schnittangaben": sum(p["schnitt_als_strukturiertes_feld"] for p in metadaten),
        "strukturierte_duengeangaben": sum(p["duengung_als_strukturiertes_feld"] for p in metadaten),
        "strukturierte_saisonangaben": sum(p["saison_als_strukturiertes_feld"] for p in metadaten),
        "einschraenkung": (
            "Erfasst ausschließlich Attributnamen und Länge des Beschreibungstexts. "
            "Volltextqualität, fachliche Richtigkeit und Pflanzensorten werden nicht bewertet."
        ),
    }
