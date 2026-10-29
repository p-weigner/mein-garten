# Mein Garten 🌿

Eigenständiges Home-Assistant-Gartendashboard. **Neuaufbau V1 – derzeit Datenquellen-Prüfung, noch keine installierbare Integration.**

## Verbindliche Anforderungen

- Das vorhandene Home-Assistant-Dashboard **„Zuhause“ bleibt unangetastet**.
- Freigegebenes dunkelgrünes Design; Navigation **Start · Pflanzen · Kalender · Bereiche**.
- Neue Pflanzen jederzeit per Suchfeld hinzufügen, **ohne Codeänderung**.
- Pflegedaten aus dynamischen Quellen, automatisch auf Deutsch, mit Quelle, Prüfstatus und lokalem Cache.
- Pflegeregeln berücksichtigen Pflanzenart, bei Bedarf Sorte und Bedingungen. Keine ungesicherten Schnitt-/Giftigkeits-/Düngeempfehlungen als automatische Aufgaben.
- Gartenbereiche dynamisch anlegen, umbenennen und entfernen; Pflegehistorie.
- Später: Freitag-Nachmittag-Zusammenfassung an Angelinas iPhone und zusätzliche wichtige Frost-/Wetterwarnungen.
- Keine monatlichen Pflicht-Abonnements oder ungeprüften Cloud-Kosten.

## Was jetzt im Repository passiert

**Phase 1:** Öffentliche botanische Namenssuche mit GBIF und iNaturalist an 21 Beispielpflanzen automatisch auf GitHub Actions testen. Anschließend getrennt die authentifizierten Pflege-Datenquellen und die deutsche Übersetzung prüfen.

Die Testpflanzen sind ausschließlich **öffentliche Beispielfälle**. Sie werden nicht als feste Pflanzenliste in das Gartendashboard eingebaut.

> Aktueller Code und Testberichte sind **kein Home-Assistant-Update**. Keine Daten des bestehenden Systems werden verändert.

## Datenschutz und Sicherheit

- Keine privaten Pflanzenfotos, Gartenstandorte, Home-Assistant-Konfigurationen oder API-Schlüssel einchecken.
- Öffentliche API-Tests benötigen keine Zugangsdaten.
- Eventuelle spätere Zugangsdaten ausschließlich als GitHub Actions Secrets oder lokal in Home Assistant einrichten; nie in Logs oder Berichten veröffentlichen.
- GitHub-Actions-Rechte so gering wie möglich halten (`contents: read`).

Weitere Hinweise zur Ausführung unter **Actions** werden mit dem Datenquellen-Workflow ergänzt.
