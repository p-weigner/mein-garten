# OpenPlantbook – tatsächlicher Pflegefeldtest am 29. Oktober 2026

**Quelle:** vom Nutzer ausgeführtes Skript `Mein Garten: OpenPlantbook-Prüfung` auf Home Assistant Green. Bericht wurde im Chat bereitgestellt. Kein API-Schlüssel nach GitHub übertragen.

## Tatsächliche Ergebnisse

13 botanische Arten aus Rosen/Stauden, Obst/Beeren, Gemüse/Kräutern, Gehölzen und Zimmer-/Kübelpflanzen getestet.

- **10/13** mit exakt übereinstimmender `pid`, gültiger Detailantwort und **allen fünf** Feldern `watering`, `sunlight`, `soil`, `pruning`, `fertilization` als nichtleere Strings.
- **2/13** mit genau einem Suchtreffer, dessen `pid` nicht exakt zur gesuchten Art passte: `Lavandula angustifolia`, `Solanum lycopersicum`. Der erste Test gibt die zurückgelieferten PIDs nicht aus. **Noch keine bestätigte Fehlart; keine automatische Übernahme.**
- **1/13** ohne Suchtreffer: `Rosa canina`.
- Bei **keinem der zehn bestätigten Treffer** war ein Pflegefeld vollständig leer.

| Art | Wasser | Licht | Boden | Schnitt | Düngung | Ergebnis |
|---|---:|---:|---:|---:|---:|---|
| Hydrangea macrophylla | 245 | 196 | 266 | 446 | 271 | exakte Art + 5 Texte |
| Hydrangea paniculata | 87 | 52 | 37 | 45 | 68 | exakte Art + 5 Texte |
| Lavandula angustifolia | 0 | 0 | 0 | 0 | 0 | 1 Suchtreffer, PID nicht exakt |
| Rosa canina | 0 | 0 | 0 | 0 | 0 | kein Suchtreffer |
| Buxus sempervirens | 61 | 38 | 37 | 27 | 77 | exakte Art + 5 Texte |
| Malus domestica | 46 | 49 | 51 | 54 | 59 | exakte Art + 5 Texte |
| Ribes rubrum | 41 | 36 | 37 | 41 | 111 | exakte Art + 5 Texte |
| Fragaria x ananassa | 37 | 45 | 37 | 55 | 71 | exakte Art + 5 Texte |
| Solanum lycopersicum | 0 | 0 | 0 | 0 | 0 | 1 Suchtreffer, PID nicht exakt |
| Cucumis sativus | 37 | 15 | 47 | 39 | 66 | exakte Art + 5 Texte |
| Ocimum basilicum | 23 | 78 | 37 | 45 | 51 | exakte Art + 5 Texte |
| Olea europaea | 16 | 26 | 37 | 22 | 32 | exakte Art + 5 Texte |
| Monstera deliciosa | 69 | 99 | 42 | 39 | 83 | exakte Art + 5 Texte |

Zahlen = Zeichenlängen, keine Qualitäts-, Wahrheits- oder Übersetzungsprüfung.

### Verteilung der Textlängen (nur 10 bestätigte Arten)

| Feld | Median Zeichen | Minimum | Maximum |
|---|---:|---:|---:|
| Gießen | 43,5 | 16 | 245 |
| Licht | 47 | 15 | 196 |
| Boden | 37 | 37 | 266 |
| Schnitt | 43 | 22 | 446 |
| Düngung | 69,5 | 32 | 271 |

**Gesamt:** 50/50 technisch gefüllte Pflegefelder über zehn Profile. In mehreren Fällen sind die Angaben sehr kurz. Eine konkrete saisonale Pflegeplanung ist daraus allein nicht verantwortbar. Die lange Bauernhortensien-Anleitung ist kein Nachweis gleicher Qualität bei allen Arten.

## Gegenüberstellung mit Permapeople

- Permapeople: **19/21** exakte Treffer; bei allen 19 strukturierte Standort-/Wasser-/Boden-/Winterhärtefelder; keine eigenständigen strukturierten Schnitt-/Düngefelder in dieser Stichprobe.
- OpenPlantbook: **10/13** exakte Treffer; fünf gefüllte Pflegefelder einschließlich Schnitt und Düngung bei allen zehn.

**Achtung:** Die Stichprobengrößen und enthaltenen Arten sind verschieden; die Trefferquoten sind **kein direkter Benchmark** für die weltweite Datenbankabdeckung.

## Fachliches Risiko

Das OpenPlantbook-Projekt dokumentiert bearbeitbare Nutzer-Pflegefelder (Release vom Mai 2026). Texte sind daher nicht notwendigerweise fachlich kuratiert. Die UI soll die Daten mit Quelle und Kennzeichnung `nicht_fachlich_geprüft` darstellen. Die vordefinierten Textfelder dürfen **nicht ohne gesonderte Regelprüfung** automatische schädliche Schnitt-/Düngeaufgaben erzeugen.

## Freigegebene technische Entscheidung

1. **GBIF und iNaturalist:** Primäre botanische Namensidentifikation (mit geprüftem Hybridzeichen-Abgleich).
2. **OpenPlantbook:** Primäre Quelle für verfügbare Pflegefreitexte, sofern botanische Art/gegebenenfalls Sorte eindeutig und Datenrechte geklärt.
3. **Permapeople:** Ergänzende Quelle für strukturierte Standortinformationen; CC BY-SA 4.0 beachten.
4. **Pflegewissen-Fusion:** Quellen einzeln dokumentieren, nur vorhandene deutsche Übersetzungen anzeigen, eigene Hinweise schützen, kein automatisches Umwandeln beliebiger Freitexte in Aufgaben.
5. **Bei fehlender Pflegequelle:** Neue Pflanzen müssen trotzdem ohne Programmänderung angelegt werden können, ohne erfundene Inhalte.
6. **Nächste Validierungen:** PID-Kandidaten von Lavendel und Tomate, fachliche Stichprobenprüfung echter Pflegefreitexte, zulässige lokale Textspeicherung sowie Live-Test der automatischen deutschen Übersetzung.
7. Erst nach diesen Validierungen wird eine gärtnerisch abgesicherte Pflegeaufgaben-Engine freigegeben.

**Integrationsstatus:** Nur Datenquellenprototyp im öffentlichen GitHub-Repo, noch keine neue Home-Assistant-Integration. Das bestehende „Zuhause“-Dashboard bleibt unberührt.
