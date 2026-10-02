# Sprintbericht S34 – Deployment, Backup, Recovery und Observability

Stand: 2026-08-09

## Ziel und Ergebnis

S34 stellt einen reproduzierbaren und beobachtbaren Beta-Betrieb für einen
Linux-PaaS mit Gunicorn, einem Worker, SQLite und privatem persistentem Volume
her. Deployment, Migration, Backup, Recovery, Health, Requestkorrelation,
strukturierte Logs und providerneutrales Fehlertracking sind umgesetzt und
getestet. Fachlogik und sichtbares Produktverhalten blieben unverändert.

Es wurde keine V0012 angelegt. Der verbindliche Zielstand bleibt V0011.

## Architektur und Datenfluss

Der vollständige Vertrag steht in
`Dokumentation/Product Bible/operations/s34-deployment-recovery.md`.

```text
Pre-Deploy:
Production-DB → SQLite-Backup-API → SHA-256
              → Migration Runner V0011
              → integrity_check + foreign_key_check + Versionsgate
              → Gunicorn-Start → Smoke

Request:
1 Proxy-Hop → ProxyFix nur Production → Request-ID
            → bestehender Auth-/CSRF-/Fachpfad
            → JSON-Requestlog stdout + X-Request-ID
            → unerwarteter Fehler/HTTP 500 → sanitisiertes Error-JSON stderr

Recovery:
Backup → neue isolierte Datei → Hash/SQLite/FK/V0011
       → Test-App → read-only Smoke → manuelle Restore-Freigabe
```

## Neue Komponenten und Dateien

- `Procfile`: eindeutiger PaaS-Einstieg mit dem freigegebenen
  Ein-Worker-Gunicorn-Befehl.
- `App/services/runtime_operations.py`: Production-Environment- und
  V0011-Gates sowie read-only Datenbankvalidierung.
- `App/services/observability.py`: Request-ID, pseudonyme Nutzerreferenz,
  JSON-Requestlogging und providerneutrales Error-Tracking.
- `App/Database/sqlite_recovery.py`: SQLite Backup API, SHA-256,
  Integritäts-/Versionsprüfung, isolierter Restore und 30-Tage-Retention.
- `Scripts/backup_sqlite.py`: regelmäßiges konsistentes Backup.
- `Scripts/restore_sqlite.py`: fail-closed Restore in eine neue Datei.
- `Scripts/predeploy.py`: Backup → Migration → Integrität als separater
  Production-Predeploy-Schritt.
- `tests/test_s34_deployment_recovery_observability.py`: 13 S34-Vertragstests.
- `Dokumentation/Product Bible/operations/s34-deployment-recovery.md`.
- `Dokumentation/Product Bible/operations/s34-deployment-checklist.md`.
- `Dokumentation/Product Bible/operations/s34-recovery-checklist.md`.
- `Dokumentation/Product Bible/roadmap/sprint-reports/S34-report.md`.

## Geänderte Dateien

- `App/webapp.py`: Production-Validierung, Production-only `ProxyFix`,
  öffentlicher `/healthz`, Request-/Error-Observability und Entfernung der
  automatischen Schemaanlage beim App-Import.
- `tests/test_s22_smart_trade_requests.py`: ausschließlich zeitunabhängiger
  Testaufbau für den bestehenden 48-Stunden-Vertrag; keine Fachlogik geändert.
- `tests/test_s33_http_integrity_hardening.py`: Production-Probe an den neuen
  V0011-/Pfad-/Logging-Vertrag angepasst.
- `Dokumentation/Product Bible/roadmap/README.md`: S34-Verweise und Sprintstand.

## Production- und Migrationsvertrag

Production verlangt fail-closed:

- `SAMMLR_ENV=production`
- externes `SAMMLR_SECRET_KEY`
- `DATABASE_PATH=/var/data/sammlr.db`
- `PORT`
- öffnbare Datenbank mit exakt V0011

Der App-Import legt kein Schema an und migriert nicht. Der separate
Predeploy-Aufruf lautet aus dem Repository-Root:

```sh
SAMMLR_ENV=production \
SAMMLR_SECRET_KEY='<extern>' \
DATABASE_PATH=/var/data/sammlr.db \
PORT="${PORT}" \
python3 -m Scripts.predeploy
```

Erst danach startet die App verbindlich mit:

```sh
cd App &&
gunicorn \
  --workers 1 \
  --bind 0.0.0.0:${PORT} \
  --access-logfile - \
  --error-logfile - \
  webapp:app
```

Nur Production erhält `ProxyFix` mit exakt `x_for=1`, `x_proto=1`,
`x_host=1`, `x_port=0`, `x_prefix=0`. Development und Testing vertrauen
keinem Proxy-Hop automatisch.

## Backup, Retention und Recovery

`create_backup` verwendet `sqlite3.Connection.backup`; eine potentiell aktive
SQLite-Datei wird nicht naiv kopiert. Production-Backups liegen ausschließlich
unter `/var/data/backups/`, heißen
`sammlr-YYYYMMDD-HHMMSS-vXXXX.db`, erhalten `0600`, und das Verzeichnis erhält
`0700`. Die Retention entfernt nur eigene, exakt passende Dateien nach mehr
als 30 Tagen.

Der Restore verweigert ein vorhandenes Ziel und überschreibt weder Backup noch
Production-Datei. Die technische Freigabe verlangt SHA-256,
`integrity_check=ok`, leeren `foreign_key_check`, V0011 und erfolgreichen
read-only App-Smoke. RPO ist 24 Stunden, RTO 60 Minuten.

## Observability- und Redaktionsvertrag

Jede Response enthält `X-Request-ID`. Syntaktisch sichere IDs bis 64 Zeichen
werden übernommen, andere durch eine UUID ersetzt. Requestlogs enthalten nur:

- `timestamp`, `level`, `request_id`, `method`, normalisierte Routenregel,
  `status`, `duration_ms`
- optional eine HMAC-pseudonymisierte interne `user_ref`

Nicht geloggt werden Querystrings, Bodies, Form-/Loginwerte, Header, Cookies,
Session, Namen, Usernames, Passwörter, Token, Secrets sowie Sticker- oder
Tradeinhalte.

Ungefangene Exceptions und direkte HTTP-500-Responses erzeugen genau ein
providerneutrales Error-Event nach stderr. Der Stack besteht ausschließlich
aus Dateiname, Zeilennummer und Funktionsname; Fehlermeldung und lokale Werte
werden nicht ausgegeben. Erwartete 400, 403, 404, 405 und 429 erzeugen kein
Error-Tracking-Event.

## Healthcheck

`GET /healthz` ist öffentlich. Es prüft Prozess, Datenbanköffnung, einfachen
Select und exakt V0011. Erfolg ist HTTP 200 mit `{"status":"ok"}`; Fehler
werden ohne Pfad- oder SQL-Details als HTTP 503 ausgegeben. Der teure
`integrity_check` bleibt Predeploy, Backupprüfung und Recovery vorbehalten.

## Recovery-Drill

Der manuelle Drill lief ausschließlich auf temporären Dateien:

- Quelle: `/private/tmp/sammlr-s34-drill-source.db`, isoliert bis V0011
- Backup:
  `/private/tmp/sammlr-s34-drill-backups/sammlr-20260809-133321-v0011.db`
- SHA-256 Backup:
  `e9bf8259f93df910239cc6f364f043b2079eacced25b12a83019a1253a16e105`
- ein absichtlich bereits vorhandenes Restoreziel wurde fail-closed nicht
  überschrieben
- erfolgreiche Recovery-Datei:
  `/private/tmp/sammlr-s34-drill-recovered-3.db`
- SHA-256 Recovery: identisch zum Backup
- Version: V0011
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: ohne Befund
- Development-Start gegen Recovery: erfolgreich
- Terminalhinweis zum temporären Development-Secret: vorhanden
- Smoke: `/healthz` 200, `/login` 200, `/` unauthentifiziert 302,
  `/static/style.css` 200

Keine lokale Entwicklungs-, Fixture-, Backup- oder Produktionsdatenbank war
am Drill beteiligt.

## Testmatrix und Ergebnisse

S34-spezifisch:

```sh
DATABASE_PATH=/private/tmp/sammlr-s34-specific-final.db \
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest tests.test_s34_deployment_recovery_observability -v
```

Ergebnis: 13 von 13 Tests erfolgreich. Abgedeckt sind Production fail-closed,
exakter DB-Pfad, Gunicorn-Appimport, ProxyFix-Grenze, Health 200/503,
Request-ID, JSON-Redaktion, sanitisiertes 500-Tracking, Backup, SHA-256,
Retention, Predeploy, Restore-Schutz, falsche Version und Recovery-Smoke.

Vollständiges Gate:

```sh
DATABASE_PATH=/private/tmp/sammlr-s34-gate-N.db \
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest discover -s tests -p 'test_s*.py' -v
```

- finaler Lauf 1: 502 von 502 Tests erfolgreich, 5,517 Sekunden
- finaler Lauf 2: 502 von 502 Tests erfolgreich, 5,617 Sekunden

Bekannte ältere SQLite-`ResourceWarning`-Hinweise und zwei bestehende
`SyntaxWarning`-Meldungen bleiben sichtbar, verursachen aber keinen Fehler.
Sie wurden wegen des strikten S34-Scopes nicht fachfremd refaktoriert.

## Release Readiness und Scope

- Deployment- und Recovery-Checklisten: vollständig und erfolgreich geprobt
- Startup, Health, Migration, Backup/Restore und Log-Redaction: grün
- `git diff --check`: ohne Befund
- V0011: unverändert höchste Migration; keine V0012
- lokale Produktdatenbank und S00-Fixture: nicht migriert
- lokale Entwicklungsdatenbank weiterhin V0007, `integrity_check=ok`,
  `foreign_key_check` ohne Befund; SHA-256 während S34 unverändert
  `db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`
- kanonische S00-Fixture während S34 unverändert; SHA-256
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`
- Fachlogik und sichtbares Verhalten: unverändert
- Hochverfügbarkeit, Docker-Zwang, Kubernetes, PostgreSQL, Offsite-Backup und
  externer Error-Tracking-Anbieter: nicht eingeführt
- S35: nicht begonnen
- Commit: nicht erstellt
- Push: nicht durchgeführt

S34 ist release-ready.
