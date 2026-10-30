# Mein Garten – Gießkontrollen mit persönlichem Verlaufskontext (30.10.2026)

**Entwicklungsbranch / Draft-PR #1. Noch nicht auf Home Assistant Green installiert, keine Änderungen an `main` oder am getrennten Dashboard „Zuhause“.**

## Ziel

Der bereits vorhandene Pflegeverlauf wird beim **manuellen Planen und Abschließen einer Gießkontrolle** als Orientierung angezeigt. Keine fremde Quelle, keine neue Wettervorhersage, keine zusätzlichen Dienste und **keine automatisch geschätzten Gießintervalle**. Die Person entscheidet selbst, ob Wasser erforderlich ist, wann die nächste Prüfung stattfinden soll und ob eine Aufgabe gespeichert wird.

## Bedienung

Im Bereich **Pflanzen → Verlauf** gibt es einen neuen Button **„＋ Gießkontrolle anlegen“**. Er öffnet das vorhandene Formular **Neue Pflegeaufgabe** mit vorausgewählter Pflanze, deren Gartenbereich, „Gießkontrolle“ als Erledigungsart und einem passenden frei änderbaren Namen. Das Datumsfeld bleibt **leer**. **Es wird keine Aufgabe angelegt, bevor die Nutzerin auf „Aufgabe speichern“ tippt.**

Beim manuellen Anlegen einer Aufgabe über **Start** oder **Pflegekalender** erscheint derselbe Kontext erst dann, wenn die Erledigungsart **„Gießkontrolle“** gewählt wird. Wird eine Pflanze nachträglich ausgewählt oder geändert, aktualisiert sich ausschließlich der Infobereich. Andere Formulareingaben (z. B. Termin und Name) bleiben erhalten. Die Aktualisierung berücksichtigt die für iOS relevanten `change`-Ereignisse.

Beim Anlegen einer **Wiederholung** bleibt der bisherige Ablauf ebenfalls erhalten. Falls eine Gießkontrolle für eine konkrete Pflanze ausgewählt ist, zeigt der Dialog deren eigene Historie. Das Startdatum und der Rhythmus werden daraus **nicht** berechnet.

Beim **Abschließen einer bereits offenen Gießkontrolle** steht der bisherige Verlauf unmittelbar über den beiden bestätigungspflichtigen Ergebnissen „Gegossen“ und „Kontrolliert – kein Wasser nötig“.

## Was im Kontext steht

- **Letzte Gießkontrolle:** tatsächlicher Zeitpunkt und gewähltes Ergebnis.
- **Zuletzt tatsächlich gegossen:** nur Aufgaben, deren Ergebnis `gegossen` lautet. „Kein Wasser nötig“ zählt nicht als Bewässerung.
- **Vorhandene offene Gießkontrollen:** Kennzeichnung, wenn bereits eine andere offene Gießkontrolle für dieselbe Pflanze besteht; **nur Hinweis**, keine erzwungene automatische Löschung oder Zusammenführung.
- **Fehlende Historie:** „Noch keine Gießkontrolle dokumentiert“ und „Noch kein tatsächliches Gießen dokumentiert“.
- **Keine Pflanze ausgewählt:** kompakter Hinweis, dass zunächst eine Pflanzenzuordnung erforderlich ist.
- **Ungültiger alter Zeitstempel:** „Zeitpunkt nicht gespeichert“ statt einer erfundenen Zeitangabe.

Es erscheinen ausschließlich die Daten der **gewählten, eigenen Pflanze** aus dem bereits authentifizierten lokalen Garten-Snapshot. Namen werden HTML-sicher dargestellt. Private Pflanzennotizen, Personenkennungen und Gießentscheidungen werden an keinen externen Anbieter übertragen.

## Abgrenzung zu Pflegewissen

Diese Funktion interpretiert **nicht**, ob die Pflanze Wasser benötigt. Sie ignoriert wissenschaftliche EIVE-Indikatoren, US-Standortkategorien und unbestätigte OpenPlantbook-Freitexte als Basis einer vermeintlich automatischen Gießempfehlung. Die Anzeige bleibt persönlicher Verlauf – keine medizinisch, meteorologisch oder gärtnerisch validierte Handlungsempfehlung.

Der Verlauf bleibt schreibgeschützt; er ändert weder gespeicherte Aufgaben noch persönliche Wiederholungsregeln. Der neu hinzugefügte Schnellzugriff erstellt lediglich eine **Formular-Vorauswahl**, nie automatisch einen Termin.

## Technische Umsetzung

- JavaScript: [`frontend/mein-garten-card.js`](../frontend/mein-garten-card.js)
- Identische integrierte Kopie: [`custom_components/mein_garten/frontend/mein-garten-card.js`](../custom_components/mein_garten/frontend/mein-garten-card.js)
- Neue dynamische UI-Funktionen: `_giessKontextHTML`, `_pflegekontextAktualisieren`; bestehende lokale `_pflegeverlaufDaten`-Berechnung weiterverwendet.
- Benutzerbestätigung: weiterhin ausschließlich über `_onSubmit` beziehungsweise die beiden bestätigten `task-water-choice`-Aktionen.
- Regressionstests: [`frontend/tests/card.test.mjs`](../frontend/tests/card.test.mjs), insbesondere Pflanzenisolation, gespeicherte Entscheidungen, vorhandene offene Aufgabe, vorausgefülltes Formular ohne Datum, unveränderte Felder beim iPhone-`change`, XSS-Schutz und fehlende automatische `_mutate`-Aufrufe.

**Offen:** wirklicher Live-Test der iPhone-Bedienung mit der laufenden Integration auf Home Assistant Green. Erst nach erfolgreicher CI und Live-Abnahme als produktiv freigeben.
