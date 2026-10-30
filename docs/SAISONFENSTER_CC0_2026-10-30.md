# Mein Garten – strukturierte CC0-Saisonfenster (Entwurf vom 30. Oktober 2026)

**Status: nur GitHub-Entwicklungsbranch. Keine Installation oder Abnahme auf Home Assistant Green.**

## Was die Funktion kann – und was nicht

Der Kalender zeigt bei **exakt passender botanischer Art** strukturierte Aussaat-, Pflanz- und Vermehrungs-Zeitfenster aus einem fest versionierten, quelloffenen Datensatz. Es werden **keine autonomen Aussaat-, Schnitt-, Dünge- oder Pflanzenschutzarbeiten** erzeugt. Die Zahlen sind zunächst **US-Planungswerte**, keine fachlich für Brandenburg freigegebenen Handlungsanweisungen.

Die Nutzerin trägt für ein Gartenjahr den selbst angenommenen letzten Frühjahrsfrost und/oder ersten Herbstfrost ein. **Erst danach** wird ein Zeitfenster angezeigt. Ein Kontrolltermin wird ausschließlich nach ausdrücklich gewähltem Datum im möglichen Fenster gespeichert. Vergangene Zeitfenster sind nicht erneut buchbar; die Home-Assistant-Zeitzone bestimmt den heutigen Kalendertag.

## Zwei eingefrorene, offline verfügbare CC0-Datenstände

Quelle: [OpenPlantDB](https://github.com/cwfrazier1/openplantdb), Lizenz [CC0 1.0](https://github.com/cwfrazier1/openplantdb/blob/main/LICENSE).

| Eingebundener Datensatz | Exakter Upstream-Commit | Ursprüngliche OpenPlantDB-Einträge | Übernommene Arten |
|---|---|---:|---:|
| Basisstand vom 5. Juli 2026 | `99393ea2dbe8da6973434974f92863beff3bbb32` | 294 | 152 |
| Erweiterung vom 30. Oktober 2026 | `c6287784527ebb4162e242394ee08f46d338218b` | 34.841 | 1.140 zusätzliche |

**Zusammen 1.292 unterschiedliche Arten** im Offline-Katalog. Die neuere Quelle wurde über den SHA-256-Wert `aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751` eindeutig identifiziert.

### Warum nicht alle 34.841 Datensätze?

Viele beziehen sich auf verschiedene Kultivare derselben botanischen Art oder enthalten kein belastbar interpretierbares Frostanker-Intervall. Die Importprüfung fand **1.193 Arten mit untereinander identischen gültigen Frostzeitfenstern** und **200 Arten mit widersprüchlichen gültigen Zeitfenstern** in der neueren Quelle. Einträge mit solchen Widersprüchen werden nicht zu Durchschnittswerten umgerechnet. Schon durch den älteren Basisstand vertretene Arten erhalten **keinen stillen Ersatz**, auch wenn eine spätere Quelle sie anders bewertet.

Die ergänzte Importdatei enthält genau **1.140 zusätzliche Arten**. Bei bereits vorhandenen Arten gilt weiterhin der ursprüngliche Basisstand, einschließlich seines eigenen Quellcommits.

Der Import nutzt ausschließlich strukturierte Felder: wissenschaftlicher Name, Quellkennung, Kategorie, Art der Aussaat/Pflanzung/Vermehrung, Frostanker und Wochenintervall. **Keine Pflegefreitexte, Fotos oder unbewiesenen Schnitt- und Düngetermine** wurden übernommen.

Speicherdateien der Integration:

- `custom_components/mein_garten/data/saison_openplantdb_v0_1.json` (152 Basisregeln)
- `custom_components/mein_garten/data/saison_openplantdb_v0_2.json` (1.140 neue Regeln)

Die beiden JSON-Dateien zusammen sind deutlich kleiner als die über 70 MB große Upstream-Gesamtdatei. Home Assistant lädt **nur** die kompakte lokale Auswahl und benötigt zur Laufzeit keinerlei OpenPlantDB-Zugang, API-Schlüssel oder Abonnement.

## Reale Abdeckung bei 50 typischen deutschen Gartenpflanzen

Von unserer repräsentativen Suchtestliste mit 50 Pflanzen besitzen **15** mindestens eine passende strukturierte Saisonvorlage. Der ältere Katalog deckte **10** ab.

| Gruppe | Saisonvorlage vorhanden | Testpflanzen |
|---|---:|---:|
| Blumen, Stauden und Rosen | 3 | 10 |
| Sträucher, Hecken und Bäume | 1 | 10 |
| Gemüse und Kräuter | 6 | 10 |
| Obst und Beeren | 1 | 10 |
| Kübel- und Topfpflanzen | 4 | 10 |
| **Gesamt** | **15** | **50** |

Die große Datenbank ist **kein Ersatz für deutsche Fachquellen**, insbesondere für Gehölze, Rosen, Sträucher und Stauden. Pflanzen ohne Quelle lassen sich trotzdem hinzufügen, pflegen und mit eigenen wiederkehrenden Aufgaben verwalten. Der Kalender zeigt bei den tatsächlich erfassten eigenen Pflanzen die **Abdeckung und fehlende Saisoninformationen** an.

## Beispiel ohne regionale Handlungsempfehlung

Für `Solanum lycopersicum` steht in der alten CC0-Version „6–8 Wochen vor dem letzten Frühjahrsfrost vorziehen“. Bei einem rein hypothetisch gewählten Referenzdatum **15. Mai 2027** errechnet das System den Zeitraum **20. März bis 3. April 2027**. Erst wenn die Nutzerin selbst einen Tag innerhalb des Zeitraums bestätigt, entsteht die Kontrollaufgabe „Vorziehen prüfen“. Weder eine Aussaat noch ein Pflegeeingriff wird automatisch ausgeführt.

## Technische und fachliche Sicherheitsgrenzen

- Botanischer Name muss exakt passen. Unklare Sorten- und Synonymzuordnungen erhalten keine erfundene Regel.
- Saisonquellen behalten dauerhaft **ihre eigene Git-Version**, die CC0-Lizenz und die damals gewählte botanische Art – auch bei nachträglicher Pflanzenbearbeitung.
- Eine zwischen dem Auswählen und Speichern geänderte Pflanzenart stoppt die Terminbuchung.
- Pro Pflanze, Saisonvorlage und Referenzjahr entsteht höchstens ein Termin, auch nach einem Neustart. Erledigte Termine dürfen nicht überschrieben werden.
- Die Frost-Referenzdaten sind **persönliche Annahmen**. Weder USDA-Klimazonen noch momentane Wetterprognosen werden automatisch als „letzter Frostag“ ausgegeben.
- Datum außerhalb des Quellenfensters oder in der Vergangenheit, unvollständige Katalogdateien und widersprüchliche Artidentitäten werden abgelehnt.
- Für Deutschland belastbare artspezifische Schnitt-, Dünge-, Krankheits- und Frosthärtedaten fehlen weiterhin. Solche konkreten Maßnahmen werden nicht autonom erzeugt.
- [DWD-Phänologie](https://wetterdienst.readthedocs.io/en/latest/data/provider/dwd/phenology/index.html) kann perspektivisch lokale Entwicklungsstadien unterstützen, ist aber **keine** geprüfte Quelle für Pflegehandlungen und bisher nicht integriert.

## Persistenz, Abnahme und Betrieb

Private Gartenangaben: `.storage/mein_garten_v1.data`

Persönliche Frost-Referenzdaten: `.storage/mein_garten_saison_v1.data`

Offline-Quellen: die beiden JSON-Dateien in `custom_components/mein_garten/data/`

Die gesamte Entwicklung läuft auf dem Draft-Branch [Pull-Request #1](https://github.com/p-weigner/mein-garten/pull/1). Vor Freigabe bleiben echte Tests auf Home Assistant Green mit Neustart, UI auf iPhone/Tablet, Wetter-/Notify-Diensten, Dokumentationsstand, Backup und Rollback erforderlich. Das eigenständige Dashboard **„Zuhause“ bleibt unangetastet**.
