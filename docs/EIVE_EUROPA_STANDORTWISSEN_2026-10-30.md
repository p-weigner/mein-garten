# Mein Garten – europäische Standortindikatoren EIVE 1.0 (30.10.2026)

**Implementierter, technisch geprüfter Entwicklungsstand in [Draft-PR #1](https://github.com/p-weigner/mein-garten/pull/1). Nicht auf Home Assistant Green installiert oder am iPhone abgenommen. Keine Produktivfreigabe, kein Merge nach `main`.** Das bestehende Dashboard „Zuhause“ und alle eigenen Gartenaufgaben bleiben unberührt.

## Warum diese Quelle?

Die bisher vorhandenen OpenPlantDB-CC0-Standortkategorien sind breit, aber teilweise US-orientiert. **EIVE 1.0** ist eine unabhängige wissenschaftliche Ergänzung: harmonisierte europäische ökologische Zeigerwerte aus 31 Ausgangssystemen. Damit können vor allem viele mitteleuropäische und heimische Pflanzen zusätzliche Standortinformationen bekommen. Die Werte beschreiben den ökologischen Standortbezug einer Art – sie ersetzen keine gärtnerische Pflegeanleitung.

| EIVE-Kürzel | Bedeutung | Was daraus **nicht** abgeleitet wird |
|---|---|---|
| L | Licht | keine Lux-Vorgabe, keine Garantie für jede Sorte |
| M | Bodenfeuchtigkeit | kein Gießintervall oder Wasserbedarf in Litern |
| N | Nährstoffverfügbarkeit | keine Dünge- oder Dosierungsanleitung |
| R | Bodenreaktion | kein tatsächlich gemessener pH-Wert im Garten |
| T | Temperatur | keine genaue lokale Frosttoleranz oder Winterhärte |

EIVE-Werte liegen auf einer **relativen europäischen Skala von 0 bis 10**. In der Oberfläche wird zu jedem Wert die Zahl der beitragenden Quellsysteme angezeigt; **nur ein Quellsystem** erhält einen auffälligen Hinweis auf die geringere Datengrundlage. Selbst viele Quellsysteme bedeuten nicht, dass die konkreten Standortbedingungen in Brandenburg oder die Pflege einer Sorte geprüft sind.

## Fachquelle und reproduzierbarer Lizenznachweis

- **Dengler, Jansen et al. (2023), Ecological Indicator Values for Europe (EIVE) 1.0.**
- Veröffentlichter Datensatz mit vollständigen Urhebern: https://doi.org/10.5281/zenodo.7534792
- Peer-reviewter Fachartikel: https://doi.org/10.3897/VCS.98324
- Originaldatei: `EIVE_Paper_1.0_SM_08.xlsx` (2.900.881 Bytes).
- Geprüfte Originaldatei: MD5 `0f0ce19cd2a781eeed027d8b0acadbcb`.
- **CC BY 4.0** direkt durch den Datensatz bestätigt: https://creativecommons.org/licenses/by/4.0/
- Werte sind für den Offline-Katalog nach exakten Arten gefiltert und auf zwei Nachkommastellen gerundet; die Benutzeroberfläche zeigt eine Nachkommastelle. DOI und Lizenzlink erscheinen unmittelbar beim Datenblock.

## Gemessene Abdeckung

**[Erfolgreicher EIVE-Quellen- und Artabdeckungslauf](https://github.com/p-weigner/mein-garten/actions/runs/41084682081).**

| Messung | Ergebnis |
|---|---:|
| Botanisch eindeutige Arten mit verwertbaren Indikatoren vor Taxonquellenprüfung | 10.686 |
| Arten mit nicht geeigneter Taxonherkunft (`additionalAggregates`) | 3 |
| Eindeutig zugelassene Arten im fertigen Offline-Katalog | **10.683** |
| Pflanzen aus unserem 50er-Benchmark, exakt enthalten | **36 / 50** |
| Dieselben Arten mit allen fünf Indikatoren | **36 / 50** |
| Daraus automatisch erzeugte Pflegeaufgaben | **0** |

Reale Beispiele: **Hainbuche, Haselnuss, Felsenbirne, Echter Lavendel, Himbeere, Thymian und Liguster** besitzen passende ökologische Indikatoren. **Bauernhortensie, Rispenhortensie, Wald-Hortensie, Tomate** und weitere in Deutschland kultivierte Pflanzen fehlen in EIVE unter den exakten erwarteten wissenschaftlichen Namen. Der bestehende breitere OpenPlantDB-Standortkatalog bleibt parallel erhalten. Fehlende EIVE-Daten werden **nicht** durch eine Gattung oder ähnliche Art ersetzt.

Diese Zahlen sind eine endliche, geprüfte Stichprobe – keine Garantie für alle in Deutschland üblichen Pflanzen.

## Technische Umsetzung

- [`tools/eive_europa_quellenprobe.py`](../tools/eive_europa_quellenprobe.py): Prüft Zenodo-Datensatz-ID, Lizenz, Originaldatei und XLSX-Schema.
- [`tools/eive_europa_artenabdeckung.py`](../tools/eive_europa_artenabdeckung.py): Liest alle `mainTable`-Zeilen und prüft botanische Zweinamen, Artstatus, 0–10-Werte sowie Beleganzahl je Feld. Keine stillen Synonymerkennungen.
- [`tools/eive_europa_export.py`](../tools/eive_europa_export.py): Erzeugt deterministisch einen kleinen CC-BY-Offline-Katalog aus dem geprüften Original.
- [`data/eive_europa_ccby_v1.json.gz.b64`](../custom_components/mein_garten/data/eive_europa_ccby_v1.json.gz.b64): ca. **255 KB** Base64-kodierter, gzip-komprimierter Katalog für **10.683 Arten**, ohne Download beim späteren Home-Assistant-Start.
- [`custom_components/mein_garten/eive.py`](../custom_components/mein_garten/eive.py): Lädt die lokale Datei im Executor, prüft **drei feste SHA-256-Fingerabdrücke** und das komplette Datenformat und liefert nur die exakten Werte der eigenen Pflanzen an den bereits authentifizierten WebSocket.
- [`frontend/mein-garten-card.js`](../frontend/mein-garten-card.js): Eigener Bereich **„Europäische Standortindikatoren“** im vorhandenen Pflegewissen-Dialog. Fünf Zahlen, sichtbare Beleganzahl und Quellenangabe – ohne Änderung der freigegebenen dunkelgrünen Gestaltung und ohne neue Bedienseite.
- [`tests/test_garten_eive.py`](../tests/test_garten_eive.py), [`tests/test_eive_europa_export.py`](../tests/test_eive_europa_export.py), [`tests/test_eive_europa_artenabdeckung.py`](../tests/test_eive_europa_artenabdeckung.py) und Frontend-Tests: Quellschutz, botanische Eindeutigkeit, Originalhash, Manipulationsabwehr, HTML-Schutz, Artabdeckung und Fehlertoleranz.

**Wichtig zur Fehlerbehandlung:** Der EIVE-Block ist optional. Wenn die Datei fehlt, die Prüfsumme nicht stimmt oder das Schema beschädigt ist, bleibt die Gartenverwaltung mit den bisherigen Standortkategorien, persönlichen Daten und Pflegeaufgaben erreichbar. Die optionalen Werte werden stattdessen weggelassen.

## Fachliche und rechtliche Grenzen

Die Veröffentlichung unter CC BY 4.0 gestattet bei korrekter Namensnennung die abgeleitete Darstellung. **Sie bestätigt aber nicht die Eignung als individuelle Pflegemaßnahme.** Aus EIVE allein werden daher keine Schnitt-, Aussaat-, Pflanz-, Bewässerungs-, Dünge-, Pestizid- oder Frosttermine erzeugt. EIVE ergänzt weder individuelle Bodentests noch die lokale Witterungsprognose und überträgt keine Aussagen zwischen botanisch unterschiedlichen Arten oder Sorten.

**Abnahme noch offen:** Tatsächliche Laufzeit auf Home Assistant Green, Anzeige im Safari-/iPhone-Dashboard, Neustart- und Fehlerfälle sowie redaktionelle Kontrolle der wissenschaftlichen Beschriftungen. Vor dieser Abnahme kein Merge nach `main` und keine produktive Installation.
