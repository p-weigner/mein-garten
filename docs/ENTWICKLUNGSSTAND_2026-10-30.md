# Mein Garten – Entwicklungsstand nach der Alpha (30.10.2026)

**Status:** Entwicklung auf Branch `codex/garten-pflegewissen-und-suche-20261030`, [Draft-Pull-Request #1](https://github.com/p-weigner/mein-garten/pull/1). **Nicht auf Home Assistant Green installiert oder dort live getestet. Nicht mergen und nicht als produktives HACS-Release bereitstellen.** Das Dashboard „Zuhause“ wird nicht verändert.

## Neu implementiert (Quellcode und isolierte Tests)

| Bereich | Verhalten |
|---|---|
| Pflanzensuche | iNaturalist + Wikidata + wissenschaftliche GBIF-Suche + GBIF-Trivialnamensindex; Trivialnamen ausschließlich für akzeptierte botanische Pflanzenarten aus dem GBIF-Backbone, Mehrdeutigkeiten im Dashboard sichtbar; deutsche positive Treffer in begrenztem lokalen Namenscache für 365 Tage und als Präfix-Fallback bei API-Ausfall |
| Pflegeprofile | Per Pflanzenkarte abrufbar; bestehende Home-Assistant-OpenPlantbook-Integration, `search` und `get` mit `include: care`; strenger botanischer Artabgleich; fünf Pflegefelder |
| Deutsch | Automatische Übersetzung der externen Pflegefelder über MyMemory, maximal 5.000 Zeichen pro Tag, lokal begrenzter privater Cache; ausstehende oder nicht vorhandene Angaben werden als solche angezeigt |
| Wiederholungen | Benutzerdefinierte Regeln alle 1–365 Tage oder jährlich; erster Termin ausdrücklich vom Benutzer angegeben; nicht doppelt bei Neustart; Pause und Löschung |
| Pflegewissen → Termin | Aus einem deutschen Pflegefeld lässt sich eine **Jahreskontrolle** erstellen. Der Termin wird erst nach eigener Datumseingabe angelegt, und der Bezug auf die nicht fachlich geprüfte Quelle bleibt sichtbar |
| Wetter | Optionaler Frost-Check über `weather.get_forecasts` (stündlich, bei Bedarf täglich); 48-Stunden-Fenster, Warnschwelle standardmäßig +2 °C, mit Validierung von Datum, Einheit und Messwert |
| Wetteraufgabe | Bei aktivierter Frostprüfung ein einmaliger Kalendereintrag pro prognostiziertem Frosttag: **Pflanzen kontrollieren**, keine Behandlung; Dublettenschutz im Datenspeicher |
| Push | Optionale Push-Nachricht für mögliche Frostgefahr und eine zusammenfassende Benachrichtigung freitags 16 Uhr über ausgewählte Home-Assistant-Notify-Entität oder gerätespezifischen Dienst |
| Standardsicherheit | Pushs anfänglich **aus**. Es wird kein allgemeiner Broadcast-Dienst angeboten; Wetter- und Notify-Ziel müssen explizit angegeben werden |
| Kombinierte Erledigung | Einfache Aufgaben bleiben 1-Klick-Aufgaben. Gießkontrollen verlangen die Entscheidung „Gegossen“ oder „Kontrolliert – kein Wasser nötig“. Beide Fälle werden mit Benutzer, Zeitpunkt und Ergebnis in der Historie geführt |
| Differenzierte Wiederholungen | Neu angelegte Gießkontrollen behalten ihre Art bei Fälligkeit, Neustart und Folgeintervall. Der Quellstatus bleibt auch nach Entfernen einer Wiederholungsregel am erledigten Termin |
| Pflegeprofil-Cache | Vollständig übersetzte Profile bleiben bis zu 30 Tage zwischengespeichert, teilweise übersetzte nur kurz; bereits übersetzte Felder werden per Quellenfingerabdruck lokal wiederverwendet. Eindeutig als deutsch deklarierte Quellfelder werden nicht durch Englisch-Deutsch-Übersetzung verändert |
| Such-Breitenprüfung | 50 reale deutsche Gartennamen aus fünf Gruppen mit aktuellem Suchcode geprüft: 50/50 erwartete botanische Arten in den ersten 15 Vorschlägen, 40/50 auf Rang 1 (repräsentative Live-Stichprobe, keine Aussage zur gesamten deutschen Gartenflora); keine festen Beispielaliases in der App |

**Ausführung (lokale Home-Assistant-Zeitzone):** wiederkehrende Aufgaben jeden Tag um 00:05 Uhr und bei Aktivierung/Erstellung; Frostprüfung täglich 06:15 und 18:15 Uhr; Wochenübersicht freitags um 16:00 Uhr. Nach einem Neustart wird der Pflegeplan erneut geprüft. Ein automatischer Push unmittelbar nach der Installation ist nicht vorgesehen.

### Bedienung nach einer späteren Freigabe

1. **Pflanzen → Pflegewissen** öffnen. Bei vorhandenen übersetzten Informationen kann „Jährliche Kontrolle dazu planen“ gewählt werden. **Datum selbst festlegen und speichern**. Das ist eine Erinnerungsregel und ausdrücklich keine geprüfte Schnitt- oder Düngeanweisung.
2. **Kalender → Benachrichtigungen** öffnen. Bestehenden iPhone-Empfänger aus Home Assistant auswählen und für Frostwarnungen auch eine vorhandene Wetterentität angeben. Wöchentliche Zusammenfassung und Frostwarnung können separat eingeschaltet werden.
3. **Kalender → Meine Wiederholungen** verwaltet bestehende manuell angelegte Intervalle und Jahresregeln. Frostaufgaben erscheinen als Wetterprognose gekennzeichnet.

## Persistenz

- Gartendaten und Nutzerregeln: `.storage/mein_garten_v1.data`
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
