# Mein Garten – CC0-Saisonfenster (Entwicklungsentwurf vom 30. Oktober 2026)

**Nur GitHub-Draft, nicht auf Home Assistant Green installiert.**

## Datenbasis

Quelle: [OpenPlantDB](https://github.com/cwfrazier1/openplantdb), Lizenz [CC0 1.0](https://github.com/cwfrazier1/openplantdb/blob/main/LICENSE).

Quellcommit: 99393ea2dbe8da6973434974f92863beff3bbb32 (5. Juli 2026). In dieser festen Version enthielt die Quelldatei data/plants.json genau 294 Datensätze. Der heutige Hauptbranch ist deutlich größer und wird **nicht** automatisch eingebunden.

Es wurden ausschließlich strukturierte Rohfelder für 152 botanisch eindeutig zuordenbare Arten übernommen: wissenschaftlicher Name, Quellenkennung, Kategorie, Aussaat-/Pflanzmethode, Frostanker und Wochenintervall. Nicht übernommen wurden Fremdtexte, Fotos, automatische Pflegeanweisungen, unklare Art-/Sortenzuordnungen und duplizierte Binomina.

Offline-Datei: custom_components/mein_garten/data/saison_openplantdb_v0_1.json (kein API-Schlüssel, kein Abo und kein Netzwerkaufruf zur Laufzeit).

## Benutzung

1. Im Gartenkalender die **Frost-Referenzdaten** für das gewünschte Jahr selbst festlegen: letzter erwarteter Frühjahrsfrost und/oder erster erwarteter Herbstfrost.
2. Bei botanisch exakt passenden Pflanzen erscheinen unverbindliche Saisonfenster mit Quelle und Hinweis auf die fehlende regionale Prüfung.
3. Über **Kontrolle planen** einen Termin innerhalb des Fensters selbst auswählen und ausdrücklich bestätigen.
4. Erst dann wird eine einzelne Kontrollaufgabe im Gartenkalender angelegt. Ihre Metadaten enthalten Quelle, CC0-Lizenz, Quellcommit, Datumsspanne, Jahr und Freigabeart.
5. Ein zweiter Termin derselben Saisonvorlage für dieselbe Pflanze und dasselbe Jahr ist nicht möglich. Löschen ermöglicht eine spätere Neuanlage; erledigte Termine bleiben im Kalender.

**Beispiel, keine regionale Empfehlung:** Für Solanum lycopersicum enthält die Quelle ein Vorzuchtfenster 6–8 Wochen vor dem erwarteten letzten Frühjahrsfrost. Bei einem nur beispielhaft gewählten 15. Mai 2027 ergibt sich der 20. März bis 3. April 2027. Das ersetzt weder regionale Erfahrung noch die Prüfung von Saatgut, Sorte und Wetter.

## Schutzmaßnahmen

- Kein automatisch erfundenes Frost-Referenzdatum aus US-Klimazonen.
- Kein Termin bei fehlendem Frostanker oder unsicherem botanischem Namen.
- Nur vom Backend aus dem lokalen Katalog erzeugte Aufgabennamen und Quellen.
- Manipulierte Termindaten außerhalb des vorgesehenen Fensters werden zurückgewiesen.
- Keine autonomen Schnitt-, Dünge-, Pflanzenschutz- oder Aussaatmaßnahmen.
- Das angezeigte Zeitfenster ist eine **US-Planungshilfe**, keine fachlich für Brandenburg überprüfte Empfehlung.
- Das nächste Kalenderjahr erfordert bewusst neu gesetzte Frost-Referenzdaten.
- Gartendaten und Saison-Referenzdaten liegen getrennt lokal in Home Assistant.

## Speicherorte und offene Abnahme

Gartendaten: .storage/mein_garten_v1.data

Saisonreferenzdaten: .storage/mein_garten_saison_v1.data

Katalog: custom_components/mein_garten/data/saison_openplantdb_v0_1.json

Vor Installationsfreigabe: echte Tests auf Home Assistant Green (iPhone-Dashboard, Datumsfelder, HA-Store, Neustart, Dashboard-Updates, lokale Zeitzone, Datumsänderungen, Backup/Rollback). Fachlich geprüfte artspezifische Schnitt- und Düngepläne sind weiterhin **nicht** implementiert. OpenPlantbook-Nutzungsrechte für eigene Pflegefreitext-Caches sind separat zu klären.

**Das eigenständige Dashboard Zuhause wird nicht verändert.**
