# Sprintbericht S32 – Authentifizierung, Secrets und CSRF

Stand: 2026-08-09

## Ziel und Ergebnis

S32 macht Authentifizierung, Sessionkonfiguration und schreibende POST-Requests
beta-tauglich. Neue Passwörter werden ausschließlich mit Werkzeug-scrypt
gespeichert, bestehende Klartextpasswörter nach einem erfolgreichen Login
kontrolliert migriert, Sessions nach Authentifizierung rotiert und über eine
persistente Auth-Version invalidierbar gemacht. Ein globaler CSRF-Guard schützt
produktive POST-Mutationen. Persistentes Login-Throttling begrenzt Versuche je
normalisiertem Username und Client-IP.

Produktion startet ohne `SAMMLR_SECRET_KEY` nicht. Der explizite lokale
Development-Modus darf ein temporäres zufälliges Secret erzeugen und meldet
einmalig:

```text
Temporary development secret active – sessions reset on restart.
```

S33 wurde nicht begonnen. Die dort vorgesehenen mutierenden GET-Routen,
Debugrouten und zusätzlichen Datenbank-Constraints wurden lediglich
inventarisiert.

## Architektur und Datenfluss

```text
SAMMLR_ENV + optional SAMMLR_SECRET_KEY
  -> Flask Secret-/Cookievertrag
  -> signierte, nicht permanente Session
     -> user_id + auth_version + csrf_token

Login/Register
  -> AuthSecurityService
     -> LoginThrottleService
     -> Legacy- oder scrypt-Prüfung
     -> atomare Migration beziehungsweise Rehash
  -> Sessionrotation

Mutierender POST
  -> globaler CSRF-Guard
  -> bestehende Route und unveränderte Fachberechtigung
```

Die Security-Schicht verwendet bestehende SQLite-Verbindungen und Werkzeug.
Sie enthält keine eigene Kryptografie und verändert keine Trade-, Inventory-,
Notification-, Privacy-, Community- oder UI-Fachlogik.

## Neue Dateien

- `App/services/auth_security.py`
- `App/Database/migrations/0010_auth_session_csrf.up.sql`
- `App/Database/migrations/0010_auth_session_csrf.down.sql`
- `tests/__init__.py`
- `tests/test_s32_auth_session_csrf.py`
- `Dokumentation/Product Bible/security/s32-auth-session-csrf.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S32-report.md`

## Geänderte Dateien

- `App/webapp.py`: Umgebungs-/Secretvertrag, sichere Cookies, CSRF-Guard,
  Sessionrotation und Auth-Version, sicherer Login/Registrierung,
  Current-Password-Prüfung sowie Integration des Auth-Service.
- `Dokumentation/Product Bible/roadmap/README.md`: S32-Verweise und Sprintstand.
- `tests/test_s26_collector_profiles.py`,
  `tests/test_s27_album_privacy_trade_pool.py`,
  `tests/test_s28_trade_ratings.py`,
  `tests/test_s29_friendships_community.py` und
  `tests/test_s31_ui_foundation.py`: ausschließlich Erwartung der nun höchsten
  Migration V0010.

## Migration V0010 und Backout

V0010 ergänzt `users.password_scheme`, `users.auth_version` und die persistente
Tabelle `login_throttle`. Bestehende Konten werden ohne Passwortrekonstruktion
als `legacy_plaintext` markiert. Nach einem erfolgreichen Login wird nur das
betroffene Passwort atomar auf `werkzeug_scrypt` migriert.

Der Backout ist fail-closed: Sobald ein sicherer scrypt-Hash existiert, wird
die Down-Migration abgewiesen. Es findet weder Klartextrekonstruktion noch
automatisches Löschen oder Zurücksetzen von Zugangsdaten statt. Vorwärtslauf,
Wiederholung und Fail-closed-Backout sind automatisiert getestet.

## Security-Vertrag

- Kanonischer Passworthash: `scrypt:32768:8:1` über Werkzeug.
- Neue Registrierungen speichern niemals Klartext.
- Legacy-Migration und Rehash ausschließlich nach erfolgreicher Prüfung.
- Produktion benötigt zwingend ein externes `SAMMLR_SECRET_KEY`.
- Tests benötigen ein eigenes explizites Testsecret.
- Explizite lokale Entwicklung darf ein zufälliges Prozesssecret verwenden.
- Cookies: HttpOnly, SameSite Lax, Secure in Produktion, keine Domain-Weitung.
- Sessionrotation nach Login; Passwortwechsel erhöht `auth_version` und
  verlangt erneuten Login.
- CSRF-Synchronizer-Token für sämtliche produktiven POST-Mutationen.
- Fehlende oder falsche CSRF-Tokens werden vor einer Mutation mit HTTP 403
  abgewiesen.
- Login-Throttling: fünf Fehlversuche, danach 15 Minuten Sperre je Username/IP.
- Login- und Registrierungsfehler geben keine Kontoexistenz preis.
- Passwortänderung und Accountlöschung erfordern das aktuelle Passwort.

## Python-3.13-Runtime

Der freigegebene offizielle macOS-Installer CPython 3.13.15 wurde vor der
Installation über die veröffentlichte SHA-256-Prüfsumme, die Signatur der
Python Software Foundation und Apples Notarisierung geprüft.

```text
Interpreter: /usr/local/bin/python3.13
Version:     Python 3.13.15
hashlib.scrypt vorhanden: True
System-Python: /usr/bin/python3, weiterhin Python 3.9.6
```

Für die Abnahme wurde mit dieser Runtime die isolierte Umgebung
`/private/tmp/sammlr-s32-py313-venv` erzeugt. Ausschließlich dort wurden die
Abhängigkeiten aus `requirements.txt` installiert: Flask 3.1.3 und Gunicorn
26.0.0 einschließlich ihrer transitiven Pakete. Das Repository erhielt keine
Venv- oder Paketartefakte.

## Testmatrix und Ergebnisse

| Bereich | Prüfung | Ergebnis |
|---|---|---|
| Runtime | Python 3.13.15 und `hashlib.scrypt` | grün |
| Migration | V0010 vorwärts, wiederholt, fail-closed zurück | grün |
| Registrierung | nur kanonischer scrypt-Hash | grün |
| Legacy-Login | Migration nur nach Erfolg | grün |
| Rehash | nicht kanonischer valider Hash wird aktualisiert | grün |
| Sessions | Rotation und Auth-Version-Invalidierung | grün |
| Secrets | Produktion fail-closed, Development temporär | grün |
| Cookies | HttpOnly, SameSite und Secure-Vertrag | grün |
| CSRF | fehlender/falscher Token blockiert Mutation | grün |
| Throttling | Limit, Fenster, Isolation und HTTP 429 | grün |
| Enumeration | einheitliche sichtbare Fehler | grün |
| Kontoaktionen | aktuelles Passwort zwingend | grün |
| Regression | vollständige S01–S32-Suite zweimal | grün |

S32-spezifischer Lauf:

```text
PYTHONDONTWRITEBYTECODE=1 \
  /private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest tests.test_s32_auth_session_csrf -v
Ran 13 tests in 0.752s – OK
```

Vollständiges Gate, Lauf 1:

```text
DATABASE_PATH=/private/tmp/sammlr-s32-gate-1.db \
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONDONTWRITEBYTECODE=1 \
  /private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest discover -s tests -p "test_s*.py" -v
Ran 476 tests in 4.756s – OK
```

Vollständiges Gate, Lauf 2:

```text
DATABASE_PATH=/private/tmp/sammlr-s32-gate-2.db \
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONDONTWRITEBYTECODE=1 \
  /private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest discover -s tests -p "test_s*.py" -v
Ran 476 tests in 4.738s – OK
```

Die Suite meldet bestehende `ResourceWarning`s für nicht geschlossene
SQLite-Verbindungen und zwei `SyntaxWarning`s für ältere Escape-Sequenzen.
Beide Läufe enden dennoch reproduzierbar mit `OK`. Diese sachfremden Befunde
wurden in S32 nicht refaktoriert.

## Development-Start

Der Start wurde mit Python 3.13.15 gegen
`/private/tmp/sammlr-s32-dev-start.db` und ohne Secret durchgeführt. Die
vorgeschriebene temporäre-Secret-Meldung erschien genau einmal. Der Server lief
anschließend ohne ReLoader auf `127.0.0.1:18080`; `GET /login` lieferte HTTP
200. Danach wurde der Prozess kontrolliert beendet. Die lokale
Entwicklungsdatenbank war nicht beteiligt.

## Release Readiness

- Höchste Repository-Migration: V0010.
- Eine isolierte Fixture-Kopie wurde reproduzierbar von V0000 auf V0010
  migriert.
- Isolierte V0010-Datenbank: `PRAGMA integrity_check = ok`.
- Isolierte V0010-Datenbank: `PRAGMA foreign_key_check` ohne Befund.
- Lokale Entwicklungsdatenbank blieb auf V0007 und wurde nicht migriert.
- Lokale Entwicklungsdatenbank: `PRAGMA integrity_check = ok` und
  `PRAGMA foreign_key_check` ohne Befund.
- SHA-256 lokale Entwicklungsdatenbank:
  `9cfce687b17d72ce80a9009f2d402861fb4e061000379545ee7f20f906015106`.
- SHA-256 kanonische S00-Fixture:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Sämtliche S32- und Gesamtgatetests verwendeten ausschließlich temporäre
  Datenbankkopien.
- Keine Produktdatenbank, Fixture oder Backup-Datei wurde migriert.

## Bekannte Grenzen und offene Punkte für S33

- Die in der Security-Spezifikation inventarisierten mutierenden GET-Routen
  müssen in S33 auf sichere HTTP-Methoden umgestellt werden.
- Debugrouten und Startup-Schreibarbeit werden erst in S33 bereinigt oder
  abgesichert.
- Foreign-Key-, Unique- und weitere Check-Constraints außerhalb V0010 gehören
  ausschließlich zu S33.
- Bestehende ResourceWarnings und ältere Escape-SyntaxWarnings sind keine
  S32-Fachregression und wurden nicht sachfremd korrigiert.

## Scope-Bestätigung

Es wurde ausschließlich S32 umgesetzt und geprüft. Es gab keine Änderung an
Inventory, Trade Lifecycle, Snapshot, Coverage, TopMatch, Smart Requests,
Shipping, Receipt, Problems, Ratings, Notifications, Operational Home,
Privacy, Community oder S31-Design. S33 wurde nicht begonnen. Es wurde kein
Commit erstellt und kein Push durchgeführt.
