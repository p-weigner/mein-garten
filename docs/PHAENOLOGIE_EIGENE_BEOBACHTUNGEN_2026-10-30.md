# Mein Garten – eigene Pflanzenentwicklung und phänologische Beobachtungen

**Entwicklungsstand: 30. Oktober 2026. Nur Draft-Pull-Request #1, nicht auf Home Assistant Green installiert.**

## Warum wir eigene Beobachtungen erfassen

Die deutschen [phänologischen Beobachtungen des DWD](https://opendata.dwd.de/climate_environment/CDC/observations_germany/phenology/) beschreiben unter anderem den zeitlichen Verlauf von Austrieb, Blüte und Fruchtreife an Beobachtungsstandorten. Solche Daten sind für das Verständnis der jahreszeitlichen Pflanzenentwicklung wertvoll, aber **keine** fachlich verifizierten Schnitt- oder Düngeanweisungen. Externe Beobachtungsdaten werden in dieser Entwicklungsstufe **nicht** abgerufen, kopiert oder als eigene Beobachtungen ausgegeben.

Stattdessen dokumentiert die Gartenanwendung den tatsächlichen Entwicklungsverlauf eurer selbst angelegten Pflanzen. Das ist unabhängig von nicht vorhandenen Saisonvorlagen aus OpenPlantDB, funktioniert offline und kostet keine monatliche Gebühr.

## Neue Bedienung in den bestehenden vier Bereichen

- **Pflanzen → Entwicklung:** Für eine angelegte Pflanze eine Entwicklungsphase und ein Beobachtungsdatum auswählen, optional eine eigene Notiz hinzufügen und speichern. Auch Pflanzen ohne botanischen Suchtreffer lassen sich beobachten.
- Die sieben vereinfachten, selbst dokumentierten Entwicklungsphasen: **Austrieb, Knospenbildung, Blütebeginn, Fruchtansatz, Fruchtreife, Laubfärbung und Blattfall**. Sie sind ein benutzerfreundliches Formular, **keine** vollständige DWD-Phasencodierung oder wissenschaftlich automatisch bestätigte Messung.
- In der Pflanzenkarte steht die jüngste eigene Beobachtung. Die Übersicht zeigt chronologisch die beobachteten Phasen. Wenn ein Blütebeginn für mehrere Jahre vorliegt, werden die frühesten **dokumentierten** Termine pro Jahr gegenübergestellt – ohne daraus eine Prognose abzuleiten.
- **Kalender:** Die sechs zuletzt dokumentierten Beobachtungen erscheinen in einem separaten Abschnitt unter dem Saisonfenster und **nicht** als offene Pflegeaufgabe. Keine Änderung an der bisherigen Kalendernavigation.
- **Freitagsübersicht:** Wenn die bestehende optionale Benachrichtigung bereits eingeschaltet ist, erscheinen dort neue eigene Beobachtungen der letzten sieben Tage. Es werden höchstens drei kurze Phasenmeldungen aufgeführt, ohne private Notiztexte, Personennamen oder präzise Ortsdaten. Bei ausgeschalteter Benachrichtigung gibt es weiterhin keinen Push.

## Datenhaltung, Historie und Schutzregeln

Die Datensätze liegen als neue Liste `beobachtungen` **ausschließlich** im bestehenden lokalen Speicher `.storage/mein_garten_v1.data`. Pro Beobachtung werden gespeichert: zufällige ID, verknüpfte Pflanzen-ID, eine der sieben Phasen, beobachtetes ISO-Kalenderdatum, optionale Notiz (max. 500 Zeichen), angemeldeter HA-Benutzer, der damals eingetragene botanische Name, die feste Herkunft `eigene_beobachtung` und ein UTC-Erstellungszeitpunkt.

- **Keine zukünftigen Beobachtungen:** Das Backend prüft die Datumsgrenze mit der tatsächlichen Home-Assistant-Zeitzone. Historische Beobachtungen können nachgetragen werden.
- **Keine doppelte Phase am selben Tag für dieselbe Pflanze:** Ein erneut gesendetes identisches Formular legt keinen zweiten Datensatz an; eine abweichende Notiz am selben Datum erzeugt einen Hinweis statt eines stillen Überschreibens.
- **Korrigierbar:** Einzelne Beobachtungen lassen sich löschen; auch die damit verbundenen Aktivitätsvermerke werden gelöscht.
- **Pflanze löschen:** Zugehörige Beobachtungen und ihre Aktivitätsvermerke werden entfernt. Beobachtungen anderer Pflanzen bleiben erhalten.
- **Art später ändern:** Der zum Zeitpunkt der ursprünglichen Beobachtung gespeicherte wissenschaftliche Name bleibt historisch nachvollziehbar.
- **Alte Garten-Alpha-Daten bleiben kompatibel:** Falls die Liste `beobachtungen` im bisherigen V1-Speicher fehlt, wird sie beim Laden im Arbeitsspeicher ergänzt. Eine beschädigte Speicherstruktur wird nicht durch leere Daten ersetzt.
- **Kein frei eingabefähiger Befehlskanal:** Nur zwei neue authentifizierte Home-Assistant-WebSocket-Aktionen für Anlegen und Löschen. Entwicklungsphasen müssen einer vorhandenen Pflanze und dem festgelegten Enum entsprechen.
- **Keine externe Datenübertragung:** Entwicklungsnotizen oder phänologische Einträge werden weder zur DWD-Seite noch an den Übersetzungsdienst geschickt. Eine eingeschaltete iPhone-Wochenübersicht übermittelt nur Pflanzenname, Phase und Datum an den vom Benutzer konfigurierten Home-Assistant-Benachrichtigungsempfänger.

## Zukunft: deutsche phänologische Daten getrennt einbinden

Der DWD veröffentlicht phänologische Beobachtungen für Deutschland unter einer [Open-Data-Lizenz CC BY 4.0](https://www.dwd.de/DE/service/copyright/copyright_node.html). Für eine spätere regionale Analyse müssen Beobachtungsstation, räumliche und zeitliche Abdeckung sowie Datenaktualität konkret geprüft und die Attribution erfüllt werden. **Eine Stationsbeobachtung oder eine überregionale Mittelzahl darf niemals als tatsächlicher Zustand der eigenen Gartenpflanze oder als gesicherter Pflegezeitpunkt ausgegeben werden.** Es erfolgt keine automatische Standortbestimmung.

Weitere offene Punkte: regionale Fachquellen zu Gehölz-, Rosen- und Staudenpflege, Rechtelage der OpenPlantbook-Freitexte, echte HACS-/Home-Assistant-Green-Laufzeitprüfung und iPhone-Ansicht einschließlich Backup/Rollback.

Die bisherige freigegebene dunkle Gartengestaltung, die vier Hauptansichten und das separate Dashboard **„Zuhause“** bleiben erhalten.
