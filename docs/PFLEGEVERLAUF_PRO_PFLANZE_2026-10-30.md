# Mein Garten – Pflegeverlauf je Pflanze (30.10.2026)

**Status: im Entwicklungsbranch umgesetzt, isolierte Python-/Frontend-Abnahme bestanden; noch nicht auf Home Assistant Green installiert.** Kein Merge nach `main` und keine Änderung des bestehenden Dashboards „Zuhause“.

## Bedienung

Im Bereich **Pflanzen** besitzt jede Pflanzenkarte einen neuen Button **„Verlauf“**. Steht bereits eine abgeschlossene Gießkontrolle im lokalen Speicher, zeigt die Pflanzenkarte zusätzlich deren Zeitpunkt und das tatsächliche Ergebnis an. Die übrigen Buttons, Gruppierungen und die dunkelgrüne Gestaltung bleiben erhalten.

Im Dialog **„Pflegeverlauf: [Pflanze]“** werden drei Kennzahlen und die jüngsten erledigten Pflegearbeiten angezeigt:

- **Erledigt**: momentan als erledigt gespeicherte Aufgaben für genau diese Pflanze.
- **Gegossen**: Gießkontrollen, die ausdrücklich mit `gegossen` abgeschlossen wurden.
- **Kein Wasser nötig**: Gießkontrollen, bei denen ausdrücklich `kontrolliert_kein_wasser` erfasst wurde.

Die **letzte Gießkontrolle** und der Zeitpunkt, zu dem tatsächlich zuletzt Wasser gegeben wurde, werden getrennt ausgewiesen. Damit wird eine Kontrolle ohne Bewässerung nicht fälschlich als Gießvorgang gezählt.

Der Verlauf beginnt bei den **20 neuesten** Aufgaben. Mit **„Weitere 20 anzeigen“** können ältere abgeschlossene Aufgaben im selben Dialog nachgeladen werden.

Jeder Eintrag nennt den ursprünglichen Aufgabennamen, den tatsächlichen Abschlusszeitpunkt in der lokalen Browser-Zeitzone, gegebenenfalls das ursprünglich geplante Datum sowie – soweit vorhanden – die bei Erledigung über Home Assistant gespeicherte Person.

## Datenhaltung und Grenzen

- Die Darstellung liest ausschließlich die bereits lokal vorhandenen `aufgaben` und die dazugehörigen Erledigungsereignisse aus `historie` im Garten-Snapshot. Es gibt **keine Schemaänderung**, **keine Datenmigration**, **keine externe Abfrage** und **keinen zusätzlichen API-Dienst**.
- Gezählt und angezeigt werden nur **gegenwärtig als erledigt gespeicherte** Aufgaben. Wieder geöffnete, noch offene, gelöschte sowie Aufgaben anderer Pflanzen zählen nicht. Das ist ein **aktueller Pflegeverlauf**, kein unveränderliches Journal aller früheren Korrekturen und Zustandsänderungen.
- Die separate Ereignishistorie kann alte Erledigungsereignisse zu später wieder geöffneten Aufgaben enthalten. Diese werden nicht als aktuelle Erledigung in die Kennzahlen übernommen.
- Bei alten Datensätzen ohne gültigen Zeitstempel wird **„Zeitpunkt nicht gespeichert“** angezeigt, statt ein Datum zu erfinden.
- Pflanzen- und Aufgabennamen sowie die gespeicherte Personenkennung werden HTML-sicher dargestellt. Der Dialog leitet persönliche Notizen, Namen, Arbeitsergebnisse und Ortsinformationen an **keinen externen Dienst** weiter.
- Das Ergebnis einer manuellen Gießkontrolle ist kein wissenschaftlich bestätigtes Wasserbedarfsprofil. Der Verlauf **generiert keine Termine**, **empfiehlt keine Intervalle** und ändert vorhandene Wiederholungsregeln nicht.
- Wird eine Pflanze mitsamt Aufgaben gelöscht, verschwinden ihre erledigten Aufgaben auch aus diesem Verlauf. Es existiert kein zusätzlicher Schatten-Cache.

## Umsetzung und Tests

- Anzeige und Dialog: [`frontend/mein-garten-card.js`](../frontend/mein-garten-card.js)
- Identische von der Integration gelieferte Kopie: [`custom_components/mein_garten/frontend/mein-garten-card.js`](../custom_components/mein_garten/frontend/mein-garten-card.js)
- Frontend-Regressionstests: [`frontend/tests/card.test.mjs`](../frontend/tests/card.test.mjs)
- Bestehende geprüfte Daten- und Erledigungslogik: [`custom_components/mein_garten/model.py`](../custom_components/mein_garten/model.py)

**Neue Tests** prüfen echte Gieß-/Nicht-Gießentscheidungen, Sortierung, persönliche Pflanzenzuordnung, Ausschluss offener/gelöschter Aufgaben, Seitennavigation und HTML-Escaping.

**GitHub-Actions-Lauf [41092892248](https://github.com/p-weigner/mein-garten/actions/runs/41092892248): 357 von 357 Python-Tests und 69 von 69 Frontend-Tests bestanden.** Zusätzlich wurden der Frontend-Abgleich, die JavaScript-Syntax und die authentifizierten HA-WebSocket-Schemas geprüft.

Noch offen bleibt die **Live-Abnahme auf Home Assistant Green**, einschließlich Bedienbarkeit auf dem iPhone, erneuter Gießentscheidung nach Neustart und der Anzeige längerer Verläufe.
