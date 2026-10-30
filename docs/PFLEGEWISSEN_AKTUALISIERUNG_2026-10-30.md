# Mein Garten – Pflegeinformationen zuverlässig aktualisieren (30.10.2026)

**Status:** Nur auf dem [Entwicklungsbranch / Draft-PR #1](https://github.com/p-weigner/mein-garten/pull/1) umgesetzt und in isolierten Tests bestätigt. **Nicht** auf dem Home Assistant Green installiert, **kein** Merge nach `main`, **keine** Änderung am bestehenden Dashboard „Zuhause“.

## Welches Problem die Änderung löst

OpenPlantbook kann zeitweise keine Art finden, eine fehlerhafte Antwort liefern oder nicht erreichbar sein. Zusätzlich können Übersetzungen unvollständig bleiben, etwa wegen der kostenlosen Tagesgrenze des Übersetzungsdienstes. Eine eigentlich bekannte Pflanze soll deshalb nicht unnötig eine leere Pflegeansicht erhalten.

## Neue Bedienung

1. In **Pflanzen** eine bereits erfasste Pflanze öffnen und **Pflegewissen** wählen.
2. Standort-Grundmerkmale des lokalen CC0-Katalogs und persönliche Notizen erscheinen **ohne** externen OpenPlantbook-Abruf.
3. Tatsächlich verfügbare deutsche Pflegehinweise werden einzeln angezeigt. Fehlende Felder erscheinen nicht als leere Karten. Die Anzahl nicht vorhandener Felder wird kompakt erwähnt.
4. **Pflegequelle erneut prüfen** lädt das Profil auf Wunsch erneut, auch bevor die normale Cachefrist abläuft.
5. Während der erneuten Prüfung bleiben bereits geladene Pflegehinweise sichtbar; die Schaltfläche wird vorübergehend deaktiviert.
6. Ist OpenPlantbook nicht erreichbar oder liefert keine verwendbaren neuen Texte, werden vorhandene deutsche Hinweise als **alter, nicht erneut bestätigter Cache-Stand** angezeigt. Der Fehlerzustand ist transparent sichtbar.
7. **Neu: Bei Teilantworten** bleiben auch einzelne bereits gespeicherte deutsche Felder erhalten. Beispiel: Ein aktualisierter Gießhinweis ersetzt nur den Gießtext; fehlt der neue Schnitthinweis, bleibt der bisherige Schnitttext mit der Kennzeichnung **„Ältere Information“** sowie dem Datum des letzten zugehörigen Quellabrufs sichtbar. Neu geladene Hinweise haben stets Vorrang.
8. **Sicherheit:** Aus einem als älter markierten Text lässt sich keine neue jährliche Pflegekontrolle planen. Bei einem vollständigen Quellenfehler gilt die Sperre für alle aus dem letzten Cache übernommenen Texte. Die App errät keine Schnitt-, Gieß- oder Düngetermine.
9. Der Abruf kann frühestens **fünf Minuten** nach einer vorangegangenen manuellen Prüfung erneut gestartet werden. Der normale Abruf und die lokale Anzeige bleiben nutzbar.

## Genaues Daten- und Fehlerverhalten

- **Artbindung:** Ausschließlich die botanische Art der tatsächlich angelegten Gartenpflanze darf abgefragt werden. Kein Auslesen über fremde oder nicht gespeicherte Pflanzen-IDs.
- **Normaler Cache:** Vollständig übersetzte Profile bis zu 30 Tage, unvollständige Profile bis zu 18 Stunden. Eine manuelle Neuprüfung kann das überschreiben, nicht jedoch die externe Tagesgrenze der Übersetzung.
- **Drosselung:** Mindestens fünf Minuten zwischen manuellen Prüfversuchen **pro botanischer Art**, in der laufenden Home-Assistant-Instanz. Bei Neustart wird dieser kurze Prüfversuchs-Zähler zurückgesetzt; der persistente **5.000-Zeichen-Tageszähler** der maschinellen Übersetzung bleibt erhalten.
- **Deutsche Alttexte:** Wenn der erneute Abruf ausfällt oder **gar keine** brauchbaren deutschen Felder enthält, bleiben zuvor gespeicherte Texte erhalten. Es wird kein neuer Erfolg vorgetäuscht.
- **Teilantworten:** Bei fehlendem oder nicht übersetztem Einzelfeld bleibt ausschließlich der zuvor für **dieselbe botanische Art und OpenPlantbook-Quelle** gespeicherte deutsche Text erhalten, mit `status: zwischengespeichert` und dem ursprünglichen Datum `zuletzt_bestaetigt_utc`. Das Datum wird bei weiteren Teilantworten nicht künstlich erneuert. Sobald eine neue deutsche Angabe kommt, ersetzt sie das ältere Feld. Ein altes Feld erhält keine neue Jahreskontroll-Aktion. Ein abweichender Artname, eine andere Quelle oder ein offensichtlich ungültiger Text werden nicht übernommen.
- **Dokumentierte Herkunft:** OpenPlantbook-Texte sind nicht fachlich geprüft; ggf. maschinell übersetzte Texte werden als solche gekennzeichnet. Ältere Daten werden im Fehlerfall mit dem ursprünglichen Abrufdatum ausgewiesen.
- **Privatsphäre:** Persönliche Notizen werden nicht an OpenPlantbook oder MyMemory gesendet. Die Schnittstelle sendet nur die botanische Art einer eigenen Pflanze an den vorhandenen Pflegeadapter.
- **Keine autonome Pflege:** Die Neuprüfung legt keine Gieß-, Schnitt-, Dünge- oder Pflanztermine an. Bereits vorhandene manuelle Planung und differenzierte Gieß-Erledigung bleiben unverändert.
- **Bestehende Daten:** `.storage/mein_garten_pflege_v1.data` wird weiterverwendet. Keine Schemaänderung, keine Migration und kein neuer API-Schlüssel erforderlich.

## Technische Änderung

- `custom_components/mein_garten/care.py`: optionale manuelle Neuprüfung mit Lock, artbezogenem Rate-Limit und Rückfall auf gespeicherte deutsche Profile.
- `custom_components/mein_garten/api.py`: optionale boolesche WebSocket-Eingabe `aktualisieren` bei `mein_garten/pflegeprofil`; nur für tatsächlich gespeicherte Pflanzen.
- `frontend/mein-garten-card.js` und `custom_components/mein_garten/frontend/mein-garten-card.js`: identische Karte mit Wiederholungsaktion, Ladezustand, Cache-Warnung und separaten Notizen.
- `tests/test_garten_pflege.py`, `tests/test_ha_ws_behavior.py` und `frontend/tests/card.test.mjs`: Backend-, API-, Bedienungs-, Sicherheits- und Fehlerfalltests, einschließlich Einzelfeld-Historie, späterer Quellenaktualisierung, Artbindung, HTML-Escaping und gesperrter Terminplanung bei älteren Texten.

## Testnachweis

Die erweiterte Einzelfeld-Historie ist im [erfolgreichen Gesamt-Testlauf 41082016491](https://github.com/p-weigner/mein-garten/actions/runs/41082016491) mit **334 Python- und 60 Frontend-Tests**, jeweils ohne Fehler, geprüft. Das neue vollständige Alpha-Testpaket wurde als GitHub-Actions-Artefakt erzeugt. Der frühere Basislauf [41077570176](https://github.com/p-weigner/mein-garten/actions/runs/41077570176) bleibt als Vergleich erhalten.

[Aktueller erfolgreicher GitHub-Actions-Lauf 41082016491](https://github.com/p-weigner/mein-garten/actions/runs/41082016491):

- **334 Python-Tests bestanden**, keine Fehler;
- **60 Node-/Frontend-Tests bestanden**, keine Fehler;
- Python-Kompilierung, JavaScript-Syntax und bytegleiche gespiegelte Frontend-Dateien bestanden;
- HA-2026.10-Probatio-WebSocket-Schema-Prüfung mit echter Bibliothek bestanden;
- vollständiges Alpha-Testpaket erzeugt.

**Wichtig:** Dies ist eine simulierte Backend-/Frontend-Abnahme auf GitHub Actions. Das tatsächliche Home Assistant Green, dessen OpenPlantbook-Konfiguration, Netzwerkausfälle und die iPhone-Bedienung müssen vor einer Installationsfreigabe separat geprüft werden.
