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

## Phase 2b: Permapeople live geprüft (AUTHENTIFIZIERT)

**Vollständiger Bericht:** [Permapeople-Livetest vom 29.10.2026](PERMAPEOPLE_LIVETEST_2026-10-29.md)  
**Vertiefter GitHub-Lauf:** https://github.com/p-weigner/mein-garten/actions/runs/40868329416

- 19 von 21 Testpflanzen mit exaktem botanischem Treffer und Grunddaten.
- Die beiden nicht exakt gefundenen Arten sind Sommerflieder und Zitrone; Synonyme wurden noch nicht getestet.
- Alle 19 haben Angaben zu Wasser, Licht, Boden und Winterhärte.
- 11 haben ein deutsches Namensfeld; 11 einen längeren Beschreibungstext.
- Nur 3 haben eine strukturierte saisonale Angabe.
- Keines der 19 Profile hat ein eigenes strukturiertes Rückschnitt- oder Düngefeld (die Texte der Beschreibungen wurden nicht fachlich geprüft).
- **46 Offline-Tests** bestanden, API-Aufrufe erfolgreich.
- Die Pflegequellen-Tests veröffentlichen keine API-Schlüssel oder vollständigen Quelltexte.

**Technisches Urteil:** Permapeople dient als **optionale Ergänzung für Pflanzensteckbriefe**. Keine ausreichende alleinige Grundlage für das gewünschte automatische Pflegewissen.

## Noch offene Prüfungen

1. **OpenPlantbook:** Echte `get`-Antworten mit `include: care` bei repräsentativen Gartenarten vergleichen (die vorhandene HA-Integration soll verwendet werden, ohne private Schlüssel nach GitHub zu übertragen).
2. **Übersetzung:** Reale Übersetzung eines zulässig genutzten kurzen Fachtexts; rechtlicher Rahmen und sicherer kostenloser Tarif.
3. **Datenqualität:** Quelltextinhalte, Fachqualität, Sortenzuordnung und Wiederverwendungsrechte.
4. **Entwicklungsfreigabe:** Danach neue Home-Assistant-Integration implementieren. Das bisherige Gartenprojekt darf vollständig ersetzt werden; das Dashboard „Zuhause“ bleibt unberührt.

Die bestehende Installation und das Dashboard „Zuhause“ werden durch keinen dieser Tests verändert.
