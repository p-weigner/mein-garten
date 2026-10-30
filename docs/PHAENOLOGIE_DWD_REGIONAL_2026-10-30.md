# Mein Garten – regionaler DWD-Phänologievergleich (Entwurf, 30.10.2026)

**Status:** Nur Draft-Pull-Request #1. Kein Merge, keine Installation auf Home Assistant Green, keine Änderung am Dashboard „Zuhause“.

## Zweck und Grenzen

Das zusätzliche Feld im vorhandenen Gartenkalender zeigt die **tatsächlich gemeldeten Entwicklungszeitpunkte** von drei allgemeinen phänologischen Indikatoren aus dem Sofortmelder-Netz des Deutschen Wetterdienstes. Es vergleicht historische Jahre und die räumlich grob ausgewählte Nordost-Region mit dem gesamtdeutschen Stationsbestand.

**Die DWD-Statistiken sind keine Vorhersagen.** Sie sind weder Messungen im eigenen Garten noch ein Beweis für eine bestimmte Entwicklungsphase einer persönlichen Pflanze. Daraus werden **keine automatischen Schnitt-, Dünge-, Gieß-, Pflanzenschutz- oder Aussaatregeln** abgeleitet.

### Verwendete offizielle Datensätze

Quelle: **Deutscher Wetterdienst (DWD), Climate Data Center (CDC)**

[Lizenz: Creative Commons Namensnennung 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.de). Die aggregierte Darstellung wurde von „Mein Garten“ aus den unten genannten DWD-Rohdateien selbst berechnet; sie ist **keine originale DWD-Prognose oder DWD-Karte**.

DWD-Datenverzeichnis: https://opendata.dwd.de/climate_environment/CDC/observations_germany/phenology/immediate_reporters/wild/recent/

Stationskatalog: https://opendata.dwd.de/climate_environment/CDC/help/PH_Beschreibung_Phaenologie_Stationen_Sofortmelder.txt

Die drei offiziellen CSV/Textdateien im obigen Verzeichnis:

| Indikator | DWD-Quelldatei | Objekt-ID | Phasen-ID |
|---|---|---:|---:|
| Hasel, Arten nicht getrennt – Blütebeginn | `PH_Sofortmelder_Wildwachsende_Pflanze_Hasel_akt.txt` | 113 | 5 |
| Forsythie – Blütebeginn | `PH_Sofortmelder_Wildwachsende_Pflanze_Forsythie_akt.txt` | 109 | 5 |
| Rotbuche – Blattentfaltung | `PH_Sofortmelder_Wildwachsende_Pflanze_Rotbuche_akt.txt` | 123 | 4 |

Diese DWD-Indikatoren sind **nicht** automatisch mit der botanischen Art einer individuell erfassten Gartenpflanze verknüpft. Beispielsweise unterscheidet die DWD-Sofortmeldung bei Haselarten nicht alle Arten; das Dashboard darf deshalb keine eigene Pflanze allein aufgrund eines ähnlichen Namens als identisch behandeln.

## Datenstand und Auswahl

Der lokale, festgehaltene Snapshot vom **30. Oktober 2026** enthält **18 Vergleichswerte**:

- **3 Indikatoren** für jeweils **2024, 2025 und 2026** in **2 großen Referenzgebieten**.
- „Nordost“ ist ein bewusst grober geografischer Ausschnitt innerhalb des deutschen DWD-Stationsnetzes: **52,0 bis 54,2° nördliche Breite / 12,0 bis 15,0° östliche Länge**. Er entspricht **nicht** exakt einer Landesgrenze, dem Landkreis Barnim oder einem Hausgrundstück.
- „Deutschland“ umfasst alle im offiziellen Stationskatalog mit gültigen deutschen Stationskoordinaten zugeordneten Messstellen.
- Nur Kombinationen mit mindestens **5 eindeutigen Stationen** werden angezeigt. Im Nordost-Snapshot liegen für die drei Indikatoren und drei Jahre jeweils **18–23 Stationen** vor.
- Der Wert **Median** ist der mittlere beobachtete Eintrittstag nach Sortierung (bei gerader Anzahl wird der untere der beiden mittleren tatsächlichen Beobachtungstage verwendet). Daneben erscheint der Bereich vom unteren bis zum oberen empirischen Quartil – als „mittlere 50 %“. **Keine** künstlich errechneten zukünftigen Termine.

### Beispielwerte: Nordost (Stationsmediane)

| DWD-Phase | 2024 | 2025 | 2026 |
|---|---|---|---|
| Hasel, Blütebeginn | 29.01. | 01.02. | 27.02. |
| Forsythie, Blütebeginn | 03.03. | 25.03. | 20.03. |
| Rotbuche, Blattentfaltung | 10.04. | 16.04. | 21.04. |

Der direkte Vergleich der Jahre illustriert die zeitliche Streuung, aber keine exakte Art- oder Wetterprognose für einen einzelnen Garten.

## Qualitätssicherung des Importprozesses

- Die DWD-Sofortmelder-Dateien werden **ausschließlich in einem GitHub-Actions-Entwicklungsworkflow** abgerufen und dort auf eine kleine, versionierte JSON-Datei reduziert. Home Assistant Green benötigt zur Laufzeit **keine DWD-Verbindung**, keine Standortfreigabe, keinen API-Schlüssel und kein Abonnement.
- Auf Grundlage der offiziellen Datenbeschreibung werden nur Meldungen mit `Eintrittsdatum_QB=1` („nicht beanstandet“) übernommen. Die Qualitätsniveaus `QN=1` (nur formal geprüft), `7` und `10` sind zugelassen. Daher wird ausdrücklich **keine Vollprüfung aller aktuellen Beobachtungen behauptet**.
- Ein Eintrittsdatum muss dem angegebenen Referenzjahr entsprechen; unplausible Kombinationen, unbekannte Stationen und widersprüchliche Datumsangaben derselben Station/Phase/Jahr-Kombination werden ausgeschlossen.
- Die DWD-`Jultag`-Spalte verwendet in den untersuchten Dateien ab März eines Schaltjahres eine **365-Tage-Zählung**. Der Import gleicht diese Spalte mit dem echten ISO-Beobachtungsdatum ab, ohne Datumsverschiebungen für Nutzer zu erfinden.
- Regionale Median- und Quartilswerte werden nur aus gültigen, eindeutigen Stationsterminen berechnet. Mehrfachmeldungen einer Station zählen nicht mehrfach.
- Alle vier Rohdateien (drei Arten plus Stationskatalog) werden mit ihrem **SHA-256-Fingerabdruck** im Snapshot dokumentiert, sodass eine andere Datenfassung erkannt und gesondert auditiert werden kann.
- Der Snapshot wird im Home-Assistant-Backend vor der Ausgabe streng validiert; fehlerhafte optionale DWD-Daten werden **weggelassen**, ohne die private Gartenverwaltung zu blockieren.
- Beim Datenimport werden **keine Nutzerpflanzen, Notizen, Gartentagebücher, IP-basierten Ortsabfragen oder Personenkennungen** an den DWD übertragen.

## Ablage und Anzeige

- Offline-Snapshot (etwa 7 KB): `custom_components/mein_garten/data/dwd_phaenologie_region_v1.json`
- Datenimport und Audit: `tools/dwd_phaenologie_probe.py`, `tools/dwd_phaenologie_export.py`
- Quellprüfungs-CI: `.github/workflows/garten-dwd-phaenologie-audit.yml`
- Export-CI: `.github/workflows/garten-dwd-phaenologie-export.yml`
- Laufzeitvalidierung: `custom_components/mein_garten/dwd_reference.py`

Im **Pflegekalender** erscheint nach der eigenen Beobachtungshistorie ein eigenständiger Bereich **„DWD: Jahreszeiten im Vergleich“**. Die beiden Schaltflächen „Nordost“ und „Deutschland“ ändern **nur die örtliche Darstellung** des bereits lokal verfügbaren Snapshots – sie führen **keinen API-Aufruf** und keine präzise Standortbestimmung aus. Historische Mediane, Quartilsspannen, Stationszahl, Datenstand und amtliche Quelle sind sichtbar.

Die bestehende eigene Beobachtungshistorie, Pflegeaufgaben, die Pflanzensuche und das separate Home-Assistant-Dashboard „Zuhause“ bleiben unverändert.

## Offene fachliche Prüfungen

1. Der Snapshot ist fixiert und wird **nicht live aktualisiert**. Bei neuen Jahresmeldungen ist ein gesonderter, reproduzierbarer Datenimport mit erneutem Quellen- und Lizenznachweis nötig.
2. Die bisherigen drei Indikatoren reichen **nicht** für breite artspezifische Pflegeanweisungen, insbesondere bei Stauden, Ziergehölzen und Rosen.
3. Eine tiefergehende stationäre Qualitäts-/Repräsentativitätsprüfung und die Frage, welche phänologischen Phasen wirklich valide regionalen Pflegezeitpunkten zugeordnet werden können, sind offen.
4. Echter Laufzeittest auf Home Assistant Green, iPhone-/Tabletansicht, Backup/Restore, Originalintegration und Benachrichtigungskontrollen bleiben notwendig.

**Keine monatlichen Gebühren. Kein Merge und keine Installation.**
