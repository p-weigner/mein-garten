"""Deterministische Pflege-Terminberechnung ohne externe Fachregeln.

Eine Wiederholung ist nur aktiv, wenn sie ausdrücklich von einem
Home-Assistant-Nutzer erstellt wurde. Ungeprüfte API-Pflegetexte erzeugen
niemals Termine. Keine verlorenen Termine beim Neustart, keine Duplikate.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def lokaler_kalendertag(zeitpunkt: datetime, zeitzone: str) -> date:
    """Planungsdatum immer aus der Home-Assistant-Zeitzone ableiten.

    Dadurch bleiben Fälligkeiten auch um 00:05 MESZ/MEZ korrekt, wenn
    die Host-Umgebung intern UTC nutzt.
    """
    if not isinstance(zeitpunkt, datetime) or zeitpunkt.tzinfo is None:
        raise ValueError("Zeitpunkt muss eine Zeitzone enthalten")
    if not isinstance(zeitzone, str) or not zeitzone:
        raise ValueError("Home-Assistant-Zeitzone fehlt")
    try:
        return zeitpunkt.astimezone(ZoneInfo(zeitzone)).date()
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unbekannte Home-Assistant-Zeitzone") from exc



def termin_fuer_regel(regel: dict, heute: date) -> date | None:
    """Gibt den zuletzt fälligen oder nächstliegenden Starttermin zurück.

    Für Intervalle wird bei länger zurückliegendem Starttermin maximal
    der letzte fällige Termin aufgerufen, nicht die gesamte Vergangenheit
    in Aufgaben verwandelt.
    """
    start = date.fromisoformat(regel["startdatum"])
    if heute <= start:
        return start
    if regel["rhythmus"] == "tage":
        tage = regel["intervall_tage"]
        if not isinstance(tage, int) or not 1 <= tage <= 365:
            raise ValueError("Ungültiges Wiederholungsintervall")
        diff = (heute - start).days
        return start + timedelta(days=(diff // tage) * tage)
    if regel["rhythmus"] == "jaehrlich":
        # 29. Februar muss bei Erstellung ausgeschlossen werden, sonst
        # entstünden in Nichtschaltjahren undefinierte Termine.
        monat, tag = start.month, start.day
        if (monat, tag) == (2, 29):
            raise ValueError("Jährliche Regeln am 29. Februar sind nicht erlaubt")
        try:
            aktuelles_jahr = date(heute.year, monat, tag)
        except ValueError as exc:
            raise ValueError("Ungültiger jährlicher Termin") from exc
        return aktuelles_jahr if aktuelles_jahr >= start else start
    raise ValueError("Unbekannter Pflegerhythmus")


def naechster_termin(regel: dict, termin: date) -> date:
    """Nächster wiederkehrender Termin nach einem bereits behandelten Datum."""
    if regel["rhythmus"] == "tage":
        return termin + timedelta(days=regel["intervall_tage"])
    if regel["rhythmus"] == "jaehrlich":
        return date(termin.year + 1, termin.month, termin.day)
    raise ValueError("Unbekannter Pflegerhythmus")


def regel_faellig(regel: dict, aufgaben: list[dict], heute: date,
                 vorschau_tage: int = 31) -> date | None:
    """Findet höchstens eine neue Aufgabe pro Regel.

    Bereits offene Aufgaben blockieren neue Instanzen. Erledigte oder
    ausdrücklich übersprungene Termine bleiben dauerhaft erledigt.
    """
    if not regel.get("aktiv", True):
        return None
    if any(t.get("regel_id") == regel["id"] and t.get("status") == "offen"
           for t in aufgaben):
        return None

    kandidat = termin_fuer_regel(regel, heute)
    if kandidat is None:
        return None
    erledigt = {
        t["faellig_am"] for t in aufgaben
        if t.get("regel_id") == regel["id"] and t.get("faellig_am")
    }
    uebersprungen = set(regel.get("uebersprungen", []))
    ende = heute + timedelta(days=vorschau_tage)
    # Pro Regel höchstens 35 Prüfungen, auch für tägliche Intervalle.
    # Es werden keine endlosen Listen über verpasste Jahre erstellt.
    for _ in range(35):
        if kandidat > ende:
            return None
        if kandidat.isoformat() not in erledigt | uebersprungen:
            return kandidat
        kandidat = naechster_termin(regel, kandidat)
    return None
