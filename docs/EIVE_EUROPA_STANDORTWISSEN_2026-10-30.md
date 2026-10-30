# Mein Garten – europäisches Standortwissen (EIVE 1.0), 30.10.2026

**Stand: reproduzierbare Forschungs- und Quellenprüfung im Draft-Branch. Keine Produktivfreigabe und kein Merge.** Die vorhandenen Gartenansichten, Pflegeaufgaben, Notizen, Benachrichtigungen und das eigenständige Dashboard „Zuhause“ werden nicht verändert.

## Warum diese Quelle?

Die bisherigen OpenPlantDB-CC0-Standortkategorien sind großflächig vorhanden, jedoch zum Teil auf die USA ausgerichtet. Für mitteleuropäische und heimische Pflanzen ist die **wissenschaftliche Sammlung EIVE 1.0** ein zusätzlicher Kandidat. Sie harmonisiert ökologische Zeigerwerte aus **31 europäischen Indikatorsystemen**. Es geht um ökologische Nischenwerte, **nicht** um erprobte Gartenpflegepläne.

**Fünf wissenschaftliche Dimensionen** im geprüften Supplement Nr. 8:

| Kürzel in der Quelldatei | Inhalt | Nicht zulässige Vereinfachung |
|---|---|---|
| M | Bodenfeuchte / Moisture | kein Gießintervall |
| N | Nährstoffverfügbarkeit / Nitrogen | keine Düngerart oder -menge |
| R | Bodenreaktion / Reaction | kein gemessener pH-Wert der eigenen Erde |
| L | Licht / Light | keine garantierte Standortverträglichkeit jeder Sorte |
| T | Temperatur / Temperature | keine exakte lokale Frosthärte |

Jeder Punkt kann neben einem ökologischen Zeigerwert eine Nischenbreite und die Anzahl beitragender Ausgangssysteme enthalten. Die Zahlen beziehen sich auf ein **ökologisches Indikatorensystem**, nicht unmittelbar auf Lux, °C, Liter Wasser oder Boden-pH.

## Verifizierte Primärquelle

- Datensatz: **Dengler, Jansen et al. (2023), EIVE 1.0, Supplement 8**.
- Forschungsdaten und vollständige Autorenangabe: https://doi.org/10.5281/zenodo.7534792
- Fachartikel: https://doi.org/10.3897/VCS.98324
- Datei: `EIVE_Paper_1.0_SM_08.xlsx`, **2.900.881 Bytes**.
- Gemessene Originalprüfsumme: `MD5 0f0ce19cd2a781eeed027d8b0acadbcb`.
- Lizenz **CC BY 4.0** direkt aus der Zenodo-Datensatz-Metadatenprüfung bestätigt. Bei einer späteren Anzeige wären Autoren, Quelle, DOI, Lizenz und Bearbeitung kenntlich zu machen.
- Quelle wurde im isolierten GitHub-Actions-Runner validiert. Auf Home Assistant Green erfolgen **keine** Zenodo-Downloads und keine zusätzlichen kostenpflichtigen Dienste.

**Erfolgreiche technische Quellenprüfung:** [GitHub-Actions-Lauf 41083144693](https://github.com/p-weigner/mein-garten/actions/runs/41083144693). Er prüft Datensatz-ID, Lizenz, gepinnte Originalprüfsumme, XLSX-Dateiformat, Tabellenstruktur und ausschließlich kleine Schemaauszüge. Nicht alle Gartenpflanzen sind damit automatisch abgedeckt.

## Erweiterte Qualitätsprüfung

- [Code für die exakte Arten- und Indikatorprüfung](../tools/eive_europa_artenabdeckung.py).
- [Tests der Taxonomie, Nullwerte, Widersprüche und Zahlenbereiche](../tests/test_eive_europa_artenabdeckung.py).
- Prüfung über **alle** Zeilen des Quellblatts `mainTable`; Tabellenüberschriften werden explizit validiert.
- Nur Datenzeilen mit `TaxonRank = Species` und vollständigem botanischen Zweinamen werden technisch erwogen. Keine Gattungen, Unterarten, Sorten oder unbestätigte Ersatz-Synonyme.
- Doppelte Artnamen werden als mehrdeutig markiert, nicht stillschweigend zusammengeführt.
- Nur endliche Werte 0–10 mit tatsächlich vorhandener Zahl von beitragenden Quellsystemen werden technisch eingelesen; unvollständige Felder bleiben leer. Bei kleiner Beleganzahl ist zusätzliche Unsicherheitskennzeichnung vorzusehen.
- Ein Test mit **50 typischen deutschen Gartennamen aus fünf Pflanzengruppen** prüft die tatsächliche exakte Zuordnung, ohne diese Namen im Produktivsuchcode fest zu hinterlegen.
- Der Auditbericht enthält nur Aggregationen, Artabdeckung und Anzahl der Quellsysteme, **keine** Rohdatenbank und keine privaten Pflanzennotizen.

## Voraussetzungen für eine spätere Anzeige im Dashboard

1. Lizenznachweis, Autorenangabe, unveränderte Prüfsumme, exakte Artidentität und die reale 50er-Abdeckung im CI-Audit bestätigen.
2. Verifizierte Spaltenbelegung und Interpretation der fünf ökologischen Dimensionen kontrollieren. Nur belastbare Zahlen in einen kleinen, komprimierten Offline-Katalog übernehmen.
3. Eigenständige und eindeutig deklarierte Anzeige **„Europäische Standortindikatoren (EIVE)“**; nicht mit den US-orientierten OpenPlantDB-Kategorien oder OpenPlantbook-Pflegefreitexten zu einem scheinbar sicheren Pflegerezept vermischen.
4. Bei nicht eindeutigem botanischem Namen, fehlendem EIVE-Eintrag oder unklaren Werten: sichtbare Lücke statt geschätzter Empfehlung.
5. **Null automatisch angelegte Aufgaben** durch EIVE. Die vorhandenen persönlichen Gießkontrollen und manuellen Jahresregeln bleiben benutzerbestimmt.
6. Nach isolierten Tests die echte Darstellung auf Home Assistant Green und dem iPhone abnehmen, bevor das Projekt als produktiv gekennzeichnet wird.

Diese zusätzliche ökologische Quelle ersetzt keine geprüfte, in Deutschland gültige Fachberatung zu Schnitt, Aussaat, Düngung, Pflanzenschutz oder Frostschutz.
