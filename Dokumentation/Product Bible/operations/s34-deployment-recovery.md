# S34 – Deployment, Recovery und Observability

Stand: 2026-08-18

## Ziel und unveränderliche Grenzen

S34 richtet Sammlr für einen Linux-PaaS-Betrieb mit einem Gunicorn-Worker,
SQLite und privatem persistentem Volume ein. Fachlogik, Benutzeroberfläche,
Inventory und Trade-Lifecycle bleiben unverändert. Seit S35 ist der aktuelle
Produktions-Migrationsstand V0018. V0013 ergänzt den additiven historischen
Sammlungs-Datenvertrag aus CB-001. V0014 ergänzt den technischen
Cutover-/Idempotenzbeleg; die CB-002-Writer erfassen neue Ereignisse ab Cutover,
ohne Altbestände zu interpretieren. V0015 ergänzt die additive persistente
Trophy-Wahrheit aus CB-005 ohne Legacy-Backfill. V0016 erlaubt den strukturierten
CB-004-Backfill-Source-Typ, führt aber selbst keinen Backfill aus. V0017 ergänzt
das additive globale Profilprivacy-Gate aus CB-006 mit Default `public`. V0018
operationalisiert den bestehenden Feed-Eventstore additiv und ergänzt den
kontrollierten Sammlr-News-Datensatz sowie kanonische Sortierindizes.

## Architektur

```text
Pre-Deploy (separater Prozess)
  /var/data/sammlr.db
    → SQLite Backup API → /var/data/backups/sammlr-...-vXXXX.db
    → Migration Runner bis V0018
    → integrity_check + foreign_key_check + Versionsprüfung
    → erst danach Gunicorn-Start

Production Request
  Proxy (genau 1 Hop)
    → ProxyFix
    → Request-ID
    → bestehende Auth-/CSRF-/Fachrouten
    → JSON-Requestlog stdout + X-Request-ID
    → unerwarteter 500: providerneutrales Error-Event stderr

Recovery-Drill
  ausgewähltes Backup
    → SQLite Backup API → neue isolierte Recovery-Datei
    → SHA-256 + SQLite-/FK-/Versionsprüfung
    → Test-App gegen Recovery-Datei
    → read-only Smoke; niemals Production überschreiben
```

## Produktionsvertrag

Der einzige Production-Einstieg ist:

```sh
cd App &&
gunicorn \
  --workers 1 \
  --bind 0.0.0.0:${PORT} \
  --access-logfile - \
  --error-logfile - \
  webapp:app
```

Pflichtwerte sind `SAMMLR_ENV=production`, ein externes
`SAMMLR_SECRET_KEY`, `DATABASE_PATH=/var/data/sammlr.db` und `PORT`.
Production startet fail-closed, wenn Pfad, Datenbankzugriff oder V0018 fehlen.
Schemaänderungen laufen ausschließlich im separaten Pre-Deploy-Schritt; der
App-Import führt keine Migration und keine Schemaanlage aus.

Nur Production vertraut über Werkzeug `ProxyFix` exakt einem Hop für
`X-Forwarded-For`, `X-Forwarded-Proto` und `X-Forwarded-Host`. Development und
Testing bleiben unverändert ohne Proxyvertrauen.

## Backup- und Restore-Vertrag

Backups werden mit der SQLite Backup API erstellt, nicht durch eine naive
Dateikopie. Das private Verzeichnis `/var/data/backups/` erhält restriktive
Rechte; Backupdateien erhalten Modus `0600`. Das Namensschema lautet
`sammlr-YYYYMMDD-HHMMSS-vXXXX.db`. Das Skript darf ausschließlich eigene,
älter als 30 Tage gewordene Dateien dieses Schemas entfernen.

Ein Restore schreibt immer in eine neue, explizit benannte isolierte Datei.
Ein vorhandenes Ziel und die Quelldatei werden nie überschrieben. Technische
Freigabe verlangt SHA-256, öffnbare SQLite-Datei, `integrity_check=ok`, leeren
`foreign_key_check`, exakt V0018 sowie erfolgreichen App- und read-only Smoke.
RPO ist 24 Stunden, RTO 60 Minuten.

## Healthcheck

`GET /healthz` ist öffentlich und prüft nur Prozess, Datenbanköffnung, einen
einfachen Select und den Migrationsstand V0018. Erfolg ist HTTP 200 mit
`{"status":"ok"}`; jeder Fehler wird detailarm als HTTP 503 beantwortet.
Ein vollständiger `integrity_check` gehört nicht in den Requestpfad.

## Logging und Fehlertracking

Jeder Request erhält eine sichere, höchstens 64 Zeichen lange
`X-Request-ID`. Eine gültige eingehende ID wird übernommen, andernfalls wird
eine neue UUID erzeugt. Dieselbe ID steht im Response-Header.

Das Requestlog ist genau ein JSON-Objekt nach stdout mit `timestamp`, `level`,
`request_id`, `method`, normalisiertem `path`, `status` und `duration_ms`.
Optional wird eine HMAC-pseudonymisierte interne `user_ref` ausgegeben.
Querystrings, Bodies, Formulardaten, Header, Cookies, Sessions, Tokens,
Passwörter, Namen, Usernames sowie Sticker- oder Tradeinhalte werden nicht
geloggt.

Providerneutrales Fehlertracking erfasst unerwartete Exceptions und HTTP 500
als sanitisiertes JSON nach stderr. Zulässig sind Request-ID, Fehlerklasse,
Route, Methode, Zeitpunkt und ein sanitisiertes Stacktrace ohne lokale Werte.
Erwartete 400, 403, 404, 405 und 429 sowie Fachablehnungen erzeugen kein
Error-Event.

## Seiteneffekte und unveränderte Komponenten

Backup, Pre-Deploy und Recovery sind explizite Operatoraktionen. Healthcheck,
Request-ID und Requestlogging sind read-only. Unverändert bleiben alle
Fachservices, DTOs, Berechtigungen, CSRF, Sessions, Navigation, UI, Inventory,
Trades, Notifications, Ratings und Community.
