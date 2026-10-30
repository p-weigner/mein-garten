# Mein Garten – Qualitätsaudit der CC0-Anbauhinweise (30.10.2026)

**Technische Forschungsstufe, keine Produktivfreigabe.** Keine Änderung an den Pflege- oder Terminregeln, kein Import englischer Pflegefreitexte in das Dashboard. Home Assistant Green und das getrennte Dashboard „Zuhause“ bleiben unberührt.

## Untersuchte Datenquelle

- OpenPlantDB, CC0 1.0, [Repository](https://github.com/cwfrazier1/openplantdb).
- Fest gepinnter Upstream-Commit: `c6287784527ebb4162e242394ee08f46d338218b`.
- Prüfhash der originalen Datei: `aa2a9dc02203c6849e24e2f8d47a5339281638d504b1adfc211e771585a8f751`.
- Nur in isolierten GitHub-Actions-Runs geladen: **niemals** auf Home Assistant Green.
- Untersuchte Felder: freie `directions`-Anbauhinweise und `planting.note`-Pflanzhinweise.
- Der Audit erstellt nur aggregierte Zählungen, Zustände und SHA-256-Fingerabdrücke; er exportiert **keine vollständigen fremden Pflegeanleitungen**.

## Echte Messung

[GitHub-Actions-Lauf 41074491039](https://github.com/p-weigner/mein-garten/actions/runs/41074491039) – erfolgreich, acht neue Offline-Unit-Tests bestanden.

| Messgröße | Ergebnis |
|---|---:|
| Rohdatensätze | 34.841 |
| Datensätze ohne exakten botanischen Zweinamen | 22.726 |
| Unterscheidbare exakte botanische Arten | 10.645 |
| Arten mit einheitlichem `directions`-Text aller Varianten | 9.936 |
| Arten mit widersprüchlichen `directions`-Texten | 650 |
| Arten mit Lücken / ungeeigneten `directions`-Feldern | 59 |
| Arten mit einheitlichem `planting.note`-Text | 9.919 |
| Arten mit widersprüchlichen Pflanzhinweisen | 656 |
| Arten mit Lücken / ungeeigneten Pflanzhinweisen | 70 |
| Arten mit konkreterer, aber **ungeprüfter** Quellenangabe | 10.256 |
| Arten mit bloß allgemeinen Quellenangaben | 389 |
| Testliste: einheitlicher Anbautext | 19 von 50 |
| Testliste: einheitlicher Pflanzhinweis | 19 von 50 |
| Als automatische Pflegeregel fachlich freigegeben | **0** |

**Wichtig zur Interpretation:** „Einheitlich“ bedeutet ausschließlich, dass alle vorliegenden Datenbank-Varianten für *denselben botanischen Zweinamen* einen nach Leerräumen normalisierten identischen Text liefern. Es beweist weder Sortengültigkeit noch fachliche Richtigkeit, Quellenlizenz einzelner möglicher Vorlagen oder Eignung für das Klima in Brandenburg. Eine genauere Quellenangabe kann auch eine unzureichende oder abgeleitete Angabe sein.

### Beispiele unserer 50er-Stichprobe

- **Bauernhortensie (`Hydrangea macrophylla`)**: vier Varianten, widersprüchliche Anbau- und Pflanzhinweise.
- **Echter Lavendel (`Lavandula angustifolia`)**: vier Varianten mit widersprüchlichen Texten.
- **Tomate (`Solanum lycopersicum`)**: 60 Varianten, voneinander abweichende Texte. Kein willkürlich ausgewählter Standardtext.
- **Rispenhortensie (`Hydrangea paniculata`)**: eine Variante mit einheitlichen Texten; trotzdem keine automatische Schnitt- oder Düngeempfehlung.
- **Felsenbirne (`Amelanchier lamarckii`)**: kein exakter Quelldatensatz; keine automatische Übertragung von verwandten Arten.

## Implementierte Schutzmaßnahmen

1. Identische Arten zusammenfassen, niemals allein anhand deutscher Namen oder Gattungen verknüpfen.
2. Bei widersprüchlichen Sorten-Freitexten **keine** automatische Aussage ableiten.
3. Fehlende, leere, zu kurze, zu lange oder HTML-enthaltende Texte separat als Lücke markieren.
4. Allgemeine Quellenbezeichnungen von konkreteren, **noch nicht qualitätsgeprüften** Referenzen unterscheiden.
5. Englische Texte und US-Maße/-Zonen nicht als fertige deutsche Regionalpflege ausgeben.
6. Kein neues Monats-/Jahres-Schema, keine Gieß-, Dünge-, Schnitt- oder Pflanzaufgabe durch dieses Audit.
7. Rohdaten, private Nutzerinformationen, Pflanzennotizen oder HA-Zugangsdaten nicht in den Auditbericht übernehmen.

## Freigabekriterien für das nächste Produktinkrement

- Für artspezifische **deutsche Hinweise**: geeignete Quellenlizenz für lokale Speicherung und Übersetzung prüfen; botanischen Art-/Sortenbezug und deutsches Klima berücksichtigen; Unsicherheit sowie Originalquelle sichtbar machen.
- Für **konkrete, automatisch terminierte Pflegeaufgaben**: strukturierte fachlich bestätigte Regel mit gültigem Klimaraum, Jahreszeit/Phänologie, Ausnahmefällen und nachweisbarer Quellen-/Versionshistorie verlangen. Einen frei formulierten Text nicht durch Stichwortsuche in eine verbindliche Regel umwandeln.
- Für verbreitete Arten ohne geprüfte Quellen: vorhandene manuellen Aufgaben, Gießentscheidungen und Standort-Grundkategorien weiter anbieten; fehlendes Wissen ehrlich anzeigen.

### Dateien und Reproduzierbarkeit

- Analyse: [`tools/openplantdb_pflegefreitext_audit.py`](../tools/openplantdb_pflegefreitext_audit.py)
- Acht Offline-Tests: [`tests/test_openplantdb_pflegefreitext_audit.py`](../tests/test_openplantdb_pflegefreitext_audit.py)
- Separater Read-only-Workflow: [`.github/workflows/garten-pflegefreitext-audit.yml`](../.github/workflows/garten-pflegefreitext-audit.yml)
- Bericht als Workflow-Artefakt: `Pflanzenpflege_Quellenqualitaet_Audit`
- Die bestehende 50er-Suchtestliste wurde **nicht** als fest codierte Produktiv-Ausnahmeliste verwendet.
