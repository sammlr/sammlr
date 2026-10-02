# Phase 7 – Engineering-Hardening-Nachweis

**Stand:** 21. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Product-Contract-Verletzung:** NEIN
**Externe Closed Beta freigegeben:** NEIN

## 1. Grundlage und Scope

Geprüft wurden der aktuelle Closed-Beta-Bauplan, Source-of-Truth-Matrix,
Product Contract Freeze, Cross-Audit-Konsolidierung, CB-017-Nachweis sowie die
referenzierten S32-Security-, S34-Deployment-/Recovery-, S35-Performance- und
RC1-Releaseverträge. Die 17 abgenommenen CB-Verträge blieben eingefroren. Es
gab keine neue Produktfunktion, Produktsemantik, Migration oder Designänderung.

Die echte Bestandsdatenbank war zu Beginn V7 mit SHA-256
`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`.
Alle schreibenden Prüfungen verwendeten ausschließlich temporäre Kopien.

## 2. Hardening-Checkliste

| Bereich | Nachweis | Ergebnis |
|---|---|---|
| Authentication/Session/Cookies | S32/S35, Manipulations- und Login-Gates | grün |
| Authorization/CSRF/IDOR/Ownership | S03/S27/S29/S32/S33, CB-006/014 | grün |
| Blocks/Profile-/Albumprivacy | Privacy-Matrix und direkte Zielpfade | grün |
| Input/Validation | Mengen-/Status-/ID-Tests plus neue Größenlimits | grün |
| DB/Transaktionen/Races | Inventory-, Lifecycle-, Exactly-once-, Dedupe- und Concurrency-Suite | grün |
| Error Handling | kontrollierte 403/404/409/413/414, sanitisiertes 500-Tracking | grün |
| Configuration/Startup | Environment-/Secret-/DB-Gates, Produktions-Smoke | grün |
| Dependencies | `pip check`, Runtimeimporte, Gunicorn-Start | grün |
| Logging | pseudonyme Requestlogs, keine Query-/Body-/Token-Debugausgaben | grün |
| Performance | verbindliche S35-Baseline neu aufgebaut und gemessen | grün |
| Mobile/Browser | CB-012/017-CSS-/UI-Gates unverändert grün | grün |
| Migration/Restore | isolierte V7→V18-Probe, Backup und V7-Restore | grün |

## 3. Klassifizierte Befunde

### A – behobene Release-Blocker

1. **S35-Performancebaseline.** Collection, Album, Stickerwall, Tradebörse und
   Dealansicht liefen vor dem Fix in 5-Sekunden-Timeouts; Suche lag bei
   1.375,265 ms. Ursache waren pro Album und pro Nutzer erneut aufgebaute volle
   Inventory-Snapshots einschließlich redundanter Reservation-/Transitreads,
   N+1-Aktivitätsreads und SQLite-Read-Thrashing unter 20 Threads.
2. **S35-Testkatalog.** Die zehn isolierten `perfXX`-Alben besaßen je 100
   synthetische Slots, wurden vom realen Routecode aber als EM24-Fallback mit
   728 Slots gerendert. Der ausschließlich explizit aktivierbare
   `performance_wsgi` stellt nun den tatsächlich erzeugten 100-Slot-Katalog
   bereit. Produktive Kataloge bleiben unverändert.

Minimaler Fix:

- S19-identische Batchprojektionen für Matching und Collection;
- gebündelte Tradepool-, Nutzer-, Friendship- und Aktivitätsreads;
- requestlokaler Header-Snapshot statt zusätzlicher Headerverbindungen;
- kontrollierte Serialisierung der beiden SQLite-intensiven Read-Projektionen
  `/sammlung` und `/trades` im bestehenden Ein-Worker-Deployment.

### B – behobene Security-/Datenrobustheitsbefunde

1. **Stored Attribute Injection:** `name` und `username` wurden in den beiden
   Accountformularen ungeescaped in `value` eingesetzt. Beide Werte werden
   jetzt geescaped; ein reproduzierender Test deckt Quote-/SVG-Payloads ab.
2. **Übergroße Eingaben:** Body, Form-Memory, Form-Part-Anzahl, Querystring,
   Name, Username und Passwort besitzen nun serverseitige Grenzen. Ungültige
   Werte ändern keine Daten; übergroße Requests enden kontrolliert mit 413/414.
3. **Foreign Keys je Runtimeverbindung:** `get_db()` aktiviert jetzt
   `PRAGMA foreign_keys=ON`; ein Test belegt die aktive Einstellung.
4. **Development-Pfad:** der direkte Start bindet nur noch an `127.0.0.1` und
   startet ohne Debugger. Produktionsstart bleibt Gunicorn und fail-closed.
5. **Logging:** `TRIGGER =` und `FINAL URL:` wurden entfernt. Damit gelangen
   Query-/Nutzerwerte nicht mehr unnötig in stdout.
6. **Response-Härtung:** `nosniff`, `DENY`-Framing und eine restriktive
   Referrer-Policy gelten generell; HSTS gilt im Produktionsmodus.
7. **Syntaxrobustheit:** die zwei bekannten ungültigen `\d`-Escape-Sequenzen
   im eingebetteten JavaScript sind korrigiert; `py_compile -Werror` ist grün.

### C – bewusst nicht vorgezogene Punkte

- Abhängigkeiten sind vollständig (`pip check`: keine Defekte), aber
  `requirements.txt` ist noch nicht als vollständig gepinnter Lock-/Supply-
  Chain-Workflow ausgeprägt. Das verlangt eine eigene Deploymententscheidung.
- Eine CSP würde wegen der bestehenden Inline-Skripte eine breite UI-/Asset-
  Umstellung erfordern und wurde nicht beiläufig eingeführt.
- Die bekannten `ResourceWarning`-Hinweise älterer Tests betreffen überwiegend
  testseitig nicht explizit geschlossene SQLite-Verbindungen. Sie erzeugen in
  den beiden Vollregressionen keine Fehler oder Skips, bleiben aber technische
  Testschuld.
- Juristische Endfassung und realer Betreiber-Backupdrill bleiben spätere
  Freigabegates und werden nicht als Codeänderung vorgezogen.

### D – kein Handlungsbedarf

- Debugrouten sind nur in explizitem Development/Testing registriert,
  produktiv nicht vorhanden und für POST zusätzlich CSRF-geschützt.
- Nicht produktiv importierte Archiv-/Backupquellen sind kein Runtimepfad.
- Der große historische `webapp.py`-/CSS-Zuschnitt ist kein Phase-7-Refactor.

## 4. Performance-Nachweis

Messvertrag: 100 Nutzer, 10 Alben, 100.000 Stickerzeilen, 2.000 Trades,
5.000 Notifications, 1.000 Freundschaften, Gunicorn mit einem Worker und 20
Threads, 20 parallele Requests. Grenze: P95 unter 500 ms und 0 Fehler.

| Pfad | Vorher P95 / Fehler | Final P95 / Fehler |
|---|---:|---:|
| Login | 9,955 ms / 0 | 8,911 ms / 0 |
| Home | 110,025 ms / 0 | 86,102 ms / 0 |
| Sammlung | 5.001,417 ms / 20 | 69,942 ms / 0 |
| Album | 5.001,940 ms / 20 | 390,211 ms / 0 |
| Stickerwall | 5.003,165 ms / 20 | 439,025 ms / 0 |
| Suche | 1.375,265 ms / 0 | 126,062 ms / 0 |
| Tauschbörse | 5.002,073 ms / 20 | 78,670 ms / 0 |
| Deal | 5.079,917 ms / 20 | 128,381 ms / 0 |
| Notifications | 93,655 ms / 0 | 29,173 ms / 0 |
| Profil | 159,738 ms / 0 | 176,209 ms / 0 |

Ergebnis: `10/10 PASS`, Fehlerquote `0 %`. Finales Artefakt:
`/private/tmp/sammlr-phase7.jCZQLR/performance-after.json`.

## 5. Tests und technische Gates

### Gezielte und kombinierte Suiten

- Phase-7-Reproduktion/Regression: 6 Tests, grün.
- Security/Privacy: 111 Tests, grün.
- Trade/Concurrency/Transaction: 270 Tests, grün.
- Feed/Profile/Collection/Notification: 138 Tests, grün.
- Mobile/UI: 43 Tests, grün.
- abschließender CB-017-/Phase-7-Kontrolllauf: 8 Tests, grün.

### Vollregression

- Lauf 1: `712/712`, 0 Fehler, 0 Skips, 7,692 s.
- Lauf 2: `712/712`, 0 Fehler, 0 Skips, 7,693 s.

### Syntax, Dependencies und HTTP

- aktive App-, Service-, Datenbank-, Script- und Testquellen:
  `py_compile -Werror` grün;
- `pip check`: `No broken requirements found`;
- isolierter Produktions-Gunicorn-Start: erfolgreich;
- `/healthz`: 200, `/login`: 200;
- unauthentifizierte Kernpfade `/`, `/sammlung`, `/trades`, `/notifications`,
  `/profil`: jeweils kontrollierter 302 zum Login;
- authentifizierte Kernpfade: S35 und kombinierte HTTP-Suiten jeweils 200.

## 6. Migration, Restore und Bestandsdatenbank

Auf einer neuen Kopie der echten V7-Datenbank:

- Backup vor Migration: V7;
- Migrationen V8–V18: erfolgreich;
- Ergebnis: V18, `integrity_check=ok`, `foreign_key_check` leer;
- geschützte Kernzählungen vorher/nachher unverändert:
  Users 4, Sticker 1.971, User-Alben 8, Trade-Requests 18,
  Notifications 89, Legacy-Trophyzeilen 61;
- Restore des V7-Backups in eine neue Datei: V7, Integrity/FK grün;
- Restore-SHA entspricht exakt dem Backup-SHA
  `ac58159ce9b90cbd384430d3e6771954531562f383e12b213c10b18609ea34d5`.

Die echte Datenbank wurde weder migriert noch beschrieben. Abschluss:

- Schema: V7;
- `integrity_check`: `ok`;
- `foreign_key_check`: leer;
- SHA-256 vorher/nachher:
  `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`.

## 7. Geänderte Dateien

- `App/webapp.py`
- `App/services/inventory.py`
- `App/services/community.py`
- `App/services/album_privacy.py`
- `App/performance_wsgi.py`
- `tests/test_phase7_engineering_hardening.py`
- `Dokumentation/Post-RC/00-master-plan.md`
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`
- `Dokumentation/Post-RC/06-engineering-hardening.md`
- `Dokumentation/Post-RC/07-simulation.md`
- dieser Report

Es wurde keine Migration ergänzt und keine fremde Working-Tree-Änderung
zurückgesetzt. `git diff --check` ist grün. Es gab keinen Commit und keinen
Push.

## 8. Abschlussbewertung

Phase 7 ist abgeschlossen und technisch abgenommen. Alle A- und B-Befunde sind
minimal behoben; C-Punkte sind transparent vertagt; D-Punkte blieben
unangetastet. Es besteht keine Product-Contract-Verletzung.

Nächster zulässiger Schritt ist **Phase 8 – Realistic Simulation**. Externe
Closed-Beta-Nutzer bleiben bis zum erfolgreichen Phase-9-Gate ausdrücklich
nicht freigegeben.
