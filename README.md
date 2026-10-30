# 🌿 Mein Garten – Home Assistant Green

> **Entwicklungsbranch – keine Installationsfreigabe:** Die neue Version mit dynamischer deutscher Namenssuche, lokalen Pflegeprofilen, kombinierten Gießentscheidungen, jährlichen Pflegekontrollen, optionaler Frost-/Freitags-Push-Logik, **1.292 CC0-Saisonfenstern mit eigener Datumsfreigabe**, **10.642 CC0-Standort-Steckbriefen**, **10.683 europäischen EIVE-Arten mit wissenschaftlichen Standortindikatoren** und **DWD-Jahreszeitenvergleich** wird in [Draft-PR #1](https://github.com/p-weigner/mein-garten/pull/1) geprüft. [Funktionsstand, Einstellungen, Sicherheit und offene Abnahmeprüfungen](docs/ENTWICKLUNGSSTAND_2026-10-30.md). Diese Änderungen wurden **nicht auf dem Home Assistant Green installiert**. Das Dashboard „Zuhause“ bleibt unberührt.

Eigenständiges Gartendashboard für Pflanzen, Gartenbereiche, Pflegeaufgaben und später automatisch übersetzte artspezifische Pflegeinformationen.

**Status:** Die ältere Garten-Alpha wurde laut Nutzerrückmeldung auf Home Assistant Green geladen. **Die neuen Funktionen des Entwicklungsbranches wurden dort noch nicht installiert oder live abgenommen.** Fachlich geprüfte automatische Schnitt- und Düngepläne sind weiterhin nicht freigegeben.

## Zusätzliche Funktionen nur im Entwicklungsbranch

- **Gießkontrollen mit persönlichem Kontext:** Beim manuellen Anlegen einer Gießkontrolle, bei Wiederholungen und beim Abschließen zeigt die Oberfläche die letzte Kontrolle, das letzte tatsächliche Gießen und gegebenenfalls bereits offene Gießkontrollen. Über **Pflanzen → Verlauf → ＋ Gießkontrolle anlegen** öffnet sich ein vorausgefülltes, noch **nicht** gespeichertes Formular. Kein Datum oder Gießintervall wird aus dem Verlauf geschätzt. [Funktionsweise und Tests](docs/GIESSKONTROLLE_MIT_VERLAUFSKONTEXT_2026-10-30.md).
- **Pflegeverlauf je Pflanze:** Auf jeder Pflanzenkarte gibt es **„Verlauf“** mit tatsächlich dokumentierten Erledigungen, den verschiedenen Gießentscheidungen, letzter Gießkontrolle und Zeitpunkt des letzten tatsächlichen Gießens. Es werden keine Intervalle oder Pflegehinweise aus der Historie erfunden. [Bedienung, Grenzen und Tests](docs/PFLEGEVERLAUF_PRO_PFLANZE_2026-10-30.md).
- **Pflegewissen übersichtlicher und gezielt aktualisierbar:** Nur tatsächlich vorhandene deutsche Pflegehinweise erscheinen als Karten; leere Felder werden verständlich ausgewiesen. Persönliche Pflanzennotizen bleiben bei Ausfall sichtbar. Über **Pflegequelle erneut prüfen** kann man deutsche Inhalte gezielt neu laden (höchstens alle fünf Minuten); bei komplett fehlender neuer Quellenantwort bleiben letzte deutsche Hinweise erkennbar als alter Cache-Stand erhalten. Bei **teilweise fehlenden** Informationen werden einzelne ältere Felder ebenfalls behalten und mit Warnung samt ursprünglichem Abrufdatum markiert. Ältere Felder werden nicht für neue jährliche Kontrollen vorgeschlagen. [Funktionsweise, Grenzen und Testnachweis](docs/PFLEGEWISSEN_AKTUALISIERUNG_2026-10-30.md). Keine neuen automatischen Pflegeanweisungen.
- [50 deutsche Pflanzennamen erfolgreich im Live-Test gesucht](https://github.com/p-weigner/mein-garten/actions/runs/41047293989), weitere Abdeckung nicht garantiert.
- **Saisonfenster für 1.292 botanische Arten** aus zwei fest versionierten OpenPlantDB-Datensätzen (CC0); bei unserer 50-Pflanzen-Testliste sind 15 Arten vertreten. Benutzer wählen ihre Frühjahrs-/Herbstfrost-Referenzdaten selbst, bestätigen jede neue Erinnerungsaufgabe einzeln. Keine automatische Schnitt-/Düngearbeit.
- **Standort-Steckbriefe für 10.642 botanische Arten** aus einem separat versionierten, ca. 645 KB kleinen OpenPlantDB-Offline-Katalog (CC0). In der deutschen 50er-Testliste erhalten **46 Arten mindestens ein grundlegendes Merkmal**, 37 Licht und Wasser zusammen. Licht, Wasser, Frosttoleranz und Wachstumsgruppe sind **unverbindliche Quellkategorien**, keine regional geprüften Pflegeanweisungen. Sie erscheinen sofort im vorhandenen Pflegewissen-Dialog, auch bei ausgefallenem OpenPlantbook. Widersprüchliche Sortenangaben bleiben leer.
- Kombinierte Gießaufgaben mit dokumentiertem „Gegossen“ oder „Kontrolliert – kein Wasser nötig“, eigene Pflegehistorie, Benutzer-Wiederholungen und Frostprüfungen.
- **Pflanzenentwicklung selbst beobachten:** Austrieb, Knospenbildung, Blütebeginn, Fruchtansatz, Fruchtreife, Laubfärbung und Blattfall bei jeder Pflanze mit Datum und optionaler Notiz erfassen. Eigene Jahresvergleiche und ein separater Beobachtungsbereich im Kalender; optionale Freitagsübersicht enthält nur Pflanze, Phase und Datum. Keine zusätzlichen Dienste oder DWD-Abfragen.
- **DWD-Jahreszeiten im Vergleich:** Im Pflegekalender drei Phänologie-Indikatoren (Haselblüte, Forsythienblüte, Rotbuchen-Blattentfaltung) aus echten amtlichen Stationsmeldungen 2024–2026 anzeigen. Nordostdeutsches Grobgebiet und deutschlandweites Stationsnetz umschaltbar, jeweils Median, Quartilsspanne und Anzahl Stationen mit CC-BY-4.0-Quellenhinweis. **Nur Offline-Snapshot, keine Wetter- oder Pflegeprognose.**
- [CC0-Saison-Datenbasis](docs/SAISONFENSTER_CC0_2026-10-30.md), [CC0-Standort-Steckbriefe](docs/STANDORTWISSEN_CC0_2026-10-30.md), [eigene Pflanzenbeobachtungen](docs/PHAENOLOGIE_EIGENE_BEOBACHTUNGEN_2026-10-30.md) und [regionale DWD-Vergleichsdaten](docs/PHAENOLOGIE_DWD_REGIONAL_2026-10-30.md). Technische Tests werden im [Draft-Pull-Request](https://github.com/p-weigner/mein-garten/pull/1) fortlaufend geprüft.
- Die zuvor installierte Garten-Alpha ist davon zu unterscheiden. **Diese neuen Änderungen sind noch nicht auf Home Assistant Green getestet oder installiert.**

## Aktueller Funktionsumfang

- **Vier freigegebene Ansichten:** Start · Pflanzen · Kalender · Bereiche, als eigenständige dunkelgrüne Lovelace-Karte.
- **Dynamische Namenssuche:** Deutsche und wissenschaftliche Pflanzennamen über iNaturalist + Wikidata. Die Bauernhortensien-Suche wurde live mit `Hydrangea macrophylla` nachgewiesen.
- **Pflanzen:** Ohne Änderung am Quellcode hinzufügen, bearbeiten, einer Gruppe/Bereich zuordnen, Notizen erstellen und entfernen.
- **Gartenbereiche:** Frei anlegen, umbenennen und entfernen; bei Bereichslöschung bleiben Pflanzen erhalten.
- **Pflegeaufgaben:** Manuell planen, erledigen, wieder öffnen und Verlauf dokumentieren.
- **Daten:** Lokal auf Home Assistant Green (`.storage/mein_garten_v1.data`); getrennt von früheren Garten-Prototypen.
- **Gartenkarte:** Bereits im Integrationspaket enthalten, als eigene statische Ressource unter `/api/mein_garten/mein-garten-v1-card.js` und mit eigenem Karten-Typ `custom:mein-garten-v1-card`. Die bisherige Gartenkarte bleibt davon unabhängig.

**Wichtig:** Das Home-Assistant-Dashboard **„Zuhause“ bleibt vollständig unangetastet.** Der alte Garten-Prototyp kann ersetzt werden.

## Nachgewiesene Tests

| Test | Ergebnis |
|---|---|
| Botanische Artidentität GBIF/iNaturalist | 21/21 Beispielarten eindeutig zugeordnet |
| Deutsche Namenssuche | „Bauernhortensie“ über Wikidata als `Hydrangea macrophylla` bestätigt |
| Permapeople | 19/21 exakte Grunddatenprofile; kein vollständiger Schnitt-/Düngekalender |
| OpenPlantbook `include: care` | 10/13 exakte Profile mit fünf gefüllten Pflegefeldern; Inhalt nicht fachlich freigegeben |
| MyMemory-Übersetzung | 5/5 eigene Beispielsätze erfolgreich ins Deutsche übersetzt |
| Backend der ursprünglichen Alpha | 152 Python-Tests (historischer Stand vor den neuen Funktionen) |
| Frontend | 11 Node-Tests bestanden, JavaScript-Syntax geprüft |
| HA 2026.10 Probatio | WebSocket-Schemas mit echter Probatio-Version 0.13.0 geprüft |
| Entwicklungsbranch: End-to-End-Alpha-Paketprüfung | **371 Python-Tests + 78 Frontend-Tests** (Stand des erfolgreichen Builds vom 30.10.2026); echte HA-2026.10-WebSocket-Schemas geprüft. Paketdateien, Manifest, V1-Ressource, eigene YAML und Ausschluss privater Dateien werden vor dem Artifact-Upload geprüft. Der Bericht `ABNAHME.json` kennzeichnet den PR-Quellcommit separat vom GitHub-Merge-Commit. |
| Echter Home-Assistant-Green-Start | **Noch offen** |

Die Live-Tests belegen nicht die Datenbankabdeckung sämtlicher Pflanzen. Auch maschinell übersetzte Pflegehinweise dürfen ohne Fachprüfung noch keine automatischen Schnitt- und Düngearbeiten anlegen.

## Version Alpha testen

- **[Automatischer Paket-Build mit allen Tests](.github/workflows/garten-alpha-paket.yml)** – vollständiges Paket als GitHub-Actions-Artefakt.
- **[Alpha-Installationsvorbereitung](docs/ALPHA_INSTALLATION.md)** – nur das erfolgreiche Artefakt zum **exakt gleichen PR-HEAD-Commit** verwenden; HACS von `main` liefert nicht automatisch den Entwicklungsbranch. Keine aktuelle Installationsfreigabe.
- **[Home-Assistant-Green-/iPhone-Abnahmeplan](docs/HA_GREEN_ABNAHME_2026-10-30.md)** – mit konkreten Bestehen-/Abbruchkriterien, Daten- und Dashboard-Schutz.
- **[Fehlerbehebung nach JavaScript-Ressourcenwechsel](docs/KONFIGURATIONSFEHLER_LOVELACE.md)** – alte und neue Gartenkarte können parallel bestehen.
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

1. Den **vollständigen Alpha-Build für exakt den aktuellen PR-HEAD** abschließen und bei jedem neuen Commit erneut prüfen. Die Paketprüfung muss eine passende `ABNAHME.json` enthalten.
2. **Erst nach bewusster Entscheidung** des Nutzers, mit vorhandenem vollständigem Backup, den [HA-Green-/iPhone-Abnahmeplan](docs/HA_GREEN_ABNAHME_2026-10-30.md) durchführen. Vorher weder `main` mergen noch die bestehende Installation überschreiben.
3. Gießkontext, Formularbedienung, Datenpersistenz, Such- und Quellen-Ausfälle sowie die Freitags-/Frostbenachrichtigungen auf dem echten Gerät prüfen. Fehler aus realen Logs gezielt beheben.
4. Fachlich geprüfte, lizenzrechtlich zulässige **strukturierte Pflegeanweisungen für deutsche Gartenpflanzen** erschließen; ohne belastbare Art- und Klimazuordnung weiter **keine** automatischen Schnitt-/Dünge-/Pflanztermine.
5. Spätere Ergänzungen wie optionale Fotobestimmung, der visuelle Gartenplan und eigenständige HA-Kalenderentitäten erst nach stabiler Alpha-Live-Abnahme.

**Datenschutz:** Keine privaten Gartenfotos, Adressen, Notizen oder API-Schlüssel in dieses öffentliche Repository einchecken. Die Pflanzensuche sendet ausschließlich eingegebene Suchbegriffe an iNaturalist/Wikidata.
