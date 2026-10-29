# Mein Garten 🌿

**Neuaufbau V1 für Home Assistant Green.** Derzeit werden Datenquellen und die Pflegewissen-Architektur geprüft; **noch keine installierbare Home-Assistant-Integration**.

## Projektziel

Ein eigenständiges, dunkelgrünes Gartendashboard mit den Ansichten **Start, Pflanzen, Kalender und Bereiche**. Neue Pflanzen werden per Suche hinzugefügt – ohne Programmänderung. Pflegeinformationen werden automatisch deutschsprachig aufbereitet, mit Quellenangabe und lokalem Cache, sobald die Rechte dafür geklärt sind. Gartenbereiche, Pflegehistorie, intelligente Pflegeaufgaben und Wetter-/iPhone-Hinweise sind geplant.

**Das vorhandene Dashboard „Zuhause“ bleibt unverändert.**

## Nachgewiesener Entwicklungsstand

| Prüfung | Stand |
|---|---|
| GBIF: botanische Namenssuche | **19 exakte Namen + 2 bestätigte Hybrid-Schreibweisen** von 21 Beispielarten |
| iNaturalist: botanische Namenssuche | **21 von 21** Beispielarten exakt, einschließlich Hybriden |
| Pflegewissen-Datenmodell | Quellen, Artabgleich, Rechte, Prüfstatus und Übersetzungsfelder implementiert |
| Übersetzungs-Cache | Lokal und atomar, offline getestet |
| Permapeople-Anbindung | API-Adapter vorhanden; **noch kein authentifizierter Live-Test** |
| Azure Translator | Optionaler Adapter und Zeichenbudget vorhanden; **noch kein Live-Test** |
| OpenPlantbook-Pflegeantworten | Normalisierung getestet; **noch kein GitHub-Livetest** |
| Home-Assistant-Anwendung | **Noch nicht neu implementiert** |

**40 Offline-Tests** einschließlich der Hybridprüfung wurden auf GitHub Actions erfolgreich ausgeführt. Alle Aussagen zur erfolgreichen Live-Abfrage beziehen sich ausschließlich auf die botanische Namenssuche.

## Links zum Nachvollziehen

- [Botanische Namenssuche – korrigierter Live-Test](https://github.com/p-weigner/mein-garten/actions/runs/40866511116)
- [Pflegewissen-Prototyp – erfolgreiche Offline-Tests](https://github.com/p-weigner/mein-garten/actions/runs/40865952351)
- [Phasen-Ergebnisse und offene Prüfungen](docs/ERGEBNISSE_PHASE1_UND_2.md)
- [Optionale API-Tests ohne eigenen PC](docs/API_TEST_OHNE_PC.md)

## Sicherheitsregeln

Das Repository ist öffentlich. Keine API-Schlüssel, Fotos, Adressen, privaten Pflanzendaten oder Home-Assistant-Konfigurationen veröffentlichen. Geheimnisse nur über GitHub Actions Secrets bzw. später die sichere HA-Konfiguration verwalten. **Keine laufenden Pflicht-Abos**, keine ungeprüfte automatische Freigabe kritischer Pflegehandlungen. Übersetzungen gelten nicht automatisch als fachlich geprüft.

Öffentliche Beispielarten unter `daten/testpflanzen.json` dienen allein den Tests. Sie sind **keine fest einprogrammierte Pflanzenbibliothek**.
