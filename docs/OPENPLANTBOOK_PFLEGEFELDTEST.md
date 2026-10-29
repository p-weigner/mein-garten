# OpenPlantbook-Pflegequellen testen – ohne neues Konto

**Ziel:** Tatsächliche Feldabdeckung von Schnitt, Düngung, Gießen, Licht und Boden bei 13 repräsentativen Arten prüfen. Die bestehende OpenPlantbook-Integration in Home Assistant wird verwendet; **keine API-Schlüssel müssen nach GitHub**.

## Vorbereitung

OpenPlantbook muss in Home Assistant bereits funktionieren und `include: care` unterstützen (ab Integration v1.5.0).

[Vollständiges temporäres Testskript (YAML)](../tests/manual/Mein_Garten_OpenPlantbook_Pflegepruefung.yaml)

## Einmalig durchführen

1. **Home Assistant → Einstellungen → Automatisierungen & Szenen → Skripte** öffnen.
2. Ein neues Skript erstellen; den Menüpunkt **In YAML bearbeiten** aufrufen.
3. Den **vollständigen Inhalt** der oben verlinkten Datei einfügen. Die Datei ist eine komplette Skriptdefinition für den Editor eines einzelnen Skripts, **keine** `scripts.yaml`-Gesamtdatei.
4. Speichern und **Ausführen**. Der Test verwendet nur `openplantbook.search` und `openplantbook.get` mit `include: care`.
5. In Home Assistant die Benachrichtigung **„Mein Garten: OpenPlantbook-Prüfung“** öffnen und den dortigen Bericht als Screenshot oder Text in den Chat schicken.

Das Skript legt **keine** Pflanzen im neuen Gartenprojekt an. Die OpenPlantbook-Integration kann während der Abfragen eigene dynamische HA-Entitäten und Cache-Einträge erstellen; sie können später wieder verschwinden. Das „Zuhause“-Dashboard wird nicht verändert. Das temporäre Testskript und die Mitteilung können nach dem Test entfernt werden.

## Bericht interpretieren

- **Suche:** Anzahl der Vorschläge, die OpenPlantbook für den vollständigen botanischen Namen zurückgegeben hat.
- **Exakte Art:** Für den wissenschaftlichen Namen wurde ein gleicher PID gefunden; ähnliche Arten werden nicht als Ersatz akzeptiert.
- **Profil:** Die Detailantwort enthält den erwarteten PID.
- **Wasser, Licht, Boden, Schnitt, Düngung:** Länge des jeweiligen API-Freitextes in Zeichen.
- **0 Zeichen** kann einen fehlenden Text oder einen API-Fehler anzeigen; bei fraglichen Ergebnissen Skript-Trace prüfen.
- **13 Arten:** bewusste Teststichprobe, keine fest hinterlegte Gartenbibliothek und kein Beleg für die allgemeine Datenabdeckung.

Keine vollständigen fremden Freitexte oder Geheimnisse gelangen in den Bericht. Die Textlängen zeigen **nicht** automatisch, dass die Inhalte deutsch, korrekt oder artspezifisch sind. Dafür ist eine getrennte Qualitätsprüfung erforderlich.

Das Skript wurde als YAML geparst und seine Templates mit Testdaten geprüft. **Ein vollständiger Lauf auf dem tatsächlichen Home Assistant Green ist noch offen.**

## Quellen

- [Home-Assistant-OpenPlantbook – `get` mit `include: care`](https://github.com/Olen/home-assistant-openplantbook)
- [Home Assistant: Actions mit `response_variable`](https://www.home-assistant.io/docs/automation/action/)
- [Home Assistant: Skriptvariablen und Wiederholungen](https://www.home-assistant.io/docs/scripts/)
