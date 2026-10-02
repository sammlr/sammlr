# Sprintbericht S33 – HTTP-Methoden, Debugrouten und additive Integrität

Stand: 2026-08-09

## Vorimplementierungsdesign

S33 härtet ausschließlich vorhandene HTTP-Mutationsverträge, Debugzugriffe und
bereits verbindliche Dateninvarianten. Es entstehen keine neue Fachfunktion,
kein neuer Produktzustand und kein Scope aus S34.

### Inventar der bisherigen mutierenden GET-Verträge

| Bisheriger Pfad | Bisherige Mutation | S33-Vertrag |
|---|---|---|
| `/debug-seed-now` | ersetzt die gewählte Development-/Testdatenbank | nur POST, CSRF, nur Development/Testing |
| `/logout` | löscht die Session | nur POST, CSRF |
| `/favorit/toggle/<album_id>` | setzt oder entfernt Favoritenalbum | nur POST, CSRF |
| `/favorit/setzen/<album_id>` | setzt Favoritenalbum | nur POST, CSRF |
| `/alben/hinzufuegen/<album_id>` | erzeugt Albumzuordnung | nur POST, CSRF |
| `/add/<album_id>/<code>` | erhöht Stickerbestand | nur POST, CSRF |
| `/remove/<album_id>/<code>` | vermindert Stickerbestand | nur POST, CSRF |
| `/undo` | kehrt letzte Bestandsmutation um | nur POST, CSRF |
| `/notifications/<id>/open` | markiert gelesen und öffnet kanonisches Ziel | nur POST, CSRF |
| `/notifications/<id>/read` | markiert gelesen | nur POST, CSRF |
| `/trades/<id>/accept` | historischer Mutationsalias | GET 405; bestehender kanonischer POST bleibt `/trade/<id>/accept` |
| `/trades/<id>/decline` | historischer Mutationsalias | GET 405; bestehender kanonischer POST bleibt `/trade/<id>/decline` |
| `/trades/<id>/confirm` | historischer Mutationsalias | GET 405; bestehender kanonischer POST bleibt `/trade/<id>/confirm` |
| `/trades/<id>/cancel` | historischer Mutationsalias | GET 405; bestehender kanonischer POST bleibt `/trade/<id>/fail` |

Alle internen Aktionslinks werden durch POST-Formulare ersetzt. Objektprüfung,
Fachservice und Redirectziel bleiben jeweils unverändert. Da Flask für einen
registrierten POST-only-Pfad einen GET nicht zur Route dispatcht, liefern die
alten direkten GET-Aufrufe HTTP 405 ohne Mutation.

### Trophy-GET-Schreibpfade

Vor S33 existieren genau zwei persistente Trophy-Schreibpfade über GET:

- `/album/<album_id>/trophaeen` synchronisiert erreichte Albumtrophäen in
  `unlocked_trophies`.
- `/trophaeen` synchronisiert erreichte globale Trophäen in
  `unlocked_trophies`.

Diese Lazy-Schreibarbeit wird entfernt. Die vorhandenen Fachmutationen decken
die Freischaltung bereits ab:

- Einzel-Add/Remove, Mengenregler, Detailmenge, Batch und Papiertransfer prüfen
  nach erfolgreicher Bestandsmutation Albumtrophäen und rufen über die
  Popup-Queue zusätzlich den globalen Trophy-Hook auf.
- Legacy-Tradeabschluss, Empfang und Teilempfang rufen die bestehenden
  Abschluss-/Trophy-Hooks für beide Seiten auf.
- Wiederholungen bleiben über den bestehenden Unique-Vertrag von
  `unlocked_trophies` idempotent.

Es wird kein Trophy-Sync-POST und keine zweite Trophy-Engine eingeführt.

### Explizit freigegebene GET-Ausnahmen

Die persistente GET-Invariante besitzt ausschließlich diese drei verbindlich
freigegebenen Ausnahmen:

- CSRF-Token-Erzeugung als technischer Sessionzustand,
- `session.pop` für bereits erzeugte, rein temporäre Trophy-Popups,
- die bestehende deduplizierte Lazy-Fristnotification-Projektion an den in S23
  freigegebenen read-only Einstiegen.

Keine dieser Ausnahmen verändert Inventory, Tradezustand, Notification-
Read-State, Berechtigungen oder andere persistente Fachwerte. Weitere
Ausnahmen wurden nicht eingeführt.

### Debugvertrag

`/debug-db` wird nur bei explizitem `SAMMLR_ENV=development` oder `testing` als
read-only Route registriert. `/debug-seed-now` wird in denselben Umgebungen als
CSRF-geschützte POST-Route registriert. In Produktion sind beide Routen nicht
registriert und liefern 404, ohne ihre Existenz zu bestätigen. Der bisherige
Query-Key ist keine Sicherheitsgrenze mehr.

### Geplante V0011-Objekte

V0011 rekonstruiert keine Tabelle und kopiert oder transformiert keine Daten.

| Objekt | Tabelle | Bestehende Invariante | Ereignis / Fehlerfall |
|---|---|---|---|
| `idx_s33_stickers_identity` | `stickers` | S08-Betrachtungseinheit `(user, album, code)` ist eindeutig | zweiter identischer Datensatz → Unique-Fehler |
| `s33_stickers_validate_insert/update` | `stickers` | S08 I-01/I-10: Zeile hat positive `quantity`, `duplicates = quantity - 1`, gültigen Nutzer und Album | INSERT/UPDATE mit ungültiger Menge, Redundanz oder Referenz → Abort |
| `s33_user_albums_validate_insert/update` | `user_albums` | Albumzuordnung verweist auf existierenden Nutzer und Album | ungültige Referenz → Abort |
| `s33_notifications_validate_insert/update` | `notifications` | Notification besitzt Empfänger; Read-State ist boolesch | ungültiger Empfänger oder `is_read` außerhalb 0/1 → Abort |
| `s33_trade_requests_validate_insert/update` | `trade_requests` | zwei Beteiligte, Album, dokumentierter Status und boolesche Bestätigungen | ungültige Referenz, Selbsttrade, Status oder Flag → Abort |
| `s33_unlocked_trophies_validate_insert/update` | `unlocked_trophies` | Unlock gehört einem Nutzer und einem Album oder dem bestehenden globalen Scope | ungültige Referenz/Scope → Abort |

Die Down-Migration entfernt ausschließlich diese V0011-Indizes und Trigger.
Sie löscht keine Zeilen und rekonstruiert keine Tabelle.

## Implementierung und Abnahme

### Ergebnis und Datenfluss

Alle im Inventar genannten fachlich mutierenden Aktionen werden nun als
CSRF-geschützte POST-Formulare ausgelöst. Der Datenfluss bleibt dabei klein:

```text
GET der Seite → read-only Darstellung mit Session-CSRF-Token
POST-Formular → globaler CSRF-Guard → bestehende Berechtigungsprüfung
              → bestehender Fachservice → unverändertes Redirectziel
historischer direkter GET → Flask Method Not Allowed (405), keine Mutation
```

Die Objektberechtigungen wurden nicht gelockert. Notifications bleiben auf den
Empfänger begrenzt, Tradeaktionen auf Beteiligte und Album-/Communityaktionen
auf ihre bisherigen Fachregeln. Wiederholte Notification-POSTs bleiben
idempotent.

Die beiden Trophy-GET-Ansichten lesen nur noch den vorhandenen Unlockstand.
Bestehende Bestands- und Trade-Mutationen verwenden weiterhin die vorhandenen
Trophy-Hooks. Ein S33-Test entfernt hierzu einen bereits erreichten Unlock und
weist nach, dass eine folgende normale Bestandsmutation ihn wieder über den
bestehenden Hook erzeugt. Eine neue Trophy-Engine oder ein Sync-Endpunkt wurde
nicht eingeführt.

### Neue Dateien

- `App/Database/migrations/0011_http_integrity_hardening.up.sql`
- `App/Database/migrations/0011_http_integrity_hardening.down.sql`
- `tests/test_s33_http_integrity_hardening.py`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S33-report.md`

### Im S33-Scope geänderte Dateien

- `App/webapp.py`: HTTP-Methoden, POST-Formulare, Debugregistrierung und
  persistenzfreie Trophy-GETs
- `App/static/style.css`: ausschließlich minimale Darstellungsneutralisierung
  der neu notwendigen Form-Buttons
- `tests/test_s01_inventory_regression.py`
- `tests/test_s03_side_effect_security_gate.py`
- `tests/test_s04_home_collection_routes.py`
- `tests/test_s10_inventory_write_service.py`
- `tests/test_s24_notification_history_navigation.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `Dokumentation/Product Bible/roadmap/README.md`

Die vorhandenen Tests wurden nur an den verbindlichen POST-/CSRF-Vertrag und
die aktuelle Zielmigration V0011 angepasst; ihre Fachbehauptungen blieben
unverändert.

### V0011-Abnahme

Der bestehende Migration Runner wurde unverändert verwendet:

```bash
/private/tmp/sammlr-s32-py313-venv/bin/python \
  App/Database/migration_runner.py up \
  --database /private/tmp/sammlr-s33-v11-fixture.db --target 11
```

- Fixture-Kopie: V0000 → V0011 erfolgreich
- wiederholter Up-Lauf: leeres Change-Set, weiterhin V0011
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: keine Treffer
- erzeugt: ein V0011-Unique-Index und zehn V0011-Validierungstrigger
- Backout V0011 → V0010: erfolgreich; exakt diese elf Objekte entfernt,
  Integrität weiterhin `ok`, keine Fachdaten gelöscht
- Kopie der lokalen V0007-Datenbank: V0008–V0011 erfolgreich,
  Integrität `ok`, keine Foreign-Key-Treffer

Die echte lokale Entwicklungsdatenbank wurde nicht migriert. Während des
kontrollierten S33-Abnahmefensters blieb ihr SHA-256 unverändert bei
`db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`.
Die kanonische S00-Fixture blieb unverändert bei
`21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.

### Testmatrix und Ergebnisse

S33-spezifisch:

```bash
DATABASE_PATH=/private/tmp/sammlr-s33-specific.db \
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest tests.test_s33_http_integrity_hardening -v
```

Ergebnis: 13 von 13 Tests erfolgreich. Geprüft wurden 405 und ausbleibende
Mutation aller historischen GETs, POST-Formulare und CSRF, Objektgrenzen,
Retry-Idempotenz, persistenzfreie Trophy-GETs, bestehende Trophy-Hooks,
Development-/Testing-Debugzugriff, Production-404 sowie V0011 Up, Repeat,
Backout und Fehlerfälle.

Vollständiges Gate, jeweils gegen eine eigene temporäre Fixture-Kopie:

```bash
DATABASE_PATH=/private/tmp/sammlr-s33-gate-N.db \
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest discover -s tests -p 'test_s*.py' -v
```

- Lauf 1: 489 von 489 Tests erfolgreich, 5,061 Sekunden
- Lauf 2: 489 von 489 Tests erfolgreich, 5,051 Sekunden

Die Ausgabe enthält bekannte `ResourceWarning`-Hinweise zu älteren offenen
SQLite-Verbindungen sowie zwei bestehende `SyntaxWarning`-Hinweise in
`webapp.py`. Sie verursachen keinen Testfehler und wurden wegen des strikten
S33-Scopes nicht fachfremd refaktoriert.

### Development- und Production-Prüfung

Der Development-Start mit CPython 3.13, explizitem
`SAMMLR_ENV=development`, einer temporären V0011-Datenbank und ohne gesetztes
Secret war erfolgreich. Das Terminal meldete exakt:

`Temporary development secret active – sessions reset on restart.`

`/login` und `/debug-db` lieferten im Development-Modus HTTP 200. Separate
Production-Subprozessprüfungen bestätigten HTTP 404 für `/debug-db` und
`/debug-seed-now`. Der mutierende Debug-Seed ist nur als CSRF-geschützter POST
registriert.

### Release Readiness und Grenzen

- produktive fachlich mutierende GET-Routen: keine verbleibende bekannte Route
- dokumentierte GET-Ausnahmen: ausschließlich CSRF-Sessiontoken,
  `session.pop` für Trophy-Popups und deduplizierte Lazy-Fristnotifications
- Migration: additiv, datenbewahrend, wiederholbar und kontrolliert rückbaubar
- Business-Verhalten, Berechtigungen, Inventory und Trade-Lifecycle:
  unverändert
- lokale Produktdatenbank und S00-Fixture: im kontrollierten Abnahmefenster
  nicht migriert und nicht verändert
- S34: nicht begonnen
- Commit: nicht erstellt
- Push: nicht durchgeführt

S33 ist damit release-ready. Die genannten älteren Warnungen sind lediglich
offene technische Beobachtungen und kein Bestandteil eines vorgezogenen S34.

Zusätzliche offene Beobachtung: Der aktuelle lokale V0007-DB-Hash weicht vom
im S32-Report dokumentierten früheren Hash ab; der Dateizeitpunkt dieser
Abweichung lag bereits vor den abschließenden S33-Migrations- und Gateprüfungen.
Die Datenbank ist weiterhin auf V0007, `PRAGMA integrity_check` liefert `ok`
und `PRAGMA foreign_key_check` keinen Befund. Mangels einer identischen
V0007-Vergleichskopie wurde keine Ursache unterstellt und keine lokale
Produktdatei zurückgesetzt oder verändert.
