# Mein Garten – Fachquellen- und Freigabeprüfung (30.10.2026)

**Entwicklung, keine Produktivfreigabe.** Fachliche und lizenzrechtliche Entscheidungen getrennt von technischen API-Erfolgen betrachten. Ein erfolgreich abgerufener Text ist keine gärtnerische Handlungsempfehlung.

## Externe Datenquellen: geprüfter Iststand

| Quelle | Nachweis | Eignung | Automatische Saisonmaßnahmen? |
|---|---|---|---|
| OpenPlantbook | [Webseite](https://open.plantbook.io/browse-db/), [HA-Anbindung](https://github.com/Olen/home-assistant-openplantbook) | Exakt abgeglichene botanische Art, fünf zusätzliche Pflege-Freitextfelder via `include: care`; öffentlich einsehbare Plattform weist ausdrücklich darauf hin, dass Nutzerdaten nicht verifiziert sind | **Nein**. Keine nachgewiesenen strukturierten, für Deutschland verifizierten Monats-/Saisonregeln; Rechte für abgeleitete deutsche, dauerhaft gespeicherte Texte vor Produktivstart klären |
| GBIF | [Species API](https://www.gbif.org/developer/species) | Internationale taxonomische Namen, Art- und Synonymprüfung; kein Pflegekalender | Nein |
| iNaturalist | [Taxonomy-API](https://api.inaturalist.org/v1/docs/) | Deutsche Suchvorschläge und wissenschaftliche Taxa; Rang und Artenzuordnung müssen berücksichtigt werden | Nein |
| Wikidata | [Lizenz CC0](https://www.wikidata.org/wiki/Wikidata:Licensing) | Deutsche Trivialnamen/Aliase mit P225 als taxonomischer Kandidat; Pflanzenart separat validieren | Nein |
| OpenPlantDB | [Schema](https://github.com/cwfrazier1/openplantdb/blob/main/SCHEMA.md), [CC0-Projekt](https://github.com/cwfrazier1/openplantdb) | Strukturierte Aussaat- und Anzuchtwerte für etwa 294 Pflanzen, `last_frost`/USDA-Zonen; methodisch als zusätzliche *Rohdatenquelle* interessant | **Noch nicht**. Klimaanker und Sortenbezug beziehen sich auf US-Rahmen; ohne validierte Übertragung auf die Region Brandenburg keine automatischen Pflanztermine |
| Permapeople | [Datenquelle](https://permapeople.org/) | Ergänzende strukturierte Standort-, Wasser- und Winterhärteinformationen; bisheriger Test 19/21 exakte Arten. CC BY-SA 4.0 mit Quellenpflicht | Nein, bisher kaum strukturierte Pflege-/Schnitt- und Düngetermine |
| DWD-Phänologie | [Datenbeschreibung](https://wetterdienst.readthedocs.io/en/latest/data/provider/dwd/phenology/index.html) | Beobachtete Wachstumsphasen in Deutschland, potenziell für regionale Saisonindikatoren. Keine artspezifische Pflegeanleitung | Nein. Beobachtung und zu empfehlende Arbeit strikt trennen |
| MyMemory | [API-Dokumentation](https://mymemory.translated.net/doc/spec.php), [Limit](https://mymemory.translated.net/doc/usagelimits.php) | Freie maschinelle Übersetzung mit max. 500 Byte pro Abschnitt, anonyme Kontingente derzeit 5.000 Zeichen pro Tag. Keine Fachprüfung | Nein |

## Schutzregel für zukünftige fachliche Automatiken

Eine strukturierte Saisonregel darf erst dann **automatisch eine konkrete Tätigkeit** erzeugen, wenn alle folgenden Voraussetzungen gemeinsam erfüllt sind:

1. Botanisches Taxon nach Art/Sorte eindeutig und aus mindestens einer geeigneten taxonomischen Quelle bestätigt; kein stiller Ersatz durch verwandte Art.
2. Regel stammt **nicht** allein aus einem maschinell übersetzten oder benutzereditierbaren Freitext.
3. Quelle, Originalreferenz, Quellenlizenz, Abrufzeitpunkt, Version sowie fachlicher Prüfstatus sind nachvollziehbar und für die vorgesehene Nutzung zulässig.
4. Monat/Saison/Phänologie, Klimaraum und bei Bedarf Freiland/Kübel sowie lokale Witterungsbedingungen sind eindeutig definiert.
5. Risiko der Handlung ist bewertet: Kontrollen können allgemeiner sein; Schnitt, Düngung, Aussaat, giftige Pflanzen und Pflanzenschutz benötigen spezifische Evidenz.
6. Widersprüche zwischen Quellen oder fehlende relevante Parameter führen zu einem sichtbaren `nicht_freigegeben` statt zu automatischen Aufgaben.
7. Eine erledigte Aufgabe wird nicht bei jedem Neustart erzeugt; Historie und tatsächliche Tätigkeiten bleiben getrennt vom Termingenerator.

**Bereits technisch umgesetzt:** manuelle Aufgaben und Wiederholungen, unterschiedliche Ergebnisse bei Gießkontrollen, Kalender-Wetterkontrollen, vorsichtig gekennzeichnete Pflegeprofile und Quellenbezug bei **selbst bestätigten** Jahreskontrollen. Diese Funktionen dürfen nicht mit einer fachlich freigegebenen automatischen Gärtnerberatung verwechselt werden.

## Vergleich der tatsächlichen deutschen Namenssuche

Ein separater 50-Arten-Benchmark bildet die fünf vereinbarten Gartengruppen mit je 10 Arten ab: [Testliste](../daten/pflanzensuche_50_de.json), [Live-Testskript](../tools/pflanzensuche_50_live.py) und [GitHub-Actions-Workflow](../.github/workflows/garten-pflanzensuche-50.yml).

**Ausgangslauf:** 41/50 erwartete binomiale Namen in den ersten 15 Ergebnissen; 28/50 an Platz 1. Der Befund belegt nur den **exakten Schreibweisenabgleich**; taxonomische Synonyme werden nicht automatisch als Erfolg gezählt. 9 Fälle benötigen eine bessere deutsche Namensabdeckung oder eine validierte Synonymzuordnung. Automatisches Hinzufügen von neun vordefinierten Namen wäre keine skalierbare Lösung.

**Geplante Bewertung jeder weiteren Iteration:** Treffer in Top 15, Rang 1, Fehl-/Mehrdeutigkeit je Gruppe, tatsächlicher Anbieterstatus. Kein automatischer „Erfolg“ bei technisch ausgefallener API oder wissenschaftlich abweichendem Taxon.

## Offene Abnahmepunkte

- OpenPlantbook-Rechte für persistente Speicherung und Übersetzung der Pflegefreitexte ausdrücklich klären. Der Code bleibt bis dahin ein **Entwicklungsstand**.
- Recherche und Erwerb einer tatsächlich lizenzkompatiblen, ausreichend breiten **strukturieren** Fachquelle mit nachgewiesener regionaler Gültigkeit. Die oben aufgeführten Quellen allein erfüllen alle Voraussetzungen derzeit nicht.
- Echte Home-Assistant-Green-Probe mit mindestens 50 eingepflegten Pflanzen, Browser-/iPhone-Test, Kontingent- und API-Ausfällen sowie validierten Benachrichtigungen.
- Erst danach fachlich geprüfte, automatisierte Pflegeregeln freigeben und die dann überholten Platzhalter entfernen.

Das bestehende Home-Assistant-Dashboard **„Zuhause“** sowie seine Integrationen bleiben unverändert.
