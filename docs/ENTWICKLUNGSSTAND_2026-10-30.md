# Mein Garten – Entwicklungsstand nach der Alpha (30.10.2026)

**Status:** Entwicklung auf Branch `codex/garten-pflegewissen-und-suche-20261030`, [Draft-Pull-Request #1](https://github.com/p-weigner/mein-garten/pull/1). **Nicht auf Home Assistant Green installiert oder dort live getestet. Nicht mergen und nicht als produktives HACS-Release bereitstellen.** Das Dashboard „Zuhause“ wird nicht verändert.

## Neu implementiert (Quellcode und isolierte Tests)

| Bereich | Verhalten |
|---|---|
| Pflanzensuche | iNaturalist + Wikidata + wissenschaftliche GBIF-Suche + GBIF-Trivialnamensindex; Trivialnamen ausschließlich für akzeptierte botanische Pflanzenarten aus dem GBIF-Backbone, Mehrdeutigkeiten im Dashboard sichtbar; deutsche positive Treffer in begrenztem lokalen Namenscache für 365 Tage und als Präfix-Fallback bei API-Ausfall |
| Pflegewissen-Dialog | Echte deutsche Pflegefelder erscheinen als eigene Karten mit Quellen-/Übersetzungsstatus; fehlende Felder werden kompakt gezählt statt als leere Karten dargestellt. Eigene Pflanzennotizen bleiben lokal und erscheinen unabhängig von der externen Quelle auch während deren Ladezeit oder Ausfall. Eine schnelle Bearbeitung der Notizen ist möglich, ohne neue automatische Pflegetermine zu erfinden. |
| Pflegeprofile | Per Pflanzenkarte abrufbar; bestehende Home-Assistant-OpenPlantbook-Integration, `search` und `get` mit `include: care`; strenger botanischer Artabgleich; fünf Pflegefelder |
| Pflegequelle erneut prüfen | Im Pflegewissen-Dialog gezielte OpenPlantbook-Neuprüfung (maximal alle 5 Minuten pro Art), ohne automatisch auf Cacheablauf warten zu müssen. Während der Aktualisierung bleiben vorher angezeigte Informationen sichtbar. Bei temporärem Fehler, komplett leerer oder teilweise fehlender neuer Antwort bleiben zuvor gespeicherte deutsche Hinweise feldweise erhalten. Historische Felder erscheinen mit Warn-Chip, altem Abrufdatum und ohne Planungsaktion; frisch geladene Felder bleiben separat. Kein Umgehen des 5.000-Zeichen-Übersetzungsbudgets. [Dokumentation und nachgewiesene 334 Python- und 60 Node-Tests](PFLEGEWISSEN_AKTUALISIERUNG_2026-10-30.md) |
| Europäische EIVE-Standortindikatoren | **10.683 exakt zugeordnete europäische Pflanzenarten** in einem lokal gespeicherten, ca. 255 KB großen CC-BY-4.0-Textkatalog aus einem geprüften Forschungsdatensatz. Fünf getrennt erklärte relative ökologische Zeigerwerte (Licht, Bodenfeuchte, Nährstoffe, Bodenreaktion, Temperatur) mit Zahl der Quellsysteme, Warnung bei nur einem Quellsystem und sichtbarer DOI-/Lizenznennung. Keine Aussage über konkrete Gieß-, Schnitt-, Dünge-, Frost- oder Pflanztermine, keine persönlichen Notizen in dieser Quelle. Optional: Bei Datenfehlern bleibt die übrige Gartenanwendung erreichbar. [Technische und fachliche Einordnung](EIVE_EUROPA_STANDORTWISSEN_2026-10-30.md) |
| CC0-Standort-Steckbriefe | **10.642 botanische Arten** aus einem kleinen, festen OpenPlantDB-Offline-Datensatz. Allgemeine Licht-, Wasser-, Frosttoleranz- und Wachstums-Kategorien erscheinen im Pflegewissen **sofort und ohne OpenPlantbook**. Bei widersprüchlichen Sortenwerten werden die jeweiligen Felder weggelassen; keine automatische Bewässerung oder regional behauptete Winterhärte |
| Deutsch | Automatische Übersetzung der externen Pflegefelder über MyMemory, maximal 5.000 Zeichen pro Tag, lokal begrenzter privater Cache; ausstehende oder nicht vorhandene Angaben werden als solche angezeigt |
| Wiederholungen | Benutzerdefinierte Regeln alle 1–365 Tage oder jährlich; erster Termin ausdrücklich vom Benutzer angegeben; nicht doppelt bei Neustart; Pause und Löschung |
| Pflegewissen → Termin | Aus einem deutschen Pflegefeld lässt sich eine **Jahreskontrolle** erstellen. Der Termin wird erst nach eigener Datumseingabe angelegt, und der Bezug auf die nicht fachlich geprüfte Quelle bleibt sichtbar |
| Wetter | Optionaler Frost-Check über `weather.get_forecasts` (stündlich, bei Bedarf täglich); 48-Stunden-Fenster, Warnschwelle standardmäßig +2 °C, mit Validierung von Datum, Einheit und Messwert |
| Wetteraufgabe | Bei aktivierter Frostprüfung ein einmaliger Kalendereintrag pro prognostiziertem Frosttag: **Pflanzen kontrollieren**, keine Behandlung; Dublettenschutz im Datenspeicher |
| Push | Optionale Push-Nachricht für mögliche Frostgefahr und eine zusammenfassende Benachrichtigung freitags 16 Uhr über ausgewählte Home-Assistant-Notify-Entität oder gerätespezifischen Dienst |
| Standardsicherheit | Pushs anfänglich **aus**. Es wird kein allgemeiner Broadcast-Dienst angeboten; Wetter- und Notify-Ziel müssen explizit angegeben werden |
| Gießkontrolle mit Verlaufskontext | Die letzte tatsächlich dokumentierte Gießkontrolle, die letzte echte Bewässerung und offene Gießkontrollen erscheinen beim **manuellen Anlegen, Wiederholen und Abschließen**; alternative Pflanzen lassen sich im Formular wechseln. Der neue Schnellzugriff aus dem Pflanzenverlauf öffnet nur ein vorausgefülltes Formular, ohne Datum, automatisch erzeugte Aufgaben oder geschätzte Gießintervalle. [Bedienung und Grenzen](GIESSKONTROLLE_MIT_VERLAUFSKONTEXT_2026-10-30.md) |
| Pflegeverlauf pro Pflanze | Eigener **„Verlauf“**-Button auf jeder Pflanzenkarte: Chronik gegenwärtig erledigter Aufgaben, getrennte Zähler für tatsächliches Gießen und Kontrollen ohne Wasser, letzter Kontroll- und letzter Gießzeitpunkt, schrittweises Nachladen älterer Erledigungen. Person und Zeiten stammen ausschließlich aus dem vorhandenen lokalen Aufgaben-/Ereignisspeicher. Wieder geöffnete, gelöschte und fremde Aufgaben werden nicht als erledigt gezählt. Keine zusätzlichen Pflegeintervalle, keine Cloud-Dienste. [Details und Tests](PFLEGEVERLAUF_PRO_PFLANZE_2026-10-30.md) |
| Kombinierte Erledigung | Einfache Aufgaben bleiben 1-Klick-Aufgaben. Gießkontrollen verlangen die Entscheidung „Gegossen“ oder „Kontrolliert – kein Wasser nötig“. Beide Fälle werden mit Benutzer, Zeitpunkt und Ergebnis in der Historie geführt |
| Differenzierte Wiederholungen | Neu angelegte Gießkontrollen behalten ihre Art bei Fälligkeit, Neustart und Folgeintervall. Der Quellstatus bleibt auch nach Entfernen einer Wiederholungsregel am erledigten Termin |
| Pflegeprofil-Cache | Vollständig übersetzte Profile bleiben bis zu 30 Tage zwischengespeichert, teilweise übersetzte nur kurz; bereits übersetzte Felder werden per Quellenfingerabdruck lokal wiederverwendet. Eindeutig als deutsch deklarierte Quellfelder werden nicht durch Englisch-Deutsch-Übersetzung verändert |
| Such-Breitenprüfung | 50 reale deutsche Gartennamen aus fünf Gruppen mit aktuellem Suchcode geprüft: 50/50 erwartete botanische Arten in den ersten 15 Vorschlägen, 40/50 auf Rang 1 (repräsentative Live-Stichprobe, keine Aussage zur gesamten deutschen Gartenflora); keine festen Beispielaliases in der App |

**Ausführung (lokale Home-Assistant-Zeitzone):** wiederkehrende Aufgaben jeden Tag um 00:05 Uhr und bei Aktivierung/Erstellung; Frostprüfung täglich 06:15 und 18:15 Uhr; Wochenübersicht freitags um 16:00 Uhr. Nach einem Neustart wird der Pflegeplan erneut geprüft. Ein automatischer Push unmittelbar nach der Installation ist nicht vorgesehen.

### Bedienung nach einer späteren Freigabe

1. **Pflanzen → Pflegewissen** öffnen. Bei vorhandenen übersetzten Informationen kann „Jährliche Kontrolle dazu planen“ gewählt werden. **Datum selbst festlegen und speichern**. Das ist eine Erinnerungsregel und ausdrücklich keine geprüfte Schnitt- oder Düngeanweisung.
2. **Kalender → Benachrichtigungen** öffnen. Bestehenden iPhone-Empfänger aus Home Assistant auswählen und für Frostwarnungen auch eine vorhandene Wetterentität angeben. Wöchentliche Zusammenfassung und Frostwarnung können separat eingeschaltet werden.
3. **Kalender → Meine Wiederholungen** verwaltet bestehende manuell angelegte Intervalle und Jahresregeln. Frostaufgaben erscheinen als Wetterprognose gekennzeichnet.

## Neue Quellenqualitätsprüfung nach der Alpha (30.10.2026)

Ein separater GitHub-Actions-Workflow analysiert die CC0-Freitexte von OpenPlantDB (Anbauhinweise und Pflanznotizen) beim festgepinnten Quellcommit mit SHA-256-Prüfung. Ergebnis: **34.841 Rohdaten**, **10.645 exakte Arten**, **9.936 einheitliche Anbautexte**, **650 Arten mit widersprüchlichen Anbautexten**. In der bestehenden 50er-Stichprobe sind nur **19** Anbautexte unter den vorhandenen Varianten einheitlich. Acht neue Offline-Tests sind erfolgreich. [Messung, Einschränkungen und Quellen](ANBAUHINWEISE_QUELLENAUDIT_2026-10-30.md), [CI-Lauf](https://github.com/p-weigner/mein-garten/actions/runs/41074491039).

**Noch nicht integriert:** Diese englischen Pflegefreitexte sind nicht regional und fachlich bestätigt und werden weder importiert noch im Dashboard angezeigt oder für Aufgaben benutzt. Das bestehende deutsche Pflegewissen und alle bisherigen Funktionen bleiben unverändert.

## Persistenz

- Gartendaten, Nutzerregeln und eigene Pflanzenentwicklungsbeobachtungen: `.storage/mein_garten_v1.data`
- Deutsche Pflegeprofile und Übersetzungsbudget: `.storage/mein_garten_pflege_v1.data`
- Benachrichtigungseinstellungen und Anti-Duplikat-Markierungen: `.storage/mein_garten_hinweise_v1.data`
- Lokal erfasste positive Pflanzennamen: `.storage/mein_garten_namen_v1.data`

Keine Codeänderung für neu angelegte Pflanzen. Die persönlichen Gartennotizen und Gartenbereiche werden weder an die Pflanzensuche noch an die Übersetzung gesendet. Für Übersetzungen werden die **externen Pflegequelltexte** an MyMemory übermittelt. Die Suchbegriffe werden an iNaturalist, Wikidata und GBIF gesendet.

## Botanische Suchabdeckung: echte 50er-Testreihe

- [Erster Live-Test](https://github.com/p-weigner/mein-garten/actions/runs/41043378877): 41/50 Art-Treffer in Top 15, 28/50 auf Rang 1.
- [Zweiter Live-Test nach Sortierkorrektur](https://github.com/p-weigner/mein-garten/actions/runs/41043740909): **42/50 Art-Treffer in Top 15, 38/50 auf Rang 1**.
- [Dritter Test nach GBIF-Trivialnamensintegration und Relevanzoptimierung](https://github.com/p-weigner/mein-garten/actions/runs/41046617157): **48/50 erwartete Arten in Top 15, 38/50 auf Rang 1**.
- [Vierter Test mit generischer Kompositum-/Bindestrich-Rückfallsuche](https://github.com/p-weigner/mein-garten/actions/runs/41047293989): **50/50 erwartete Arten in Top 15, 40/50 auf Rang 1**.
- Die beiden zuvor fehlenden Namen werden über ein allgemeines Verfahren gefunden: Falls sämtliche regulären Anbieter keine Art liefern, wird bei langen deutschen Wörtern ein kurzer erster Wortabschnitt erneut bei iNaturalist gesucht und ein botanisch akzeptierter Treffer **nur dann** übernommen, wenn der vollständige deutsche Namenstext nach Bindestrich-/Leerzeichen-Normalisierung übereinstimmt. Bei Namen mit mehreren Wörtern ergänzen GBIF-Trivialnamen des letzten langen Wortteils alternative, als **prüfbedürftig** gekennzeichnete Kandidaten.
- Keine der 50 Benchmarkarten ist als Sonderregel in der produktiven Suchlogik hinterlegt. Ein gültiger botanischer Taxonname bestätigt nicht die Eindeutigkeit eines deutschen Sammelnamens; die Nutzerin wählt die konkrete Art.
- Bei Sammelnamen (z. B. „Felsenbirne“) liefert der Trivialnamensindex mehrere botanisch akzeptierte Arten. Eine akzeptierte Art ist kein Beweis, dass der deutsche Sammelname eindeutig wäre; die Nutzerin wählt die tatsächliche Art.
- Das Wikimedia-/Wikidata-Fallback wurde in einer separaten Live-Diagnose untersucht, lieferte in der GitHub-Runner-Umgebung nur HTTP-Fehler und wird deshalb **nicht** als zusätzliche Abhängigkeit in die Suchlogik integriert.
- [50 Testarten](../daten/pflanzensuche_50_de.json), [reproduzierbarer Live-Test](../tools/pflanzensuche_50_live.py) und [Quellen-/Lizenzprüfung](FACHQUELLEN_FREIGABE_2026-10-30.md).

## Strukturierte Standort-Grundlagen ohne fremde Pflegefreitexte

- **10.642 botanisch eindeutige Arten** mit mindestens einer verwendbaren CC0-Standortkategorie, aus dem fest versionierten OpenPlantDB-Stand mit 34.841 Rohdatensätzen. Nur eine etwa 645 KB große Offline-Datei in der Integration; Hash und Quellcommit sind gepinnt.
- Die 50 deutschen Testpflanzen erhalten nun **46 Profile mit mindestens einer Angabe**, davon **37 mit Licht und Wasser zugleich**. Das ist deutlich breiter als die nur **15/50** saisonal unterstützten Arten.
- Quellkonflikte werden je Feld ausgeschlossen statt gemittelt: Licht bei 133 Arten, Wasser bei 148, Frostkategorie bei 117, Wachstumsgruppe bei 74. Beispiel *Hydrangea macrophylla*: Licht vorhanden, Wasser aus widersprüchlichen Werten **nicht** übernommen.
- Das Dashboard zeigt die Basisangaben sofort in **Pflanzen → Pflegewissen**, auch wenn OpenPlantbook nicht eingerichtet oder erreichbar ist. Die separaten übersetzten OpenPlantbook-Texte bleiben optisch und fachlich als eigene Quelle gekennzeichnet.
- **Keine** neuen Standortabfragen, API-Schlüssel oder Monatsgebühren. Die WebSocket-Antwort überträgt nur Profilwerte zu **den eigenen erfassten Pflanzen**, nicht alle 10.642 Arten.
- Sonnen-, Wasser- und Frostkategorien sind allgemeine Quellangaben, keine für Brandenburg geprüften Pflege-, Bewässerungs- oder Winterhärteanweisungen. Daraus entstehen **keine** automatischen Aufgaben.
- [Vollständige Abdeckung, Qualitätsmessung, Quelle und Lizenz](STANDORTWISSEN_CC0_2026-10-30.md).

## Amtliche DWD-Phänologie als separater, read-only Regionalvergleich

- Neu: Unter **Kalender → DWD: Jahreszeiten im Vergleich** erscheinen drei meteorologisch-phänologische Indikatoren als **historisch beobachtete** Jahresdaten (Haselblüte, Forsythienblüte, Rotbuchen-Blattentfaltung).
- Aus dem offiziellen DWD-Sofortmelder-Netz wurden für **2024, 2025 und 2026** insgesamt **18** statistische Vergleiche vorverarbeitet: je Indikator die Region **Nordost (grobes Rechteck 52–54,2° N / 12–15° O)** und Deutschland insgesamt. Die Region ist **kein exakter Nutzerstandort, keine amtliche Landesgrenze und keine Grundstücksmessung**.
- Jeder Eintrag zeigt **Median der tatsächlichen Eintrittsdaten, unteres/oberes Quartil, Anzahl der berücksichtigten Stationen, DWD-Quelle und CC-BY-4.0-Lizenz**. Ausgegeben wird nur bei mindestens fünf widerspruchsfreien Stationsmeldungen. Der jüngere Datenstand ist teilweise lediglich **formal** geprüft.
- Die 3 offiziellen Quelldateien plus Stationskatalog wurden in einem getrennten GitHub-Actions-Export mit SHA-256-Nachweis zu einem **ca. 7 KB großen statischen Offline-Snapshot** zusammengefasst. Auf Home Assistant Green entstehen **keine DWD-Webzugriffe, keine präzise Standortabfrage und keine Zusatzkosten**.
- Technische Laufzeit: `custom_components/mein_garten/dwd_reference.py` validiert den Snapshot und gibt ihn nur **lesend** an das Kalender-Dashboard weiter. Falls der optionale Snapshot beschädigt ist, bleiben die vorhandenen Pflanzen, Kalenderaufgaben und Beobachtungen verfügbar.
- Die DWD-Phasen werden **nicht** als eigene Pflanzenbeobachtungen gespeichert und **nicht** automatisch in Schnitt-, Dünge- oder Aussaattermine übersetzt.
- [Regionalvergleich: Datenlage, Qualitätsflags, Lizenz, Begrenzungen](PHAENOLOGIE_DWD_REGIONAL_2026-10-30.md).

## Eigene phänologische Gartenbeobachtungen

- Neu: **Pflanzen → Entwicklung** für jede gespeicherte Pflanze, auch ohne botanischen Datenbanktreffer. Sieben kontrollierte Beobachtungsphasen, tatsächliches Datum und optionale private Notiz. Die beobachtete botanische Art bleibt als Historienreferenz bestehen.
- Neue Liste `beobachtungen` im vorhandenen lokalen Garten-Store. Alte V1-Speicher werden ohne Datenverlust erweitert. Einträge sind auf der Home-Assistant-Ortszeit geprüft; zukünftige Beobachtungen, ungültige Phasen und doppelte Eingaben werden abgelehnt. Löschungen entfernen auch ihre Aktivitätsbezüge.
- Im Pflanzenbereich erscheint die jüngste Beobachtung. In einem eigenen Dialog stehen der Verlauf und ein Vergleich des frühesten **dokumentierten** Blütebeginns mehrerer Jahre. **Kein** automatisches Erkennen biologischer Phasen und keine Prognose zukünftiger Termine.
- Unter **Kalender** stehen die letzten tatsächlichen Pflanzenbeobachtungen getrennt von offenen Aufgaben. Die schon vorhandene freitägliche iPhone-Übersicht kann sie bei aktivierter Einstellung als kurze Zusammenfassung aufführen; **Notizen, Beobachternamen und genaue Standortdaten werden nicht per Push übermittelt**.
- Keine DWD-Daten abgerufen, keine neuen Internetabfragen oder zusätzlichen kostenpflichtigen Dienste. Für eine spätere regionale Analyse kann [DWD-Phänologie](https://opendata.dwd.de/climate_environment/CDC/observations_germany/phenology/) eine getrennte, mit Herkunft und räumlicher Unsicherheit ausgewiesene Kontextquelle sein, ist aber keine verlässliche Quelle für konkrete Schnitt- oder Düngeanweisungen.
- [Dokumentation der Pflanzenentwicklung](PHAENOLOGIE_EIGENE_BEOBACHTUNGEN_2026-10-30.md).

## Strukturierter Saisonkalender als Planungshilfe

- **1.292 eindeutige CC0-Saison-Datensätze** aus zwei fest versionierten OpenPlantDB-Snapshots: 152 vom 5. Juli 2026 (`99393ea2dbe8da6973434974f92863beff3bbb32`) und 1.140 zusätzliche vom 30. Oktober 2026 (`c6287784527ebb4162e242394ee08f46d338218b`). Von 34.841 neuesten Rohdatensätzen wurden nur botanisch eindeutige Arten mit konsistentem Frostfenster in den lokalen Katalog übernommen. Kein Download der großen Quelldatei auf Home Assistant Green.
- Botanisch exakter Artabgleich; nur die unterstützten Frostanker last_frost/first_frost und quellgebundene Wochenintervalle werden übernommen. Keine unbekannten Gattungen/Sorten oder fehlenden Daten schätzen.
- Der Nutzer legt Frostreferenztage **selbst** fest. Die berechneten Zeitfenster sind ausdrücklich US-Planungswerte, keine lokale Brandenburg-Fachfreigabe.
- Neue Ansicht im **Pflegekalender**: Saisonfenster, Quellen-/Lizenzinformation, Eingabe der Referenztage und manuell bestätigte Kontrollaufgaben. **Keine** automatische Aussaat, Schnittarbeit oder Düngung.
- Ein Saisontermin ist je Pflanze, Vorlage und Referenzjahr eindeutig und enthält die Quellversionsnummer dauerhaft.
- Für die repräsentative Liste mit 50 deutschen Gartenpflanzen bestehen inzwischen **15** fachlich noch ungeprüfte Saisonfenster (zuvor 10). Besonders Gehölze, Rosen und Stauden haben weiterhin große Datenlücken; der Kalender zeigt fehlende Artvorlagen sichtbar an.
- Vergangene Saisonfenster werden anhand der Home-Assistant-Ortszeit markiert und können nicht erneut als „neue“ Termine angelegt werden.
- Weitere Informationen: [CC0-Saisonfenster](SAISONFENSTER_CC0_2026-10-30.md).

## Grenzen und notwendige Abnahme

1. **Artspezifische Saison-Automatik noch nicht freigegeben:** Eine vertrauenswürdige, lizenzrechtlich zulässige und fachlich validierte strukturierte Quelle für Schnitt-, Dünge- und Pflanzenpflegekalender fehlt weiterhin. Es werden keine entsprechenden Maßnahmen aus einem ungeprüften Pflegefreitext abgeleitet.
2. **Keine garantierte Artabdeckung:** Auch drei Namensquellen und ein Cache garantieren nicht jede in Deutschland kultivierte Art oder Sorte. Ohne sichere Artzuordnung bleiben Pflegehinweise aus.
3. **Nutzungsrechte klären:** OpenPlantbook-Texte, automatische Übersetzung und langfristige Speicherung dürfen erst nach Prüfung der konkreten Nutzungsbedingungen produktiv freigegeben werden.
4. **Echte Home-Assistant-Green-Laufzeitprüfung ausstehend:** Testen: OpenPlantbook-Actions, Push-Entität oder Dienst, vorhandene Wetterentität, HA-Start/Entladen, Tageswechsel/DST, API-Ausfälle, Übersetzungslimits, Einrichten/Deaktivieren und Browser auf iPhone/Tablet.
5. **Gärtnerische Plausibilitätsprüfung:** Mindestens 50 Pflanzen aus allen vereinbarten Gruppen testen. Bei Wetterwarnungen immer darauf hinweisen, dass eine Temperaturprognose weder amtliche Unwetterwarnung noch artspezifische Gefährdungsbeurteilung ist.
6. **Kein kostenpflichtiger Dienst:** Es werden öffentliche Datenquellen, kostenlose Übersetzungskontingente und vorhandene Home-Assistant-Dienste eingesetzt. Kontingente, API-Verfügbarkeit und persönliche Nutzungsvoraussetzungen bleiben anbieterabhängig.

### Technische Referenzen

- [Home Assistant: Wettervorhersage abrufen](https://www.home-assistant.io/actions/weather.get_forecasts/)
- [Home Assistant: Benachrichtigung an Notify-Entitäten](https://www.home-assistant.io/actions/notify.send_message/)
- [Home Assistant: klassische Benachrichtigungsaktionen](https://www.home-assistant.io/actions/notify.notify/)
- [Home Assistant OpenPlantbook Integration](https://github.com/Olen/home-assistant-openplantbook)

Der Draft-Branch bleibt von `main` getrennt. Das bisherige Garten-Dashboard kann später ersetzt werden; „Zuhause“ und andere Home-Assistant-Funktionen bleiben außen vor.
