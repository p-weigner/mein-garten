# Mein Garten – Abnahmeplan für Home Assistant Green und iPhone

**Stand: 30.10.2026. Nur Testvorbereitung, keine Installation ausgeführt.** Der aktuelle Code liegt im [Draft-PR #1](https://github.com/p-weigner/mein-garten/pull/1). Die Abnahme wird **erst nach einem erfolgreichen GitHub-Actions-Lauf für exakt dessen HEAD-Commit** durchgeführt. Sie ist bis dahin gesperrt.

## Vorbereitende Sicherheitsprüfung

| Kriterium | Erwartetes Ergebnis | Nachweis |
|---|---|---|
| Aktuelles PR-HEAD = CI-Commit | Dieselbe vollständige Commit-SHA in PR, Lauf und `ABNAHME.json` | Offen |
| GitHub-Actions-Lauf | `completed / success` einschließlich Backend, Frontend, Paket- und HA-WebSocket-Schema-Tests | Offen |
| Installationspaket | `Mein_Garten_V1_Alpha_Testpaket` mit `ABNAHME.json`, Gartenintegration, vollständigem Dashboard-YAML und Anleitung | Offen |
| Home-Assistant-Backup | Aktuell, vollständig, gesichert und wiederherstellbar | Offen |
| Bestehendes Dashboard „Zuhause“ | Darstellung, Ressourcen, Navigation, Automationen und Heiz-/Lichtsteuerung vorab dokumentiert | Offen |
| Garden-Altstand | Vorhandene Integrations- und Frontend-Version erfasst; kein stilles Überschreiben einer unbekannten Version | Offen |
| iPhone und Home Assistant Green | Installation erfolgt nur nach bewusster Zustimmung; keine Änderungen an `main` | Offen |

**Abbruch bei einem fehlgeschlagenen Punkt.** Ein grüner CI-Lauf älterer Commits ist keine gültige Freigabe. Die CI-Paketprüfung ist kein Ersatz für diese Geräteabnahme.

## A. Grundfunktion und Bestandschutz

| Nr. | Prüfung | Erwartetes Ergebnis |
|---|---|---|
| A01 | Gartenintegration nach HA-Neustart öffnen | Keine Konfigurationsfehler, vier Gartenbereiche Start/Pflanzen/Kalender/Bereiche sichtbar |
| A02 | Vorhandenes Dashboard „Zuhause“ öffnen | Alle Kacheln, Räume, Heizpläne und Schnellzugriffe unverändert |
| A03 | iPhone-App schließen und erneut öffnen | Garten lädt auch nach neuer Sitzung; keine Endlosschleife |
| A04 | Zweites Endgerät verbindet sich mit Garten | Der aktuelle Pflanzen- und Aufgabenstand ist synchron |
| A05 | Internetverbindung temporär trennen | Bereits lokale Pflanzendaten, Gartenbereiche, Aufgaben und Standortindikatoren bleiben lesbar |
| A06 | Alte Gartenressource vorhanden lassen | Alte Ressource wird nicht ersetzt; neue V1-Karte besitzt eigenen Namen |

## B. Pflanzen- und Wissensverwaltung

| Nr. | Prüfung | Erwartetes Ergebnis |
|---|---|---|
| B01 | Deutsche und botanische Pflanzensuche mit mehreren Arten | Treffer und Quellenstatus korrekt; kein Überfit auf Bauernhortensie |
| B02 | Neue Pflanze ohne Suchtreffer anlegen | Eigener Name und Notizen bleiben möglich |
| B03 | Pflanze einer frei angelegten Gartenfläche zuordnen | Zuordnung funktioniert ohne YAML-Bearbeitung |
| B04 | Pflanze ohne Gartenfläche anlegen | Keine Pflichtzuordnung; später editierbar |
| B05 | Pflegewissen mit OpenPlantbook-Verfügbarkeit öffnen | Nur tatsächliche deutsche Hinweise; Quelle/Übersetzungsstatus sichtbar |
| B06 | OpenPlantbook nicht erreichbar | Lokal gespeicherte Hinweise, persönliche Notizen und Standortgrundwerte bleiben erhalten |
| B07 | Pflegequelle erneut prüfen | 5-Minuten-Schutz; bestehende übersetzte Texte werden bei Fehlantwort nicht gelöscht |
| B08 | Teilweise fehlender Pflegehinweis | Älterer Einzelhinweis getrennt mit Abrufdatum markiert, keine neue Jahreskontroll-Aktion darauf |
| B09 | EIVE-Indikatoren einer passenden Art | DOI, CC-BY-Lizenz, Wert und Zahl der Quellsysteme sichtbar |
| B10 | EIVE-Art nicht enthalten | Keine erfundene Artübereinstimmung oder generierte Pflegeanweisung |
| B11 | Pflanze und Bereich nach HA-Neustart | Daten weiterhin vorhanden |

## C. Pflegeverlauf und Gießentscheidungen

| Nr. | Prüfung | Erwartetes Ergebnis |
|---|---|---|
| C01 | Gießkontrolle für eine Pflanze erstellen und als „Gegossen“ abschließen | Aufgabe erledigt, tatsächliches Gießen und Zeitpunkt gespeichert |
| C02 | Zweite Gießkontrolle als „Kontrolliert – kein Wasser nötig“ abschließen | Zähler „Gegossen“ erhöht sich **nicht**; letzte Kontrolle aktualisiert sich |
| C03 | „Pflanzen → Verlauf“ öffnen | Erledigungen der gewählten Pflanze korrekt getrennt, keine Daten anderer Pflanzen |
| C04 | „＋ Gießkontrolle anlegen“ im Verlauf antippen | Formular vorausgewählt, **Datum leer**, noch **keine neue Aufgabe** angelegt |
| C05 | Manuelles Datum oder Name eingeben, danach Pflanze wechseln | Nur Verlaufs-Infobereich aktualisiert sich, eigene Eingaben bleiben unverändert |
| C06 | Erledigungsart von „Gießkontrolle“ auf „Ein Klick – erledigt“ ändern | Verlaufs-Infobereich verschwindet, Aufgabenart aktualisiert sich |
| C07 | Bereits offene Gießkontrolle für dieselbe Pflanze | Warnhinweis, keine automatische Entfernung oder Zusammenführung |
| C08 | Bereits offene Gießkontrolle abschließen | Vorherige Gießhistorie sichtbar, Ergebnis muss bewusst bestätigt werden |
| C09 | Wiederkehrende Kontrolle anlegen | Benutzer setzt Start und Intervall selbst; nichts aus dem Verlauf geschätzt |
| C10 | Aufgabe wieder öffnen | Der aktuell erledigte Eintrag wird nicht mehr als „erledigt“ gezählt |
| C11 | Aufgabe löschen | Gelöschter Vorgang verschwindet aus der aktuell sichtbaren Verlaufsliste |
| C12 | Home Assistant neu starten | Gießentscheidung und letzter tatsächlicher Gießzeitpunkt bleiben gespeichert |

## D. Saison, Benachrichtigungen und Sicherheit

| Nr. | Prüfung | Erwartetes Ergebnis |
|---|---|---|
| D01 | Saisonkalender öffnen | Saisonfenster als unverbindlich und nicht regional geprüft beschriftet |
| D02 | Frost-Referenzdaten fehlen | Keine willkürlichen lokalen Frosttage |
| D03 | Persönliche Pflegeaufgabe vormerken | Speicherung erst nach Bestätigung, keine automatische Aussaat oder Düngung |
| D04 | Freitags-Push deaktiviert lassen | Keine ungefragte Wochenbenachrichtigung |
| D05 | Frost-Push deaktiviert lassen | Keine ungefragte Wetterwarnung |
| D06 | Benachrichtigung bewusst aktivieren | Nur der konfigurierte Home-Assistant-Nachrichtendienst wird verwendet |
| D07 | Pflegefelder bei Quellenausfall | Keine automatischen neuen Gieß-, Schnitt-, Dünge- oder Pflanzregeln |
| D08 | Persönliche Notiz mit Sonderzeichen anzeigen | HTML-sicher, kein Skript wird ausgeführt |
| D09 | Mehr als 20 abgeschlossene Aufgaben | Verlauf lädt ältere Einträge schrittweise, Darstellung auf iPhone stabil |

## E. Rückfall und Abschluss

Der vorherige funktionierende Gartenstand muss vor Änderungen über das **vollständige HA-Backup** verfügbar bleiben. Die bestehende separate Garten-Konfiguration wird nur nach ausdrücklicher Entscheidung durch die neu getestete Garten-YAML ersetzt. Bei einem fehlgeschlagenen Test: keine weiteren Änderungen an „Zuhause“, Garten-Vorversion beziehungsweise Backup wiederherstellen und Ursache anhand **bereinigter** HA-Protokolle dokumentieren.

**Abnahmeentscheidung erst nach realen Beobachtungen:**

- **Erfolgreich:** Alle kritischen Punkte A01/A02, B01/B05/B06/B11, C01–C05/C08/C12 sowie D04/D05/D07 bestanden; übrige Punkte dokumentiert und keine gravierenden Fehler.
- **Eingeschränkt:** Technische Mindestfunktionen vorhanden, aber einzelne optionale Quellen/Ansichten auffällig; vor produktiver Nutzung nacharbeiten.
- **Nicht bestanden:** Datenverlust, Änderung an „Zuhause“, unbestätigte automatische Aufgaben, nicht ladende Karte, falsche Pflanzenzuordnung oder fehlgeschlagene Wiederherstellung.

**Weder dieser Plan noch GitHub Actions beweisen eine erfolgte Installation.** Bis zur echten Abnahme bleiben alle Felder **offen**.
