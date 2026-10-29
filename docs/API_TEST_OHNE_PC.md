# Pflegequellen auf GitHub testen – ohne privaten PC

Die öffentliche botanische Namenssuche ist bereits geprüft. Für **echte Pflege-Daten** verlangt Permapeople einen separaten API-Zugang. Er ist für nicht kommerzielle Projekte vorgesehen, benötigt aber ein Benutzerkonto.

## Was bereits funktioniert

Unter https://github.com/p-weigner/mein-garten/actions stehen zwei Workflows:

- **Datenquellen-Livetest:** GBIF und iNaturalist – vollautomatisch ohne Zugangsdaten.
- **Pflegequellen-Prüfung:** 33 Offline-Tests und ein optionaler API-Livetest. Ohne API-Zugang wird ausdrücklich \`nicht_getestet\` gemeldet.

## Optionaler Permapeople-Zugang

Nur falls der kostenlose nicht kommerzielle API-Test ausdrücklich gewünscht ist:

1. Auf https://permapeople.org/ ein Konto eröffnen und unter **My API keys** ein API-Schlüsselpaar erstellen.
2. Im öffentlichen GitHub-Repository unter **Settings → Secrets and variables → Actions** zwei **Repository secrets** erstellen. Die Werte werden dabei nicht Teil des öffentlichen Quellcodes:
   - \`PERMAPEOPLE_KEY_ID\` – der Key-ID-Wert
   - \`PERMAPEOPLE_KEY_SECRET\` – der Secret-Wert
3. Auf **Actions → Pflegequellen-Prüfung → Run workflow** klicken.
4. Im anschließend erzeugten Artifact \`mein-garten-pflegequellen\` stehen die Treffer- und Feldzahlen für 21 Pflanzen – **keine vollständigen Pflegequelltexte, keine Schlüssel**.

**Bitte niemals Zugangsdaten in eine Chatnachricht, ein GitHub-Issue oder eine Datei im Repository eintragen.** Bei Fehlern Schlüssel nicht als Screenshot weitergeben.

Bei der Nutzung der Daten ist die CC-BY-SA-4.0-Lizenz mit Quellenangabe und Share-Alike zu beachten:
https://permapeople.org/knowledgebase/api-docs/

## Optionale Azure-Übersetzung (noch nicht nötig)

Der Workflow unterstützt später diese Secrets:

- \`AZURE_TRANSLATOR_KEY\`
- \`AZURE_TRANSLATOR_REGION\` (falls die Azure-Ressource eine Region verlangt)

**Bitte aktuell kein Azure-Konto nur für den Test eröffnen.** Azure verlangt ein Nutzerkonto und eine Azure-Subscription; andere Ressourcen können Kosten verursachen. Sobald wir eine geeignete Datenquelle gefunden haben, entscheiden wir die Übersetzung getrennt. Dann muss ausdrücklich der kostenlose F0-Tarif ausgewählt und kontrolliert werden.

Der technische Prototyp sieht ein lokales Zeichenbudget und eine persistente Übersetzungsspeicherung vor. Beides ist noch nicht produktiv im Home Assistant eingebaut.

## Datenschutz / Veröffentlichung

Das Repository ist **öffentlich**. Deshalb gehören persönliche Fotos, Adressen, Pflanzenstandorte, persönliche Notizen und die API-Antworttexte nicht in GitHub-Artefakte. Der Pflegequellen-Workflow gibt nur aggregierte Feld- und Trefferzahlen aus.

## Grenzen

Ein grünes Ergebnis ohne konfigurierten API-Schlüssel heißt **nicht**, dass die Pflegequellen funktionieren oder deutsche Pflegeanleitungen liefern. Für die tatsächliche Qualität von Schnitt-/Dünge-/Gießratschlägen ist nach den API-Livetests eine gesonderte fachliche Prüfung erforderlich.
