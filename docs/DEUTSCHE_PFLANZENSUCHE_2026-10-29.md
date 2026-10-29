# Deutsche Pflanzensuche – überprüfte API-Strategie

**Datum:** 29. Oktober 2026

**Live-Test iNaturalist + GBIF:** https://github.com/p-weigner/mein-garten/actions/runs/40874005777  
**Live-Test Wikidata:** https://github.com/p-weigner/mein-garten/actions/runs/40874298208

## Ausgangsproblem

Die Nutzerin möchte beim Hinzufügen einer neuen Pflanze direkt im Dashboard nach normalen deutschen Namen suchen. Es darf **keine feste Pflanzenbibliothek im Programm** geben, und niemand soll eine neue Art durch Programmcode ergänzen müssen.

Der frühe Garten-Prototyp lieferte bei „Hortensie“ keine Garten-/Bauernhortensie. Die neuen echten API-Tests zeigen, weshalb ein Anbieter allein für deutsche Namen nicht genügt.

## Echte Suchbefunde

| Suchbegriff | iNaturalist (de) | GBIF `species/suggest` | Wikidata (de, P225) |
|---|---|---|---|
| Hortensie | Gattung *Hydrangea*, verschiedene Arten, kein automatischer Artbeweis | keine geeigneten Ergebnisse | Gattung *Hydrangea*, Familie |
| **Bauernhortensie** | **0 Treffer** | **0 Treffer** | **Hydrangea macrophylla** (deutscher Hauptname „Gartenhortensie“, Alias „Bauernhortensie“) |
| Echter Lavendel | nicht gesondert geprüft; bei „Lavendel“ unter den Vorschlägen | bei „Lavendel“ keine geeigneten Treffer | **Lavandula angustifolia** |
| Tomate | **Solanum lycopersicum** unter den Vorschlägen | unter anderem Fliegen und Viren; für deutsche Freitextsuche ungeeignet | **Solanum lycopersicum**, daneben Tomatenminiermotte |
| Apfelbaum | unter ersten Beispielen *Malus angustifolia*; **nicht** automatisch als Kulturapfel behandeln | keine geeigneten Ergebnisse | nicht geprüft |
| Rote Johannisbeere | **Ribes rubrum** | keine geeigneten Ergebnisse | Testaufruf fehlgeschlagen; keine inhaltliche Aussage möglich |
| Gartenhortensie | nicht gesondert geprüft | nicht gesondert geprüft | in diesem Suchlauf kein geeigneter P225-Treffer |

## Folgerung für die Benutzeroberfläche

1. **Primäre deutsche Namenssuche:** iNaturalist mit `locale=de`. Botanische Namen und deutsche Vorschläge dynamisch auflisten.
2. **Ergänzung für umgangssprachliche Namen und Aliase:** Wikidata-Suche, danach den taxonomischen Namen **P225** aus der jeweiligen Entität holen. So wird „Bauernhortensie“ ohne programmierte Einzelliste erkannt.
3. **Botanische Validierung:** Den vorgeschlagenen wissenschaftlichen Namen über GBIF bzw. iNaturalist abgleichen. Ein einfacher deutscher Suchtreffer genügt nicht für die Freigabe artspezifischer Pflegehinweise.
4. **Mehrdeutigkeit:** Gattung, Familie, Krankheiten, Tiere und verschiedene Arten niemals automatisch als gewünschte Pflanzenart übernehmen. Der Nutzerin eine eindeutige Artenauswahl zeigen.
5. **Kein stiller Fallback auf eine ähnliche Art.** Bei unklarer Art dürfen persönliche Pflanzen angelegt werden, aber artspezifische Pflegehinweise erst nach bestätigter Zuordnung abrufen.
6. **Schonend auf API-Limits reagieren:** Eingaben entprellen, Cache nutzen, Limits und Fehler verständlich anzeigen. Wikidata antwortete bei einem der sechs Suchbegriffe nicht erfolgreich; Fallback auf iNaturalist ist nötig.
7. **Keine fest codierten Art-Aliase:** Neue Arten können durch neue öffentliche Datensätze verfügbar werden.

## Nutzung und Rechte

Wikidata stellt die **strukturierten Daten unter CC0** bereit. Quelle: https://www.wikidata.org/wiki/Wikidata:Licensing

Für Artennamen und taxonomische Zuordnung ist das deutlich unkomplizierter als eine vollständige fremde Pflegebibliothek. Die API ist jedoch eine von Freiwilligen gepflegte Datenquelle, keine automatische Garantie fachlicher Richtigkeit.

GBIF und iNaturalist sind für botanische Suchdaten geeignet; Namensvorschläge können irreführende Ränge enthalten und müssen vor der Verwendung als Pflegegrundlage geprüft werden.

## Bereits implementiert

- `tools/deutsche_namenssuche_live.py`: Erkundung deutscher Namen über iNaturalist und GBIF.
- `tools/wikidata_namen.py`: generischer deutscher Aliassuch-Adapter mit P225-Verifikation.
- `tools/wikidata_namen_live.py`: tatsächlicher API-Livetest.
- `tests/test_wikidata_namen.py`: 7 zusätzliche Tests gegen unpassende Entitäten, ungültige IDs und falsche Artzuordnung.
- `custom_components/mein_garten/model.py`: dynamische Anlage beliebiger Pflanzenarten in lokaler Datenbank.

**Noch nicht verbunden:** Live-Suche im neuen Home-Assistant-Frontend. Das ist der nächste Integrationsschritt. Kein Installationspaket freigegeben.
