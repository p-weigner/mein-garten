# Mein Garten – Konfigurationsfehler nach Austausch der JavaScript-Ressource

**Betroffen:** Erstinstallation der V1-Alpha-Karte in Home Assistant Green.  
**Fehlerbild:** Rotes Dashboard mit „Konfigurationsfehler“ nach Austausch der bisherigen Garten-JavaScript-Ressource.

## Ursache und Korrektur

Die ursprüngliche V1-Alpha-Integration verwendete denselben Custom-Element-Namen `mein-garten-card` wie die frühere Gartenkarte. Wenn beide Skripte geladen werden, kann der Browser die alte Klasse wiederverwenden; wird der bisherige Ressourcen-Eintrag dagegen entfernt, kann das bisherige Dashboard seine Karte verlieren. Fehlt außerdem die neue JS-Datei bzw. wurde sie nicht von Home Assistant registriert, erscheint ein Konfigurationsfehler.

**Ab V1 Alpha b2 sind die beiden Karten technisch getrennt:**

| | Frühere Gartenkarte | Neue V1-Alpha-Karte |
|---|---|---|
| Custom-Element | `custom:mein-garten-card` | `custom:mein-garten-v1-card` |
| JavaScript-Ressource | Bisheriger Ressourcenpfad aus der alten Garteninstallation | `/api/mein_garten/mein-garten-v1-card.js` |
| Dashboard-YAML | Alte, noch vorhandene Konfiguration | [Vollständige V1-YAML](../frontend/dashboard-mein-garten.yaml) |

**Nie eine Ressource für eine andere Version überschreiben oder ersetzen:** Den alten Ressourcen-Eintrag bei Bedarf wiederherstellen und die neue V1-Ressource **zusätzlich** hinzufügen. Alle Ressourcen gelten in Home Assistant übergreifend und können verschiedene Dashboards versorgen.

## Sichere Schritte

1. **Exakte Version prüfen:** Diese Anleitung gilt für die V1-Alpha. Die **neuen** Funktionen liegen noch im [Draft-PR #1](https://github.com/p-weigner/mein-garten/pull/1) und **nicht automatisch auf `main`**. Für einen später bewusst freigegebenen Livetest nur das **grüne Alpha-Artefakt mit übereinstimmender PR-HEAD-SHA und `ABNAHME.json`** verwenden. Davor kein beliebiges HACS-`main`-Update auslösen. [Aktuelle Vorbereitung](ALPHA_INSTALLATION.md).
2. **Neustart:** Home Assistant vollständig neu starten. Das ist nötig, damit der neue statische Frontend-Pfad registriert wird.
3. **Integration:** Unter Einstellungen → Geräte & Dienste → **Mein Garten** muss die Integration eingerichtet und geladen sein. Nur das HACS-Repository hinzuzufügen genügt nicht.
4. **Ressourcen:** Unter Einstellungen → Dashboards → Menü `⋮` → Ressourcen die neue JavaScript-Modul-Ressource **zusätzlich** eintragen: `/api/mein_garten/mein-garten-v1-card.js`. Um einen alten Frontend-Cache zu umgehen, kann die URL eine Query-Version aus dem **tatsächlich installierten Test-Commit** bekommen (z. B. `?v=<commit-kurzsha>`). Die frühere Garten-Ressource zunächst erhalten und die Seite nach dem Speichern neu laden.
5. **Nur Garten-Dashboard:** Die **vollständige** [V1-Dashboard-YAML](../frontend/dashboard-mein-garten.yaml) dort einsetzen. Sie verwendet `custom:mein-garten-v1-card`. Die Rohkonfiguration von „Zuhause“ niemals ändern.
6. **Frontend-Cache:** In der iOS-Companion-App die Ansicht neu laden (herunterziehen); falls nötig in den App-Einstellungen den Frontend-Cache zurücksetzen. Ein Test im Safari-Browser kann zwischen App-Cache und Backend unterscheiden.

## Wenn weiterhin „Konfigurationsfehler“ angezeigt wird

**A. JS-Datei prüfen:** Im Browser die lokale Home-Assistant-Adresse öffnen und `/api/mein_garten/mein-garten-v1-card.js` anhängen.

- **JavaScript-Quelltext erscheint:** Ressource wird vom Home Assistant ausgeliefert; dann sind der Ressourceneintrag, dessen Typ, Frontend-Cache oder der Dashboard-Kartentyp zu prüfen.
- **HTTP 404 / Not Found:** HACS-Update, HA-Neustart, geladene Integration und URL prüfen. Das Problem liegt dann vor dem eigentlichen Kartenrendering.
- **HTTP 500 / andere Fehlermeldung:** Home-Assistant-Protokolle kontrollieren.

**B. Exakten Frontend-Fehler ermitteln:** In Home Assistant bei der roten Konfigurationsfehler-Karte auf „Bearbeiten“ oder bei einem Browser in den Entwicklertools auf die Fehlermeldung schauen. **`Custom element doesn't exist: mein-garten-v1-card`** wäre ein Nachweis für einen fehlenden/nicht geladenen JS-Eintrag; andere Fehlermeldungen benötigen eine andere Behebung.

**C. Beide Ressourcen nicht mit demselben Elementnamen verwechseln.** Die neue JS-Datei registriert ausdrücklich `mein-garten-v1-card` und darf keine alte Karte ersetzen.

Diese Schritte ändern **keine** Daten und **keinen** Code des Hauptdashboards „Zuhause“.

Quellen: [Home Assistant – Ressourcen einbinden](https://contributors.home-assistant.io/frontend/custom-ui/resources/), [Home Assistant – Frontend-Cache](https://www.home-assistant.io/faq/browser/), [Home Assistant – eigener Karten-Typ](https://contributors.home-assistant.io/frontend/custom-ui/card/).
