# Phase 3 – Automatische deutsche Übersetzung

**Stand:** 29. Oktober 2026  
**Echter anonymisierter Live-Test:** https://github.com/p-weigner/mein-garten/actions/runs/40872712042  
**Implementierter Adapter:** [tools/mymemory.py](../tools/mymemory.py)  
**Technische Tests:** 76 Tests im Live-Workflow; beim Aufbau des Garten-Backends wurde der Gesamtumfang weiter erhöht.

## Technisches Ergebnis

MyMemory wurde ohne Registrierung, ohne API-Schlüssel und ohne kostenpflichtige Zusatzdienste mit **fünf selbst verfassten englischen Gartenpflege-Sätzen** live abgefragt.

| Feld | Original (Testtext) | Tatsächliche deutsche API-Antwort | Einschätzung |
|---|---|---|---|
| Wasser | Water moderately and avoid waterlogging. | Gießen Sie mäßig und vermeiden Sie Staunässe. | Sinn korrekt |
| Standort | The plant prefers partial shade and moist, well-drained soil. | Die Pflanze bevorzugt Halbschatten und feuchte, gut durchlässige Erde. | Sinn korrekt |
| Rückschnitt | Do not prune in autumn because the flower buds develop on older wood. | Im Herbst nicht beschneiden, da sich die Blütenknospen auf älterem Holz entwickeln. | Verneinung und Grund erhalten |
| Düngung | Apply a little fertilizer in spring, but do not overfertilize. | Im Frühjahr etwas Dünger auftragen, aber nicht überdüngen. | Sinn korrekt; etwas holprig |
| Frost | Protect the roots from severe frost and do not water frozen soil. | Schützen Sie die Wurzeln vor starkem Frost und gießen Sie keine gefrorenen Böden. | Sinn erkennbar, stilistisch unnatürlich |

**Ergebnis:** 5/5 API-Antworten erhalten; bei den fünf Beispielen wurde der wesentliche Sinn übertragen, einschließlich wichtiger Verneinungen. **Dies belegt keine zuverlässige Übersetzung sämtlicher botanischer Fachtexte.** Maschinenübersetzung ist keine gärtnerische Fachprüfung.

## Kosten-/Limitbedingungen

Quelle: https://mymemory.translated.net/doc/usagelimits.php und https://mymemory.translated.net/doc/spec.php

- Anonymous: **5.000 Zeichen pro Tag**, kein Konto notwendig.
- Einzelne Anfragen: **höchstens 500 UTF-8-Byte**.
- Das Modul `tools/mymemory.py` zerlegt längere Felder vor dem Senden und reserviert das eigene Tagesbudget lokal.
- Anbieter-Rate-Limits können trotzdem greifen, weil Limits nicht nur von unserem lokalen Budget abhängen.
- **Kein automatischer Wechsel zu einem kostenpflichtigen Tarif.**
- Nur einzelne zulässige Fachtextabschnitte übertragen – nie private Fotos, Gartenstandorte, Nutzernotizen oder API-Schlüssel.
- Die Nutzungsbedingungen gestatten automatisierte API-Aufrufe innerhalb der Grenzen: https://mymemory.translated.net/terms-and-conditions

### Alternative

Microsoft Translator **F0** stellt 2 Millionen kostenlose Zeichen je Abrechnungsmonat bereit; es ist ein bewusst eingerichtetes Azure-Konto erforderlich. Nach Erreichen des F0-Limits stoppt der Übersetzungsdienst statt automatisch kostenpflichtig fortzufahren. Quellen: https://azure.microsoft.com/de-de/pricing/details/translator/ und https://www.microsoft.com/en-us/translator/business/faq/ .

Der Azure-Adapter `tools/anbieter.py` ist noch **nicht mit echtem Azure-Zugang getestet**. Er bleibt optional, bis dieser Weg ausdrücklich gewünscht wird.

## Umgang mit fremden Pflegeinformationen

- Eine API-Auskunft zur Nutzbarkeit ist **nicht automatisch** eine Lizenz zum Neuveröffentlichen, dauerhaften Kopieren und Weiterübersetzen.
- Die Home-Assistant-OpenPlantbook-Integration ist GPL-3.0, aber daraus kann **keine Lizenz der API-Pflanzenfreitexte** abgeleitet werden.
- Eine ausdrückliche allgemeine Nachnutzungslizenz für diese Pflegefreitexte konnte bis hierher **nicht verifiziert** werden. Deshalb sollen keine vollständigen OpenPlantbook-Quelltexte in das öffentliche GitHub-Repo, GitHub-Actions-Artefakte oder fremde öffentliche Dienste ohne Rechteprüfung aufgenommen werden.
- Permapeople stellt Daten unter CC BY-SA 4.0 bereit; Attribution und weitere Lizenzpflichten sind für die Verwendung einzuhalten.
- Der derzeitige Live-Test überträgt nur eigens für dieses Projekt verfasste Beispielsätze. Es wurden keine fremden vollständigen Pflanzenpflegehinweise an den Übersetzungsdienst geschickt.

## Festgelegte technische Regeln

1. MyMemory ist der erste **kostenfreie Pilot-Anbieter**, kein Garantieversprechen für jede Pflegeart.
2. Übersetzung nur bei neuem oder geändertem zulässigem Quelltext; sonst lokalen Übersetzungscache nutzen.
3. Originalsprache, Quelle, Zeitstempel und Übersetzungsstatus getrennt dokumentieren.
4. Englische Originaltexte werden nicht als deutsche Pflegeanleitungen ausgegeben.
5. Fehlende Übersetzung bleibt als fehlend markiert.
6. **Keine automatisch erzeugten Rückschnitt- oder Düngearbeiten allein aufgrund übersetzter Freitexte.**
7. Vor produktiver Integration Nutzungsrechte, langfristige Zuverlässigkeit sowie echte Fachtextqualität weiter prüfen.
