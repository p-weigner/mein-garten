# 🌿 Mein Garten – Home Assistant Green

Eigenständiges Gartendashboard für Pflanzen, Gartenbereiche, Pflegeaufgaben und später automatisch übersetzte artspezifische Pflegeinformationen.

**Status: V1 Alpha – erste zusammenhängende Oberfläche und lokales Backend entwickelt.** Die Benutzerinstallation auf einem echten Home Assistant Green ist noch nicht durchgeführt. Automatische Pflegepläne und deutsche API-Pflegeprofile sind noch nicht freigegeben.

## Aktueller Funktionsumfang

- **Vier freigegebene Ansichten:** Start · Pflanzen · Kalender · Bereiche, als eigenständige dunkelgrüne Lovelace-Karte.
- **Dynamische Namenssuche:** Deutsche und wissenschaftliche Pflanzennamen über iNaturalist + Wikidata. Die Bayern-/Bauernhortensien-Suche wurde live mit `Hydrangea macrophylla` nachgewiesen.
- **Pflanzen:** Ohne Änderung am Quellcode hinzufügen, bearbeiten, einer Gruppe/Bereich zuordnen, Notizen erstellen und entfernen.
- **Gartenbereiche:** Frei anlegen, umbenennen und entfernen; bei Bereichslöschung bleiben Pflanzen erhalten.
- **Pflegeaufgaben:** Manuell planen, erledigen, wieder öffnen und Verlauf dokumentieren.
- **Daten:** Lokal auf Home Assistant Green (`.storage/mein_garten_v1.data`); getrennt von früheren Garten-Prototypen.
- **Gartenkarte:** Bereits im Integrationspaket enthalten, als statische Ressource unter `/api/mein_garten/mein-garten-card.js`.

**Wichtig:** Das Home-Assistant-Dashboard **„Zuhause“ bleibt vollständig unangetastet.** Der alte Garten-Prototyp kann ersetzt werden.

## Nachgewiesene Tests

| Test | Ergebnis |
|---|---|
| Botanische Artidentität GBIF/iNaturalist | 21/21 Beispielarten eindeutig zugeordnet |
| Deutsche Namenssuche | „Bauernhortensie“ über Wikidata als `Hydrangea macrophylla` bestätigt |
| Permapeople | 19/21 exakte Grunddatenprofile; kein vollständiger Schnitt-/Düngekalender |
| OpenPlantbook `include: care` | 10/13 exakte Profile mit fünf gefüllten Pflegefeldern; Inhalt nicht fachlich freigegeben |
| MyMemory-Übersetzung | 5/5 eigene Beispielsätze erfolgreich ins Deutsche übersetzt |
| Backend | 152 Python-Tests bestanden; inklusive echter Datenspeicher- und WebSocket-Vertragsmock-Tests |
| Frontend | 11 Node-Tests bestanden, JavaScript-Syntax geprüft |
| HA 2026.10 Probatio | WebSocket-Schemas mit echter Probatio-Version 0.13.0 geprüft |
| Echter Home-Assistant-Green-Start | **Noch offen** |

Die Live-Tests belegen nicht die Datenbankabdeckung sämtlicher Pflanzen. Auch maschinell übersetzte Pflegehinweise dürfen ohne Fachprüfung noch keine automatischen Schnitt- und Düngearbeiten anlegen.

## Version Alpha testen

- **[Automatischer Paket-Build mit allen Tests](.github/workflows/garten-alpha-paket.yml)** – vollständiges Paket als GitHub-Actions-Artefakt.
- **[Vollständige Installationsanleitung](docs/ALPHA_INSTALLATION.md)** – inklusive HACS und eigener Lovelace-Ressource.
- **[Vollständige Dashboard-YAML](frontend/dashboard-mein-garten.yaml)** – nur für das neue eigenständige Garten-Dashboard.
- **[Vollständiger Frontend-JavaScript-Code](frontend/mein-garten-card.js)** – im HACS-Integrationsordner automatisch mitgeliefert.
- **[Backend-Vorversion und offene Funktionen](docs/HA_BACKEND_BETA.md)**.

Keine monatlichen Pflichtabonnements. Für die freie Pflanzensuche sind nur öffentliche APIs und eine Internetverbindung erforderlich.

## Technische Struktur

- `custom_components/mein_garten/` – Home-Assistant-Integration: lokaler Speicher, Konfigurationsdialog, WebSocket-API, dynamische deutsche Pflanzensuche und eingebettete JS-Karte.
- `frontend/` – vollständige Quell-JavaScript-Karte und separate Dashboard-YAML.
- `tools/` – überprüfte Forschungsadapter zu GBIF, Permapeople, Wikidata, OpenPlantbook und kostenloser Übersetzung. **Noch nicht vollständig mit dem neuen Backend verbunden.**
- `tests/` und `qa/` – Python-/Node-/Schema- und Sicherheitsprüfungen.
- `docs/` – API-Livetests, Nutzungsrechte und Entwicklungsdokumentation.

## Nächste Ausbaustufe

1. Installations- und Laufzeittest mit der Alpha-Version auf Home Assistant.
2. Die Pflegequellen ans Backend anschließen, klare botanische Identität prüfen und Rechte zur dauerhaften Nutzung der Texte berücksichtigen.
3. Echte deutsche Pflegehinweise mit Quellenangabe und privatem Übersetzungscache in der Pflanzenansicht anzeigen.
4. Fachlich geeignete saisonale Pflegeregeln, Kalenderintegration, Wetterwarnungen und die freitägliche iPhone-Zusammenfassung ergänzen.
5. Optional Fotobestimmung und weiterführende Gartenbereichsansichten.

**Datenschutz:** Keine privaten Gartenfotos, Adressen, Notizen oder API-Schlüssel in dieses öffentliche Repository einchecken. Die Pflanzensuche sendet ausschließlich eingegebene Suchbegriffe an iNaturalist/Wikidata.
