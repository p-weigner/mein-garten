# Mein Garten V1 – Backend-Vorversion

**Entwicklungsstand:** 29. Oktober 2026  
**Status:** Quellcode vorhanden und in GitHub getestet. **Nicht als fertiges HACS-Update installieren.**

## Ziel der neuen Integration

Das neue Garten-Backend speichert Pflanzen, Bereiche, manuelle Aufgaben und Historie direkt in Home Assistant Green. Es ist **komplett unabhängig** vom bisherigen Dashboard „Zuhause“ und verwendet den neuen Speicher `.storage/mein_garten_v1.data`.

Alte Garten-Prototypen werden **nicht migriert oder überschrieben**. Das bisherige Gartenprojekt wird später erst bei der Freigabe ersetzt.

## Implementierte Module

| Modul | Aufgabe |
|---|---|
| `custom_components/mein_garten/model.py` | Reines Python-Datenmodell für Pflanzen, Bereiche, Aufgaben und Historie |
| `custom_components/mein_garten/__init__.py` | Home-Assistant-Store: gespeicherter Zustand, atomare Änderungen, Sperre gegen parallele Schreibvorgänge |
| `custom_components/mein_garten/config_flow.py` | Einmalige lokale Einrichtung über Home Assistant |
| `custom_components/mein_garten/api.py` | Authentifizierte WebSocket-Befehle, einschließlich Live-Aktualisierung für verschiedene Endgeräte |
| `custom_components/mein_garten/const.py` | Speicher-/Domain-Konstanten |
| `custom_components/mein_garten/manifest.json` | HA-Integrationsbeschreibung |
| `custom_components/mein_garten/translations/de.json` | Deutsche Einrichtungstexte |

## Funktional im Datenmodell

- Gartenbereiche beliebig hinzufügen, umbenennen und entfernen.
- Beim Löschen eines Bereichs bleiben Pflanzen erhalten und werden **nicht zugeordnet**.
- Beliebige neue Pflanzen ohne Codeänderung hinzufügen. Deutsche und botanische Namen, Gruppe, Bereich und Notizen pflegen.
- Fünf festgelegte Nutzergruppen für die Karten, **keine fest hinterlegte Pflanzenartenliste**.
- Aufgaben manuell erstellen, mit Fälligkeitsdatum versehen, erledigen oder wieder öffnen.
- Erledigungen mit Datum und ausführender Person dokumentieren.
- Löschvorgänge entfernen referenzierte Daten und die zugehörigen Aufgabenaktivitäten.
- Eingaben validieren, Speicherung nur nach vollständiger Prüfung, parallele Schreibvorgänge serialisieren.
- Beschädigte oder unbekannte Datenformate werden **nicht stillschweigend überschrieben**.

## Vorläufige WebSocket-Befehle

`mein_garten/get`, `mein_garten/subscribe`, `mein_garten/bereich_anlegen`, `mein_garten/bereich_umbenennen`, `mein_garten/bereich_entfernen`, `mein_garten/pflanze_anlegen`, `mein_garten/pflanze_bearbeiten`, `mein_garten/pflanze_entfernen`, `mein_garten/aufgabe_anlegen`, `mein_garten/aufgabe_erledigen`, `mein_garten/aufgabe_wieder_oeffnen`, `mein_garten/aufgabe_entfernen`.

Änderungen werden nur für authentifizierte Home-Assistant-Benutzer verarbeitet.

## Prüfungen

- Reine Pflanzen-/Aufgabenmodell-Tests, Formatprüfungen, WebSocket-Vertragstests.
- Asynchrone Store-Tests mit simuliertem Home-Assistant-Storage, einschließlich Schreibausfall und Parallelität.
- Python-Syntaxprüfung.
- **Kein echter Home-Assistant-Green-Installations- oder Laufzeittest.** Die WebSocket-Antworten wurden noch nicht auf einer realen laufenden Home-Assistant-Version geprüft.

## Vor der Benutzerinstallation noch offen

1. Dynamische deutsche Pflanzensuche in die Home-Assistant-API integrieren.
2. OpenPlantbook und Permapeople mit sauberem Quellabgleich anbinden.
3. Übersetzung unter Beachtung der Nutzungsrechte und des lokalen Kontingents integrieren.
4. Das freigegebene dunkelgrüne Frontend mit den vier Tabs **Start, Pflanzen, Kalender, Bereiche** entwickeln.
5. Pflegekalender, saisonale Regeln, optionale Fotobestimmung und die iPhone-Benachrichtigungen vervollständigen.
6. In einer isolierten HA-Testumgebung testen; erst danach auf Home Assistant Green installieren.

**Bitte die aktuelle Datei-Version noch nicht nach `/config/custom_components/` kopieren.** Ein fertiges Paket mit Installationsanleitung wird nach erfolgreichem Integrationstest erstellt.
