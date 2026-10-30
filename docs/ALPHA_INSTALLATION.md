# Mein Garten V1 – Installations- und Testvorbereitung für Home Assistant Green

**Stand: 30.10.2026 · Entwicklungsbranch, keine produktive Installationsfreigabe.** Die Gartenintegration wurde in GitHub Actions technisch geprüft, aber **die aktuelle Entwicklungsfassung noch nicht auf Home Assistant Green installiert oder dort abgenommen**. Das bestehende Dashboard **„Zuhause“ darf weder verändert noch durch ein Garten-Dashboard ersetzt werden**.

> **Wichtig:** Der aktuelle neue Funktionsstand befindet sich nur im offenen [Draft-PR #1](https://github.com/p-weigner/mein-garten/pull/1) auf dem Branch `codex/garten-pflegewissen-und-suche-20261030`. **Eine HACS-Installation vom Branch `main` liefert NICHT automatisch diesen Entwicklungsstand.** Bitte vor einem gezielten Alpha-Livetest weder das Haupt-Dashboard bearbeiten noch ein beliebiges altes Installationspaket verwenden.

## 1. Was im aktuellen Entwicklungsbranch implementiert ist

- Vier Bereiche: **Start, Pflanzen, Kalender und Bereiche**, im bestehenden dunklen Gartenstil.
- Breite dynamische Pflanzensuche über botanische und deutsche Namen. Unklare Zuordnungen werden kenntlich gemacht; eigene Pflanzen ohne Treffer können weiterhin angelegt werden.
- Eigene Pflanzennotizen, frei bearbeitbare Gartenbereiche, manuelle Aufgaben und nutzerdefinierte Wiederholungen.
- Gespeicherte Pflegeentscheidungen: **„Gegossen“** oder **„Kontrolliert – kein Wasser nötig“**. Verlauf pro Pflanze mit früheren Erledigungen, tatsächlichen Zeitpunkten und Schnellzugriff auf ein **noch nicht gespeichertes** Formular für eine weitere Kontrolle.
- Manuelles Planen und Abschließen mit **Gießverlauf als Kontext**, aber ohne automatische Ermittlung von Gießterminen oder Wasserbedarf.
- Deutsche Pflegeprofile aus OpenPlantbook/Übersetzung soweit verfügbar; Quelle und ältere, nicht erneut bestätigte Einzelhinweise werden gekennzeichnet. Persönliche Notizen bleiben lokal.
- Getrennte CC0-Standortgrundlagen, **europäische EIVE-Indikatoren (CC BY 4.0)**, vorsichtige unverbindliche Saisonfenster und DWD-Phänologie-Referenzdaten.
- Optionaler Freitagsbericht und Frost-Prüfung über vorhandene Home-Assistant-Dienste. Die Einstellungen müssen ausdrücklich aktiviert werden; es werden keine neuen externen kostenpflichtigen Konten vorausgesetzt.

**Nicht als fertig freigegeben:** Fachlich zuverlässige automatische Schnitt-, Dünge- und Pflanzregeln für Brandenburg, Pflanzenfotos/automatische Bildbestimmung, vollständige Prüfung auf der echten Home-Assistant-Green-Hardware und der iPhone-App.

## 2. Vorabbedingungen für einen bewussten Livetest

1. Im [Draft-PR](https://github.com/p-weigner/mein-garten/pull/1) den **genauen aktuellen Commit** ablesen.
2. Unter [GitHub Actions – Mein Garten V1 – Alpha-Paket](https://github.com/p-weigner/mein-garten/actions/workflows/garten-alpha-paket.yml) einen **erfolgreichen** Lauf auswählen, dessen `head_sha` **exakt diesem Commit** entspricht. Ein grüner Lauf eines früheren Commits reicht ausdrücklich **nicht**.
3. Im Lauf unter **Artifacts** das `Mein_Garten_V1_Alpha_Testpaket` öffnen. Es enthält zusätzlich den maschinenlesbaren **`ABNAHME.json`**-Bericht mit Quell-Commit, geprüften Datei-Hashes, Kartentyp und der ausdrücklichen Kennzeichnung **`home_assistant_green_installiert: false`**.
4. Falls der aktuelle Lauf nur **queued / in progress / failure** zeigt, **nicht installieren**. Zuerst die CI-Fehler beheben und einen erfolgreichen vollständigen Build abnehmen.
5. **Vollständiges Home-Assistant-Backup** vor einem Eingriff erstellen und lokal erreichbar sichern. Garten-Altversion und vorhandene Dashboard-Ressourcen dokumentieren; die bestehenden Bereiche und insbesondere „Zuhause“ dürfen unangetastet bleiben.
6. Vor der Installation den vorhandenen Integrationszustand (HACS-Installation, bestehende Karte, Name der Lovelace-Ressourcen und Garten-Dashboard) prüfen. Diese Integration wird weiterhin unter der eigenen Domain `mein_garten` geladen, kann also ein vorhandenes Garten-Alpha ersetzen. **Es gibt keinen parallelen zweiten Backend-Namensraum.**

## 3. Inhalt eines zulässigen Alpha-Testpakets

| Bestandteil | Speicherort im Artefakt | Funktion |
|---|---|---|
| Integration | `custom_components/mein_garten/` | Python-Backend, lokales Frontend und geprüfte Offline-Daten |
| Garten-Dashboard | `Mein_Garten_Dashboard.yaml` | **Ausschließlich** `custom:mein-garten-v1-card` |
| Anleitung | `ANLEITUNG.md` | Dieselbe vollständige Anleitung wie im geprüften Commit |
| Status | `STATUS.txt` | Kennzeichnung als unfertiger Alpha-Test |
| HACS-Metadaten | `hacs.json` | Integrationsmetadaten |
| Paketprüfung | `ABNAHME.json` | Quell-Commit, Manifestversion und SHA-256-Fingerabdrücke der kritischen Dateien |

Die CI-Paketprüfung stoppt bei fehlenden Dateien, Abweichungen zu den Repository-Dateien, falscher Version, fremden Home-Assistant-Integrationen, Konfigurations-/Geheimdateien und symbolischen Links. Ein **erfolgreicher Paketcheck ist trotzdem kein Live-Test**.

## 4. Getrennter Installationspfad für den späteren Test

**Nur wenn der aktuelle PR-Commit im erfolgreichen Alpha-Artefakt bestätigt ist und ein Backup existiert:**

1. Das **exakt zu diesem Commit gehörende** Artefakt entpacken. **Nicht** einfach in HACS auf `main` klicken und davon ausgehen, dass es die neue Version ist.
2. Die **vollständige** enthaltene Ordnerstruktur `custom_components/mein_garten` auf dem Home Assistant Green unter `/config/custom_components/mein_garten` installieren. Hierfür muss eine vorhandene, berechtigte Dateiverwaltung beziehungsweise eine vom Nutzer eingerichtete Dateiübertragung zur Verfügung stehen. Kein manuelles Ersetzen einzelner Python- oder JavaScript-Funktionen.
3. Home Assistant vollständig neu starten und unter **Einstellungen → Geräte & Dienste** prüfen, dass die bestehende Integration **Mein Garten** geladen ist. Falls sie noch nicht eingerichtet ist, die Integration einmalig hinzufügen.
4. In **Einstellungen → Dashboards → Ressourcen** sicherstellen, dass die **zusätzliche** JavaScript-Modul-Ressource `/api/mein_garten/mein-garten-v1-card.js` eingebunden ist. Wenn ein älterer JavaScript-Stand zwischengespeichert ist, eine neue Query-Version anhand des gerade getesteten Commits verwenden, beispielsweise `?v=<commit-kurzsha>`; die bisherige Gartenressource bis zum erfolgreichen Test **nicht löschen**.
5. **Nur im eigenständigen Garten-Dashboard** die vollständige Datei `Mein_Garten_Dashboard.yaml` als Rohkonfiguration verwenden. Sie besteht aus dem Kartentyp `custom:mein-garten-v1-card`. **Auf keinen Fall** die Rohkonfiguration des Dashboards „Zuhause“ öffnen oder ersetzen.

## 5. Konkrete Live-Abnahme auf Home Assistant Green / iPhone

Der vollständige [HA-Green-Abnahmeplan](HA_GREEN_ABNAHME_2026-10-30.md) beschreibt die Prüfschritte und die erwarteten Ergebnisse. Besonders zu prüfen sind:

- Gartenkarte wird nach Neustart mit allen vier Bereichen geladen und **„Zuhause“ funktioniert unverändert**.
- Pflanzensuche, Pflanzenanlage ohne Treffer und deutschsprachige Pflegehinweise bzw. verständliche Fehlermeldungen bei nicht erreichbaren Quellen.
- Pflanze und Gartenbereich bleiben nach HA-Neustart erhalten.
- „Gegossen“ und „Kontrolliert – kein Wasser nötig“ werden unabhängig gespeichert, auch nach Neustart; eine wieder geöffnete Aufgabe zählt nicht mehr als erledigt.
- Eine neue Gießkontrolle über **Pflanzen → Verlauf** öffnet nur ein **noch nicht gespeichertes** Formular. Das Datumsfeld bleibt leer, das Speichern erfordert eine Nutzeraktion.
- Wechsel der Pflanze im Formular aktualisiert die Gießhistorie **ohne** Verlust des manuell eingetippten Namens und Datums – insbesondere auf dem iPhone.
- Bei Ausfall von OpenPlantbook bleiben verfügbare Standortgrundlagen und persönliche Notizen sichtbar.
- Optionale Offline-Indikatoren und saisonale Hinweise erscheinen ohne automatisch erzeugte, fachlich nicht bestätigte Pflegeanweisungen.
- Bei einer Fehlfunktion den bisherigen funktionsfähigen Gartenstand und notfalls das vorbereitete Home-Assistant-Backup wiederherstellen. Andere Dashboards bleiben weiterhin unverändert.

**Datenschutz:** Keine vollständigen HA-Protokolle, Tokens, privaten Pflanzennotizen oder Personenkennungen öffentlich auf GitHub hochladen. Bei Bedarf Fehlertexte vor dem Teilen bereinigen.

## 6. Aktueller Freigabestatus

Der Entwicklungszweig ist **Draft** und die ursprüngliche ältere Garten-Alpha war bereits separat auf Home Assistant Green geladen. **Die neue Entwicklungsfassung ist nicht produktiv getestet oder installiert**. Kein automatischer Merge und keine Installation ohne bewusste Entscheidung des Nutzers.

Weitere Referenz: [Ressourcentrennung bei Lovelace-Konfigurationsfehlern](KONFIGURATIONSFEHLER_LOVELACE.md).
