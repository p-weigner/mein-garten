# Mein Garten V1 – technischer Alpha-Test (noch nicht vollständig)

Diese Anleitung ist für einen **bewussten Test der neuen Gartenverwaltung** gedacht. Die frühere Garteninstallation kann vollständig ersetzt werden. Die bestehende Home-Assistant-Oberfläche **„Zuhause“ bleibt unangetastet**.

## Was im Alpha-Paket funktioniert

- Startseite mit Pflanzenzahl, Aufgaben und Bereichen.
- Dynamische Pflanzensuche nach deutschen oder botanischen Namen über iNaturalist und Wikidata. Bekannte Arten werden taxonomisch geprüft; unsichere Vorschläge sind markiert.
- Neue Pflanzen ohne feste Artenliste hinzufügen, umbenennen, bearbeiten, Notizen erfassen und löschen.
- Gartenbereiche anlegen, umbenennen und löschen. Die Pflanzen bleiben bei Bereichslöschung erhalten.
- Manuelle Aufgaben mit Fälligkeit anlegen, erledigen, wieder öffnen und löschen.
- Aufgabenübersicht unter „Kalender“, einfache Erledigungshistorie und Synchronisierung über Home Assistant.
- Lokale Daten in einem neuen Home-Assistant-Store `.storage/mein_garten_v1.data`.
- Die JavaScript-Karte wird **von der Integration selbst** unter `/api/mein_garten/mein-garten-v1-card.js` ausgeliefert; kein separater `www`-Upload erforderlich.

## Was NOCH NICHT funktioniert

- Automatische deutsche Pflegehinweise in der tatsächlichen Gartenoberfläche.
- Automatisch erzeugte artspezifische und saisonale Pflegeaufgaben.
- Pflege-Wetterregeln, Frostwarnungen und Freitagspush.
- Fotos und automatische Pflanzenbestimmung.
- Kalender-Entität in der allgemeinen HA-Kalenderansicht.
- Vollständige Prüfung unter dem aktuellen Home Assistant 2026.10 auf dem echten Green.

Die Quellen- und Übersetzungsmodule wurden separat entwickelt und getestet; sie sind **nicht** als voll funktionsfähige Pflegeautomatik freigegeben. Es entstehen keine Pflichtabonnements. Die Pflanzensuche benötigt Internetzugang, sonst ist die manuelle Erfassung weiterhin möglich.

## Einmalige Einrichtung der Alpha-Vorversion

**Vor jedem Test:** Ein aktuelles Home-Assistant-Backup erstellen. Das alte „Mein Garten“ darf überschrieben werden; das Dashboard „Zuhause“ und die übrigen Integrationen bleiben unangetastet.

### Variante A – HACS

1. In HACS das Repository `https://github.com/p-weigner/mein-garten` als **benutzerdefiniertes Repository, Kategorie Integration** hinzufügen.
2. **Mein Garten** installieren bzw. auf mindestens Version `1.0.0b2` aktualisieren und Home Assistant vollständig neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** die Integration **Mein Garten** einmalig einrichten. Wenn bereits eine alte „Mein Garten“-Integration existiert, deren Status prüfen, bevor du sie erneut hinzufügst.
4. Unter **Einstellungen → Dashboards → Ressourcen** (gegebenenfalls über das Drei-Punkte-Menü) die neue JavaScript-Ressource `/api/mein_garten/mein-garten-v1-card.js?v=1.0.0b2` vom Typ **JavaScript-Modul zusätzlich** hinzufügen. Eine frühere Gartenressource nicht ersetzen; die neue Karte besitzt einen eigenen Namen.
5. **Ein separates Dashboard** „Mein Garten“ erstellen und dessen Rohkonfiguration durch den vollständigen Inhalt aus `frontend/dashboard-mein-garten.yaml` ersetzen. Die V1-YAML verwendet `custom:mein-garten-v1-card`. **Nicht die Rohkonfiguration von „Zuhause“ bearbeiten.**

### Variante B – Manuell

Die vollständige Ordnerstruktur `custom_components/mein_garten` des Pakets nach `/config/custom_components/mein_garten` kopieren, Home Assistant neu starten und mit Schritt 3 der HACS-Variante fortfahren. Es sind keine Teiländerungen an YAML-Dateien vorgesehen.

## Was beim Test beobachtet werden sollte

- Lässt sich die Integration ohne Einrichtungsfehler laden?
- Wird die Gartenkarte mit allen vier Reitern angezeigt?
- Funktioniert „Bauernhortensie“ als dynamischer Suchbegriff?
- Bleibt eine angelegte Pflanze nach dem Neustart erhalten?
- Werden neue Gartenbereiche auf dem iPhone und auf einem zweiten Gerät synchron dargestellt?
- Was melden die Protokolle bei einer fehlerhaften API-Verbindung?
- Wird beim Löschen eines Bereichs **keine** Pflanze gelöscht?

Wenn eine Installation oder Abfrage fehlschlägt, Fehlertext/Protokollauszug mitteilen. **Keine API-Schlüssel oder private Daten in GitHub-Issues hochladen.**

## Aktueller Qualitätsnachweis

Die Module wurden mit Python- und Node-Tests in GitHub Actions überprüft. Ein echter Home-Assistant-Green-Lauf fehlt noch. Das Alpha-Paket ist deshalb **kein vollständiges V1-Release**.

Für die neue Version wurden keine Dateien des vorhandenen Dashboards „Zuhause“ geändert. Alle Eingriffe erfolgen ausschließlich im eigenständigen Gartenbereich.

**Hinweis:** Beim Öffnen der Pflanzensuche werden die eingegebenen Suchbegriffe an iNaturalist und Wikidata übermittelt. Andere persönliche Gartendaten werden von dieser Suchfunktion nicht übertragen.

### Konfigurationsfehler nach Ressourcenwechsel

Falls nach der Änderung „Konfigurationsfehler“ erscheint, prüfe die [vollständige Anleitung zur Karten- und Ressourcen-Trennung](KONFIGURATIONSFEHLER_LOVELACE.md). Die alte Karte und die neue V1 müssen **verschiedene Elementnamen** und **eigene JavaScript-Ressourcen** verwenden. Im iPhone kann zusätzlich der Frontend-Cache veraltet sein.
