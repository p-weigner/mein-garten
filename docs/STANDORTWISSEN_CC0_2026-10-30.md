# Mein Garten – strukturierte Standort-Steckbriefe aus CC0-Daten (30.10.2026)

**Status:** Entwicklung in [Draft-Pull-Request #1](https://github.com/p-weigner/mein-garten/pull/1). Noch **nicht auf Home Assistant Green installiert oder dort getestet**. Das separate Dashboard „Zuhause“ bleibt unverändert.

## Zweck und Datenschutz

Die bisherigen deutschen OpenPlantbook-Pflegefreitexte sind für viele Arten nicht vorhanden, unvollständig oder momentan nicht erreichbar. Damit die Pflanzenverwaltung trotzdem hilfreiche Basisdaten anzeigen kann, gibt es unter **Pflanzen → Pflegewissen** einen eigenständigen **Standort-Steckbrief**, der ausschließlich auf kleinen, lokal mitgelieferten und frei verwendbaren, strukturierten Daten basiert.

Es werden keine privaten Pflanzen-, Personen-, Gartenbereichs-, Notiz- oder Standortinformationen an OpenPlantDB übertragen. Home Assistant Green lädt zur Laufzeit ausschließlich die etwa **645 KB große lokale Datei**. Keine API-Schlüssel, keine Konten, keine Abonnements, keine neuen Netzwerkanfragen.

**Wichtige Einschränkung:** Die Einträge sind allgemeine, teils US-orientierte Quellkategorien, keine regional geprüften Anbau- und Gartenpflegeinformationen für Brandenburg. Diese Daten begründen **keine** automatischen Gießmengen, Frostwarnungen, Schnitt-, Dünge- oder Pflanzenschutzmaßnahmen.

## Quelle, Lizenz und geprüfter Datensatz

- Öffentliche Originaldaten: [OpenPlantDB](https://github.com/cwfrazier1/openplantdb)
- Lizenz der Daten: **Creative Commons Zero 1.0 (CC0)**, keine zusätzliche OpenPlantbook- oder Permapeople-Lizenz für diese Daten
- Fest verwendeter Upstream-Git-Commit: `c6287784527ebb4162e242394ee08f46d338218b`
- Originaldatei: [data/plants.json im festgehaltenen Commit](https://github.com/cwfrazier1/openplantdb/blob/c6287784527ebb4162e242394ee08f46d338218b/data/plants.json)
- SHA-256 der Originaldatei: `aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751`
- Lokaler Offline-Snapshot: `custom_components/mein_garten/data/standort_cc0_v1.json`
- SHA-256 des Snapshots: `fb368b13a28d42bebdedadeff6e76fca09f322d4b2ca04dbeb3637fbf37e7a38`
- Enthaltene Inhalte: botanischer Artname, Sonnenexposition, allgemeine Wasserbedarfs-Kategorie, Frosttoleranz-Kategorie und Wachstumsgruppe
- Ausgeschlossen: fremde Pflegetexte, Bilder, Quellen-Freitexte, Schnittanleitungen, Düngeintervalle, Sortenbeschreibungen, USDA-Härtezonen und frei interpretierte Pflegezeiten

**Die ursprünglichen 34.841 Quelldatensätze werden auf 10.642 botanisch unterscheidbare Arten mit mindestens einem verwendbaren Merkmal reduziert.** Der Katalog ist dynamisch erzeugt; keine Artliste ist im Python-Code fest einprogrammiert.

### Warum Einträge und einzelne Eigenschaften fehlen können

Die Quelle enthält für einige Arten mehrere Sorten-/Anbauvarianten. Für jede botanische Art und **für jedes Merkmal getrennt** werden alle gültigen Quellenwerte verglichen. Wenn sich die Sortenwerte unterscheiden oder ein unbekannter Wert vorliegt, wird **das einzelne Merkmal ausgelassen**. Der Rest des Steckbriefs bleibt lesbar.

Im Ausgangsmaterial wurden so aufgrund von Sorten-/Quellenkonflikten die folgenden Einzelmerkmale für bestimmte Arten gesperrt:

| Merkmal | Arten mit verwendbarem Merkmal | Arten mit widersprüchlichen Werten |
|---|---:|---:|
| Licht | 10.512 | 133 |
| Wasser | 10.497 | 148 |
| Frostkategorie | 10.528 | 117 |
| Wachstumsgruppe | 10.571 | 74 |

Beispiel: Bei **Hydrangea macrophylla** stimmt die Licht-Kategorie in den vorhandenen Quellvarianten überein. Die Wasser-Kategorie ist dagegen nicht eindeutig und wird im Steckbrief **nicht als Gießempfehlung ausgegeben**.

Diese Prüfung beweist weder fachliche Richtigkeit noch eine belastbare Winterhärte. Sie vermeidet lediglich künstliche Widerspruchsauflösungen.

## Messung mit 50 typischen deutschen Gartenpflanzen

Der 50-Pflanzen-Test wird **nicht** für eine feste Sonderzuordnung im Produkt verwendet. Er dient allein der reproduzierbaren Abdeckungsprüfung.

| Gartengruppe | Arten mit mindestens einem Standortmerkmal | Darunter mit Licht + Wasser | Testarten |
|---|---:|---:|---:|
| Blumen, Stauden und Rosen | 10 | 8 | 10 |
| Sträucher, Hecken und Bäume | 9 | 7 | 10 |
| Gemüse und Kräuter | 10 | 6 | 10 |
| Obst und Beeren | 9 | 9 | 10 |
| Kübel- und Topfpflanzen | 8 | 7 | 10 |
| **Gesamt** | **46** | **37** | **50** |

Es fehlen u. a. exakt belegte Profile für *Amelanchier lamarckii*, *Fragaria × ananassa*, *Citrus × limon* und *Pelargonium zonale*. Pflanzen ohne Daten bleiben manuell nutzbar; ihre Merkmale werden nicht von ähnlichen Arten übernommen.

## Bedienung und Darstellung im Garten-Dashboard

1. Eine Pflanze mit eindeutiger botanischer Art hinzufügen.
2. Auf ihrer bestehenden Pflanzenkarte **Pflegewissen** wählen.
3. Der Standort-Steckbrief wird **sofort** aus dem bereits geladenen lokalen Offline-Katalog angezeigt, auch während das separate OpenPlantbook-Profil noch lädt oder nicht verfügbar ist.
4. Zur jeweiligen Art werden nur tatsächlich vorhandene Kategorien auf Deutsch dargestellt; unsichere Kategorien fehlen. Es gibt keine automatisch ausgelösten Termine.
5. Detaillierte, automatisch übersetzte OpenPlantbook-Texte bleiben darunter als **eigenständige, gesondert bezeichnete Quelle** sichtbar. Die Quellen überschreiben einander nicht und werden nicht als gegenseitig bestätigt ausgegeben.

Der Standort-Steckbrief wird bei einer späteren Änderung des botanischen Namens nicht von der bisherigen Art übernommen. Eine unbekannte Art erhält eine sichtbare Datenlücke, keine Gattungs- oder Sortenvermutung.

## Implementierung, Laufzeit und Tests

- Deterministischer Audit: `tools/openplantdb_standort_audit.py`
- Offline-Importer: `tools/openplantdb_standort_export.py`
- CI: `.github/workflows/garten-standort-audit.yml` und `.github/workflows/garten-standort-export.yml`
- Read-only-Backend: `custom_components/mein_garten/standort.py`
- Quelle/Version/Hash und Feldwerte werden bei jedem Integrationsstart im **Home-Assistant-Executor** aus der lokalen Datei validiert. Eine beschädigte oder fehlende **optionale** Datei verhindert nicht das Laden der persönlichen Gartenverwaltung.
- Die WebSocket-API sendet **nur die Artmerkmale der tatsächlich angelegten Pflanzen**, nicht die gesamte Datenbank von über 10.000 Arten.
- Kein neuer Schreibbefehl, kein Standort- oder Pflegesensor, keine eigenständige Automatik. Die Integration ist abwärtskompatibel mit der bisherigen Alpha-Gartendatenstruktur.
- Programmgesteuert geprüft: Genauigkeit der Quellenhashes, unzulässige Kategorien, doppelte Arten, fehlende Quellwerte, HTML-Escaping, OpenPlantbook-Ausfall, Abdeckung und eine große Anzahl an simulierten Pflanzen.

**Weiterhin offen:** Rechte für dauerhafte Speicherung und Übersetzung von OpenPlantbook-Freitexten, echte regional geprüfte Rosen-, Stauden- und Gehölzpflegepläne sowie eine reale HACS-/Home-Assistant-Green-Abnahme (Neustart, lokale Daten, Dashboard auf dem iPhone, Restore/Backup). Eine bestandene GitHub-CI ersetzt diese Abnahme nicht.
