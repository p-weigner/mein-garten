# 🌿 Mein Garten – Home Assistant Green

Eigenständige Gartenverwaltung mit dynamischer Pflanzensuche, deutschsprachigen Pflegeinformationen, Bereichen, Aufgaben und Pflegehistorie.

**Status: Neuaufbau V1 – Forschungsphase und Backend-Vorversion. Noch kein fertiges installierbares Gartendashboard.**

## Verbindliche Ziele

Das bisherige Home-Assistant-Dashboard **„Zuhause“ wird nicht verändert**. Die Gartenoberfläche behält das bereits freigegebene dunkelgrüne Design mit den vier Seiten **Start · Pflanzen · Kalender · Bereiche**.

Pflanzen sollen ohne Programmänderungen nach deutschem oder wissenschaftlichem Namen gefunden und angelegt werden können. Englische Pflegeinformationen werden mit Quellenangabe und lokalem Cache automatisch ins Deutsche übertragen. Pflegekalender, Pflegehistorie, individuelle Gartenbereiche, Freitagnachmittags-Zusammenfassung für Angelinas iPhone und wichtige Wetter-/Frosthinweise bleiben Projektbestandteile.

**Keine monatlichen Pflicht-Abonnements und keine unkontrollierte Abrechnung.**

## Was tatsächlich geprüft ist

| Bestandteil | Nachgewiesener Stand |
|---|---|
| Botanische Namenssuche | **21/21** Testarten durch iNaturalist exakt; GBIF **19 exakt + 2 bestätigte Hybrid-Schreibweisen** |
| Deutsche Pflanzennamen | iNaturalist liefert für viele Begriffe Vorschläge; Wikidata findet **Bauernhortensie → Hydrangea macrophylla** |
| Permapeople | **19/21** exakte Arten mit strukturierten Grunddaten; keine strukturierten Schnitt-/Düngefelder in dieser Stichprobe |
| OpenPlantbook | Echter Home-Assistant-Test: **10/13** exakte Arten mit allen fünf Pflegefreitextfeldern; Qualität und Textnutzungsrechte noch offen |
| Kostenlose deutsche Übersetzung | MyMemory live geprüft: **5/5** selbst verfasste englische Garten-Sätze ins Deutsche übertragen |
| Übersetzungssicherheit | Lokales Tagesbudget (anonym höchstens 5.000 Zeichen), 500-Byte-Segmentgrenze, privater Cache und Fehlerbehandlung implementiert |
| Lokal gespeicherte Pflanzen/Bereiche/Aufgaben | Datenmodell und HA-Backend-Grundlage implementiert; noch kein echter HA-Green-Lauf |
| Backend-Tests | **124 Python-Tests** in GitHub Actions bestanden; zusätzliche 11 YAML-/Jinja-Skripttests |
| Fertige Benutzeroberfläche | Noch nicht neu umgesetzt |

Eine bestandene Prüfung bedeutet **nicht**, dass alle Arten weltweit vollständig erfasst sind, dass übersetzte Pflegetexte fachlich geprüft wären oder dass die neue Backend-Vorversion bereits produktionsreif ist.

## Projektstruktur

- `custom_components/mein_garten/` – neue, lokal speichernde Home-Assistant-Backend-Vorversion. Pflanzen, Bereiche, Aufgaben, Historie und authentifizierte WebSocket-Befehle.
- `tools/` – dynamische Arten-/Aliassuche, Datenquellen-Fusion und kostenlose Übersetzung; Forschungsadapter, noch nicht vollständig ans HA-Backend angeschlossen.
- `tests/`, `qa/` – Offline-/Sicherheitstests und einmaliges OpenPlantbook-Testskript.
- `docs/` – echte Live-Ergebnisse, Architekturentscheidungen und offene Prüfungen.
- `.github/workflows/` – automatische Tests ohne privaten PC.

## Dokumentierte Live-Tests

- [Deutsche Pflanzennamen und Garten-/Bauernhortensie](docs/DEUTSCHE_PFLANZENSUCHE_2026-10-29.md)
- [OpenPlantbook-Pflegefelder](docs/OPENPLANTBOOK_LIVETEST_2026-10-29.md)
- [Permapeople-Pflanzendaten](docs/PERMAPEOPLE_LIVETEST_2026-10-29.md)
- [Automatische deutsche Übersetzung, Kosten und Rechte](docs/UEBERSETZUNG_LIVETEST_2026-10-29.md)
- [HA-Backend-Vorversion mit Funktionsumfang und Grenzen](docs/HA_BACKEND_BETA.md)

## Nachprüfbare GitHub-Läufe

- [Botanische Artnamen](https://github.com/p-weigner/mein-garten/actions/runs/40866511116)
- [Kostenlose Übersetzung und echte deutsche Ergebnisse](https://github.com/p-weigner/mein-garten/actions/runs/40872712042)
- [Deutsche Pflanzen-Aliase über Wikidata](https://github.com/p-weigner/mein-garten/actions/runs/40874298208)
- [Backend- und Speicherverträge](https://github.com/p-weigner/mein-garten/actions/runs/40873699383)

## Noch zu entwickeln

Die aktuellen Quellenmodule werden zum Home-Assistant-Backend verbunden. Danach folgen das bereits vereinbarte dunkelgrüne Dashboard, intelligente bestätigte Pflegeaufgaben, Kalender, Wetterwarnungen und iPhone-Benachrichtigungen. Vor einer Installation müssen die tatsächliche Home-Assistant-Laufzeitkompatibilität und die Rechte an dauerhaft gespeicherten OpenPlantbook-Pflegefreitexten geklärt werden.

**Bitte noch keine Dateien aus diesem Repository nach `/config/custom_components/` kopieren.** Die neue Garteninstallation wird später als vollständiges geprüftes Paket bereitgestellt.

## Datensicherheit

Das Repository ist öffentlich: Keine privaten Fotos, Adressen, Gartenstandorte, persönlichen Nutzernotizen oder API-Schlüssel einchecken. Alle bisherigen GitHub-Livetests verwenden nur öffentliche Pflanzennamen, anonymisierte Feldzahlen oder selbst verfasste Übersetzungsbeispiele. Die Daten des bisherigen Gartendashboards und von „Zuhause“ werden nicht verändert.
