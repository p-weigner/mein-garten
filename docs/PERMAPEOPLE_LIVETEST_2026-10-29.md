# Permapeople – authentifizierter Pflegequellen-Livetest

**Datum:** 29. Oktober 2026  
**Quelle:** vom Nutzer bereitgestelltes GitHub-Actions-Artefakt `mein-garten-pflegequellen.zip` und anschließender vertiefter Live-Test.  
**Vertiefter Workflow:** https://github.com/p-weigner/mein-garten/actions/runs/40868329416

## Ergebnis

- 21 repräsentative Arten aus fünf Gartengruppen getestet.
- **19/21** Arten mit streng exaktem wissenschaftlichem Namen und nutzbaren Werten; **2/21** ohne exakten Treffer.
- Fehlende Exakttreffer: `Buddleja davidii` und `Citrus × limon`. Dies beweist **nicht**, dass die API die Arten nicht unter Synonymen kennt; unser erster Suchadapter prüft nur exakte Namen aus der ersten Ergebnisseite.
- Bei allen 19 exakten Treffern: *Water requirement*, *Light requirement*, *Soil type*, *USDA Hardiness zone*.
- **11/19** mit eigenem Attribut `German name`.
- **11/19** mit nichtleerem Beschreibungstext; bei allen elf länger als 200 Zeichen.
- **3/19** Profile mit mindestens einem strukturierten Attribut für Saison, Aussaat, Ernte oder Pflanzzeit. Das ist noch **keine** vollständige Pflegeaufgabe.
- **0/19** Profile mit einem eigenständigen strukturierten Feldnamen für Schnitt/Pruning.
- **0/19** Profile mit einem eigenständigen strukturierten Feldnamen für Düngen/Fertilizing.
- Es wurden weitere Attribute zu Wuchsform, Höhe, Essbarkeit, Pflanzenteilen und Quellenlinks gefunden. Ihre fachliche Richtigkeit wurde **nicht** untersucht.

**Ein wichtiger Unterschied:** Die erste Version des Testberichts zeigte nur die vier von unserem Adapter übernommenen Felder. Erst der vertiefte Live-Test hat unabhängig davon die gesamten Attributnamen der 19 gefundenen Profile ausgewertet. Freitextbeschreibungen könnten Hinweise zu Schnitt und Düngung enthalten; ihre Inhalte wurden bewusst **nicht in das öffentliche Repository geschrieben**.

## Bewertung

**Permapeople = ergänzende Pflanzensteckbriefquelle, keine alleinige Grundlage für automatische Jahrespflegeplanung.**

Die API und die Daten sind für nichtkommerzielle Nutzung interessant. Die Rohdaten stehen unter CC BY-SA 4.0; beim Einbau sind Quellenangaben und Lizenzvorgaben einzuhalten. Allgemeine Angaben wie Essbarkeit, Giftigkeit und Warnungen dürfen weder ungeprüft noch automatisch als Sicherheitsfreigabe verwendet werden.

Es gab bei diesem Lauf keine API-Ausfälle. Das heißt nicht, dass Qualitäts-, Lizenz- und Übersetzungsfragen vollständig gelöst sind.

## Noch nicht live nachgewiesen

1. Welche Arten OpenPlantbook mit `include: care` tatsächlich mit **Schnitt- und Düngetexten** bedient.
2. Übersetzung echter englischer Pflegefelder ins Deutsche über einen zulässigen kostenlosen Dienst (Azure Translator F0 ist bisher nur offline simuliert).
3. Vollständigkeit, Genauigkeit und Nachnutzungsrechte von Pflegefreitexten.
4. Dynamisches Synonymhandling für nicht exakt gefundene Pflanzen.
5. Genügend fachlich abgesicherte Regeln für automatische Kalenderaufgaben.

## Folgerung für den Neuaufbau

- **Botanische Suche:** GBIF + iNaturalist (bereits öffentlich live getestet).
- **Basissteckbrief:** Permapeople optional, nie alleinige fachliche Autorität.
- **Pflanzenpflege:** Nächste Prüfung mit OpenPlantbook `include: care`, danach ggf. weiteren spezialisierten Quellen.
- **Deutsch:** Automatische Übersetzung als separate Schicht mit privatem Cache, Quellenangabe und Status.
- **Pflegekalender:** Ausschließlich anhand geeigneter artspezifischer, nachvollziehbarer Regeln. Keine ungeprüften Freitexte direkt in wiederkehrende Aufgaben umwandeln.
- **UI:** Neues Home-Assistant-Gartendashboard, keine manuelle Code-Erweiterung für neue Arten.

## Sicherheit

Das GitHub-Repository ist öffentlich. Es enthält keine persönlichen Gartenfotos, Pflanzenstandorte, privaten Nutzernotizen, API-Schlüssel oder vollständigen fremden Pflegefreitexte. Ein grüner Testlauf bestätigt nur die aufgerufenen Prüfungen – keine generelle inhaltliche Richtigkeit.
