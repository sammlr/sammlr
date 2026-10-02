# Phase 9 – finales Closed-Beta-Gate

**Stand:** 21. August 2026
**Entscheidung:** CLOSED BETA: NICHT FREIGEGEBEN
**P1:** 17/17 abgeschlossen
**Technische Produktgates:** GRÜN
**Offene Release-Blocker:** 1
**Migration der echten DB:** NEIN

## 1. Finale Gate-Matrix

| Gate | Voraussetzung | Benötigter Nachweis | Vorhandener Nachweis | Erneut ausgeführt | Ergebnis | Release-Blocker |
|---|---|---|---|---|---|---|
| Product Contract | CB-001–017, Freeze | 17/17, kein offenes P1, kein Scope Creep | CB-Reports, Bauplan, CB-017 | NEIN; kein Produktdrift | GRÜN | NEIN |
| Engineering Hardening | Phase 7 | Security, Runtime, Dependencies, Logging, Performance, Recovery | Phase-7-Report | teilweise: 28er Final-Suite, Compile, Dependencies, Startup | GRÜN | NEIN |
| Realistic Simulation | Phase 8 | Population, Journeys, Chaos, Exactly-once, Checkpoints | Phase-8-Report, reproduzierbarer Test | JA: Phase-8-Test 1/1 | GRÜN | NEIN |
| Security / Privacy | CB-006 und fremde Verbraucher | Auth, CSRF, Ownership, Privacy, Blocks, IDOR/XSS/Secrets | CB-017 92/92, Phase 7 111/111, Phase 8 359/359 | NEIN; kein Appdrift | GRÜN | NEIN |
| Daten / Migration | S34, CB-001–005/017 | V7→V18 auf Kopie, kein Backfill, Integrity/FK, Restore | CB-017 und Phase 7; S34/S38 Tests | JA: S34/S38 Final-Suite und V7-read-only-Check | GRÜN | NEIN |
| Core Journeys | integrierter P1-Stand | Sammlung bis Karriere einschließlich Tradeproblem | CB-017 Safari-/Tradeflow, Phase-8-Journeys | JA: Phase-8-Test 1/1 | GRÜN | NEIN |
| Mobile / Browser | CB-001–016 integriert | echter Safari-Smoke 390 px, keine Overflows, Kernaktionen | CB-017-Report, CB-012-Report | NEIN; kein App-/CSS-Drift | GRÜN | NEIN |
| Performance | S35 | 10 Kernpfade P95 < 500 ms, 0 Fehler | Phase 8: 10/10; Stickerwall 429,284 ms | NEIN; aktueller Code bereits gemessen | GRÜN | NEIN |
| Legacy Cutover | CB-016 | keine operative Parallelwahrheit/Legacy-Writes | CB-016, CB-017, Phase 8 | JA innerhalb Phase-8-Wiederholung | GRÜN | NEIN |
| Technische Release Operations | S34/S38 | Config fail-closed, Backup/Migration/Restore-Vertrag, Health/HTTP | S34/Phase 7/CB-017 | JA: 28/28 und Gunicorn-Smoke | GRÜN | NEIN |
| Rechtliche Freigabe | Phase-7-Restpunkt, RC1-Checkliste | juristische Endprüfung und finale Betreiberangaben | ausdrücklich als offen dokumentiert | NEIN; extern erforderlich | ROT | **JA** |
| Betreiber-Recoverydrill | Phase-7-/Phase-8-Restpunkt, S34 | realer, dokumentierter Backup-/Restore-Drill im Betreiberumfeld | S34-Betreiberdrill vom 21. August 2026 | JA: Backup → Restore V7 → Upgrade V18 → Restore V7 | GRÜN | NEIN |

## 2. Product Contract und P1

CB-001 bis CB-017 sind 17/17 abgeschlossen. CB-017 bestätigt alle sechs
Bauplan-Gates, keinen offenen P0, keine ungeklärte P1-Abweichung und keine
Product-Contract-Verletzung. Phase 7 und Phase 8 veränderten keine
Produktsemantik. Der Phase-9-Working-Tree-Abgleich fand seit dem gültigen
Safari- und Performance-Nachweis ausschließlich Test- und
Dokumentationsänderungen; App-, CSS-, Runtime- und Migrationsstand drifteten
nicht.

Die ausdrücklich ausgeschlossenen Post-Beta-Themen – unter anderem
Cross-Album-SmartTrades, Mehrfachexemplare, Push, historische Read-only-Ansicht,
Rankings und komplexe Reminder-/Disputesysteme – wurden nicht vorgezogen.

## 3. Security und Privacy

Die gültigen Nachweise umfassen Authentication, Sessionrotation, CSRF,
Authorization, Ownership, direkte und manipulierte IDs, ProfilePrivacy,
Albumprivacy, gegenseitige Freundschaft, Blocks, sichere Deep Links, Stored-XSS
und Secret-/Log-Redaction. CB-017 bestand 92/92, Phase 7 bestand 111/111 und die
Phase-8-Quersuite 359/359. Der finale S34/S38-/Hardening-Lauf bestätigte
fail-closed Produktionskonfiguration, sanitisiertes Logging, sichere Header,
Debug-Abwesenheit in Production und read-only Recovery erneut.

Ergebnis: kein Privacy-/Security-Leak und kein technischer Release-Blocker.

## 4. Daten, Migration und Restore

Die vorhandenen realitätsnahen Nachweise belegen:

- Predeploy-Backup einer V7-Kopie vor jeder Migration;
- kontrolliertes V7→V18-Upgrade ohne impliziten historischen Backfill;
- unveränderte geschützte Kernzählungen;
- `integrity_check = ok` und leeren `foreign_key_check`;
- Restore in eine neue Datei mit identischem Backup-/Restore-Hash;
- erfolgreichen read-only App-/HTTP-Smoke gegen die Recoverydatei;
- frische V0→V18-Migration und leeren Repeat-up.

Phase 9 wiederholte die 13 S34- und 6 S38-Tests vollständig. Ergänzend führte
ein Operator am 21. August 2026 den verpflichtenden realen Drill aus: Online-
Backup der aktuellen V7-Bestands-DB über die SQLite Backup API, erster
isolierter V7-Restore, Upgrade der Restore-Kopie auf V18 und erneuter Restore
des Originalbackups auf V7. Integrity/FK, Datenzählungen, Dateirechte,
Gunicorn-Starts und zentrale HTTP-/Read-Smokes waren grün. Das gesamte
Operatorfenster betrug 4 Minuten 44 Sekunden und lag deutlich innerhalb des
S34-RTO. Der vollständige Nachweis steht in
`S34-backup-restore-drill-report.md`; der Betreiber-Recoveryblocker ist damit
geschlossen.

Die echte Bestandsdatenbank wurde ausschließlich read-only geprüft:

- Schema vorher/nachher: V7;
- SHA-256 vorher/nachher:
  `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`;
- `integrity_check = ok`;
- `foreign_key_check` leer.

Sie wurde nicht migriert, restauriert oder als Test-/Simulationsziel verwendet.

## 5. Core Journeys, Mobile und Safari

CB-017 belegt den echten Safari-Smoke mit 390 × 792 CSS-Pixeln und DPR 2. Alle
Kernseiten besaßen `document.scrollWidth = window.innerWidth = 390`; Bottom Nav,
Glocke und Tauschen waren erreichbar. Feedkarte, Empty State, Deep Link,
CSRF-Quantity-Fetch und vollständiger Zwei-Nutzer-SmartTrade wurden real im
Browser geprüft.

Phase 8 ergänzte 31 Nutzer, 56 Albumzuordnungen, mehr als 1.700 Stickerzeilen,
zwei historische Abschlüsse, zwei regulär abgeschlossene Trades, einen
terminalen Problemtrade, konkurrierende Nachfrage, Retention, Feedprivacy und
Karriereprojektion in verbundenen Journeys. Vier Checkpoints waren grün.

Seit diesen Nachweisen wurden weder `App/webapp.py` noch
`App/static/style.css`, Fachservices, Migrationen oder Runtimekonfiguration für
Phase 9 verändert. Gemäß Phase-9-Vertrag waren Safari und die Volljourneys
daher nicht erneut manuell auszuführen. Der reproduzierbare Phase-8-Test lief
erneut 1/1 grün.

## 6. Performance

Der aktuelle Phase-8-Nachweis mit Gunicorn, einem Worker, 20 Threads, 20
parallelen Requests, 100 Nutzern und 100.000 Stickerzeilen bestand alle 10
Pfade unter 500 ms und ohne Fehler. Stickerwall P95 war 429,284 ms; der
langsamste Pfad war Album mit 469,071 ms. Seit der Messung gab es keinen
relevanten Code- oder Konfigurationsdrift. Der Gatevertrag verlangte deshalb
keine erneute Lastmessung und es wurde keine unnötige Optimierung vorgenommen.

Der historische RC1-Known-Issue-Eintrag zur alten S35-Baseline ist durch den
neueren Phase-7- und Phase-8-Nachweis fachlich geschlossen, bleibt aber als
historische Evidenz unverändert erhalten.

## 7. Legacy

CB-016 und die integrierten Folgeläufe bestätigen, dass Notifications,
`user_activity`, dynamische Completion-/Trophy-Berechnung und operatives Home
keine parallelen Produktwahrheiten mehr bilden. Phase 8 erzeugte alle neun
zulässigen Notification-Typen, keine unerlaubten Typen und keinen neuen
`legacy`-Write. Historische Legacy-Zeilen und sichere Redirect-/Read-
Kompatibilität dürfen bestehen bleiben. Ergebnis: grün.

## 8. Release Operations und Deployment

Technisch vorhanden und erneut bestätigt sind:

- der einzige Gunicorn-Production-Einstieg mit einem Worker;
- Pflichtkonfiguration `SAMMLR_ENV`, externes Secret, Port und exakter
  Produktionsdatenbankpfad;
- fail-closed Start bei fehlendem Secret, falschem Pfad oder falscher Version;
- separater Predeploy-Prozess mit Backup vor Migration;
- restriktive Backupdateien, SHA-256 und 30-Tage-Retention;
- Healthcheck, Request-ID, redigierte JSON-Logs und sanitisiertes
  Fehlertracking;
- S34-Deployment-, Recovery- und Incident-Checklisten.

Der finale lokale Gunicorn-Smoke verwendete eine isolierte V18-Datei:

- `/healthz`: 200;
- `/login`: 200;
- `/static/style.css`: 200;
- `/`, `/sammlung`, `/trades`, `/notifications`, `/profil`: kontrolliert 302
  zu `/login`.

Der reale S34-Betreiberdrill ist nun ebenfalls grün dokumentiert. Backup und
Restores lagen in geschützten Verzeichnissen außerhalb des Repositories; die
Dateien hatten Modus `0600`, die Verzeichnisse `0700`. Die echte Bestands-DB
blieb bei V7 und behielt vor/nach dem Drill exakt den bestätigten SHA-256.

Nicht als grün ausgegeben wird weiterhin die fachfremde juristische Freigabe:
Die S36-Texte sind funktionale Entwürfe. Juristische Endprüfung und finale
Betreiberangaben fehlen.

Ein spezielles Adminsystem, CMS oder automatisiertes Einladungssystem ist im
Closed-Beta-Vertrag nicht vorgeschrieben und wird nicht als künstlicher Blocker
erfunden. Das reale Deployment und seine unmittelbare S34-Deploymentcheckliste
wären nach einem späteren GO reine Durchführung vor der ersten Einladung;
aktuell wird wegen des verbleibenden juristischen Blockers nicht deployt.

## 9. Finale technische Tests

Phase 9 führte gezielt die seit den letzten Vollnachweisen relevanten Gates aus:

- CB-017-CSS-Vertrag: 2/2;
- Phase-7-Hardening: 6/6;
- Phase-8-Simulation: 1/1;
- S34 Deployment/Recovery/Observability: 13/13;
- S38 Release Candidate: 6/6;
- zusammen: **28/28**, 0 Fehler, 0 Skips.

Die Phase-8-Vollregressionen mit **713/713 zweimal**, die Security-/Privacy-
und 359er Quersuite bleiben gültig. Da danach kein Produkt-, CSS-, Runtime-
oder Migrationsdrift entstand, verlangte der primäre Phase-9-Vertrag keine
dritte Vollregression.

Weitere finale Ergebnisse:

- `py_compile -Werror`: grün;
- `pip check`: `No broken requirements found`;
- `git diff --check`: ohne Befund;
- Startup-/Health-/zentrale unauthentifizierte HTTP-Smokes: grün;
- echte V7-DB: Hash, Integrity und FK unverändert grün.

## 10. Akzeptierte Restrisiken

Folgende dokumentierte Punkte blockieren die Closed Beta technisch nicht:

- nicht vollständig gepinnter Supply-Chain-/Lockfile-Workflow;
- keine CSP wegen bestehender Inline-Skripte;
- ältere testseitige `ResourceWarning`-Hinweise;
- nicht importierte Archivquellen mit historischen Syntaxartefakten;
- große historisch gewachsene `webapp.py`-/CSS-Dateien;
- lokale Simulation ersetzt keine mehrtägige reale Nutzung oder Netzlatenz;
- alle ausdrücklich vertagten P2-/P3-/Future-Produkte.

Sie sind weder P0 noch ungeklärte P1-Abweichungen und beeinträchtigen keinen
belegten Kernworkflow.

## 11. Offener Release-Blocker und Entscheidung

### Blocker 1 – juristische Endprüfung

Erforderlich sind dokumentierte juristische Freigabe der funktionalen
Datenschutztexte sowie final bestätigte Betreiberangaben. Diese fachfremde
Freigabe kann nicht aus grünen Softwaretests abgeleitet werden.

### Geschlossen – realer Betreiber-Backup-/Restore-Drill

Der Operator-Drill vom 21. August 2026 belegt Backup-Pfad, SHA-256, Version,
Integrity/FK, geschützte Dateirechte, zwei Restoreziele, V7→V18-Upgrade,
Health-/Read-Smokes, Dauer und Ergebnis. Die echte Bestands-DB wurde nicht
überschrieben oder migriert. Dieser frühere Release-Blocker ist geschlossen.

## Finale Entscheidung

**CLOSED BETA: NICHT FREIGEGEBEN.**

Externe Closed-Beta-Nutzer dürfen noch nicht eingeladen werden. Es besteht kein
technischer Produktblocker; die Entscheidung folgt ausschließlich dem einen
offenen Compliance-Gate.

Nächster notwendiger Schritt:

1. juristische Texte und Betreiberangaben freigeben lassen;
2. danach nur das finale Gate erneut bewerten und bei dokumentierter
   juristischer Freigabe eine neue ausdrückliche Go-/No-Go-Entscheidung
   dokumentieren.

Kein Commit und kein Push wurden ausgeführt.
