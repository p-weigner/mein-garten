# Datenquellen-Projekt: nachprüfbarer Teststand

Datum: 29. Oktober 2026

## Phase 1: botanische Namenssuche (LIVE)

Ursprünglicher GitHub-Lauf: https://github.com/p-weigner/mein-garten/actions/runs/40864984736

**Korrigierter und erfolgreicher Lauf:** https://github.com/p-weigner/mein-garten/actions/runs/40866511116

- 21 öffentliche Beispielarten in fünf Gartenkategorien
- GBIF: **19/21** strenge exakte Namen; **2/21** mit gleichwertiger Hybrid-Schreibweise und exakt bestätigtem GBIF-Abgleich (100 % Konfidenz)
- iNaturalist: **21/21** exakt; Hybridrang wird ausdrücklich zugelassen
- Keine Verbindungsfehler.
- Gartenerdbeere (Fragaria × ananassa) und Zitrone (Citrus × limon) werden nun korrekt zugeordnet. GBIF ließ im kanonischen Namen bei beiden das Hybridzeichen weg, iNaturalist kennzeichnet sie als Hybrid.
- Zusammen **40 Offline-Tests** bestanden (einschließlich sieben zusätzlicher Tests für Hybridfälle).

Diese Stichprobe ist **kein** repräsentativer Nachweis vollständiger Gesamtartenabdeckung. Sie sagt nichts über das vorhandene Pflegewissen aus.

## Phase 2: gemeinsame Pflegedatenstruktur (SIMULIERT)

GitHub Actions: https://github.com/p-weigner/mein-garten/actions/runs/40865952351

- 33 Offline-Tests bestanden.
- Testen: falsche Arten zurückweisen, Quellen dokumentieren, Lizenzhinweise führen, kritische Aussagen nicht automatisch planen, maschinelle Übersetzungen lokal wiederverwenden, unübersetzte Texte nicht als deutsche Hinweise anzeigen.
- Der Übersetzungscache wird privat und atomar geschrieben; eine Beispielübersetzung wird **simuliert**.
- Die technischen API-Adapter wurden nur mit simulierten Antworten getestet.

### Was die Prüfung ausdrücklich NICHT bestätigt

- **Permapeople:** API-Livetest nicht durchgeführt, weil keine Zugangsdaten gesetzt sind.
- **Azure Translator:** API-Livetest nicht durchgeführt, weil kein Schlüssel eingerichtet ist. Es wurde **kein Azure-Konto** angelegt.
- **OpenPlantbook:** In GitHub kein Live-Test, da vorhandene API-Zugangsdaten nur auf Home Assistant liegen.
- **Pflegequalität und deutschsprachige Fachtexte:** Noch nicht bei einer ausreichenden Zahl echter API-Antworten geprüft.
- **Lizenzfragen:** Die dauerhafte Nutzung jedes importierten Volltextes ist noch nicht freigegeben.

Beim Pflegequellen-Workflow lautet das Ergebnis ohne Zugangsdaten ausdrücklich \`nicht_getestet\`. Ein grüner Workflow bedeutet lediglich, dass Tests und Berichtserstellung korrekt laufen.

## Nächste Freigabeschritte

1. Permapeople-API mit einem freiwillig eingerichteten privaten Testzugang an 21 Arten prüfen.
2. OpenPlantbook-Pflegeantworten über die vorhandene HA-Integration an denselben Arten vergleichen (ohne Schlüsselübertragung nach GitHub).
3. Deutsche Übersetzung über einen bewusst gewählten Dienst mit echter kurzer Testübersetzung prüfen. Kein kostenpflichtiger Tarif als Voraussetzung.
4. Nutzungsrechte für lokales Speichern + Übersetzen der Quellen klären.
5. Erst danach neue Home-Assistant-Integration und Dashboard implementieren.

Die bestehende Installation und das Dashboard „Zuhause“ werden durch keinen dieser Tests verändert.
