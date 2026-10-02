# Sprintbericht S35 – Datenschutz, Account Lifecycle und Performance-Baseline

Stand: 2026-08-09

## Ziel und Ergebnis

S35 führt den verbindlichen Account Lifecycle mit exakt `active`,
`deactivated` und `anonymized` ein. Nutzer können ihr Konto nach erneuter
Passwortprüfung deaktivieren, nach einem gesonderten Bestätigungsschritt
reaktivieren und – sofern keine laufende Tauschaktionen existieren – endgültig
anonymisieren. Historische Trade- und Bewertungsdaten bleiben fachlich
erhalten, personenbezogene Produktoberflächen zeigen ausschließlich
„Gelöschter Nutzer“.

Die Account-Funktionen, Migration V0012, Tests, Export-Grundlage und
Performance-Messung sind vollständig umgesetzt. Die Performance-Baseline hat
jedoch verbindliche Release-Blocker ergeben. S35 ist deshalb fachlich und
technisch abgeschlossen, aber die Public-Beta-Release-Readiness ist nicht
gegeben. Gemäß Scope wurden keine Performanceoptimierungen vorgenommen.

Nicht umgesetzt wurden Admin-Sperren, S29-Blockierungen, Download-/ZIP-Export,
zusätzliche Rechtstexte, automatische Optimierungen oder Arbeiten an S36.

## Product-Owner-Entscheidungen

- `deactivated` wird nicht durch einen normalen Login aktiviert. Korrekte
  Zugangsdaten erzeugen nur einen kurzlebigen Reaktivierungsnachweis; erst das
  explizite POST „Konto reaktivieren“ aktiviert den Account und erstellt die
  Session.
- Deaktivierung verlangt das aktuelle Passwort und erhöht `auth_version`,
  wodurch bestehende Sessions sofort ungültig werden.
- Anonymisierung verlangt aktuelles Passwort und die verbindliche Checkbox.
  Sie ist endgültig und besitzt keine Karenzzeit.
- Laufende Zustände blockieren die Anonymisierung; abgeschlossene und sonstige
  terminale Zustände bleiben als technische beziehungsweise fachliche
  Historie erhalten.
- Historische Tradepositionen, Timeline, Versand, Empfang, Probleme und
  Bewertungen bleiben erhalten. Sammlung, Albumzuordnungen, Bestand,
  Trophäen, Communitydaten, Aktivität, Notifications und Login-Throttle-Daten
  werden entfernt.
- Der frühere Username wird wieder freigegeben. Ein interner Tombstone bleibt
  ausschließlich zur referenziellen Integrität bestehen und wird nie
  angezeigt.
- Der Datenexport ist nur als read-only Service und Dateninventar vorbereitet;
  es gibt keine UI und keine Datei.
- Die Performance-Baseline verwendet den verbindlichen Datensatz,
  Gunicorn/SQLite, 20 parallele Requests und die freigegebenen P95-Grenzen.

## Architektur und Datenfluss

Der vollständige Vertrag steht in
`Dokumentation/Product Bible/roadmap/s35-account-lifecycle-privacy-performance.md`.

```text
Login -> AuthSecurityService
      -> active: Session
      -> deactivated: Reaktivierungsnachweis
         -> CSRF-POST bestätigen -> active -> Session
      -> anonymized: Login verweigert

Profil -> CSRF-POST -> AccountLifecycleService
  Deaktivierung -> Passwort -> account_state + auth_version -> Session aus
  Anonymisierung -> Passwort + Checkbox -> Trade-Gate
    -> laufend: unverändert verweigern
    -> terminal: persönliche Daten atomar entfernen,
       Historienreferenzen erhalten, Identität anonymisieren

Profil/Suche/Matching/neue Communityaktionen -> nur active
Historische Tradeansichten -> gelöschte Identität als „Gelöschter Nutzer“

AccountDataInventoryService -> read-only Kategorien und Zählwerte
Performance-Skript -> isolierte /private/tmp-DB -> Gunicorn -> 20 Requests
```

### Read-/Write-Pfade und Seiteneffekte

`AccountLifecycleService` besitzt die S35-Schreibregeln. Deaktivierung ändert
nur Accountzustand und Sessionversion. Reaktivierung ändert nur den Zustand
zurück auf `active`. Anonymisierung läuft transaktional, prüft zuerst das
Trade-Gate und entfernt erst danach die freigegebenen personenbezogenen
Datenkategorien. Eine abgewiesene Aktion persistiert nichts.

`AccountDataInventoryService`, Profile, Suche, Privacy- und Matchingfilter
sowie die Baseline lesen ausschließlich. Inventory, Availability, Trade
Lifecycle, Ratings, Notificationtypen, Community-State-Machine, Security und
Deployment bleiben die bestehenden kanonischen Quellen.

## Migration und Datenbankstand

V0012 ergänzt additiv:

- `users.account_state TEXT NOT NULL DEFAULT 'active'` mit `CHECK` auf
  `active`, `deactivated`, `anonymized`,
- einen Index für aktive Nutzerprojektionen.

Bestehende Nutzer werden durch den Default `active`. Die Up-Migration ist
wiederholt ausführbar. Die Down-Migration ist fail-closed, sobald mindestens
ein nicht aktiver Account existiert; sie transformiert oder löscht keine
Fachdaten.

Die Abnahme erfolgte ausschließlich auf einer temporären Datenbank:

- Pfad: `/private/tmp/sammlr-s35-acceptance-v12.db`
- Migrationsstand: V0012
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: ohne Befund
- SHA-256: `ea84b8653f8c1bcd7db74e70d52dc32e11327ab83605c7a4af0baa5bcdb27374`

Die lokale Entwicklungsdatenbank wurde nicht migriert und blieb auf V0007.
Ihr SHA-256 blieb
`db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`.
Die kanonische S00-Fixture blieb ebenfalls unverändert; SHA-256
`21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.

## Neue Dateien

- `App/Database/migrations/0012_account_lifecycle.up.sql`
- `App/Database/migrations/0012_account_lifecycle.down.sql`
- `App/services/account_lifecycle.py`
- `App/performance_wsgi.py`
- `Scripts/s35_performance_baseline.py`
- `tests/test_s00_s35_gate_environment.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `Dokumentation/Product Bible/roadmap/s35-account-lifecycle-privacy-performance.md`
- `Dokumentation/Product Bible/roadmap/s35-performance-baseline.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S35-report.md`

## Geänderte Dateien

- `App/services/auth_security.py`: Accountzustände und explizites
  Reaktivierungsergebnis in den bestehenden Auth-Vertrag integriert.
- `App/webapp.py`: aktive Session vorausgesetzt, Reaktivierungs-,
  Deaktivierungs- und Anonymisierungswege sowie anonymisierte historische
  Anzeigen ergänzt.
- `App/services/collector_profiles.py`: deaktive/anonymisierte Profile aus
  öffentlicher Projektion entfernt.
- `App/services/album_privacy.py`: Profil-/Albumreads auf aktive Eigentümer
  begrenzt.
- `App/services/community.py`: Suche, Matching und neue Communityinteraktionen
  auf aktive Accounts begrenzt.
- `App/services/runtime_operations.py`, `Scripts/restore_sqlite.py` und die
  lebenden S34-Operationsdokumente: erwarteten aktuellen Migrationsstand auf
  V0012 angehoben.
- `Dokumentation/Product Bible/roadmap/README.md`: S35-Spezifikation,
  Baseline, Report, Status und Release-Blocker verlinkt.
- Bestehende Migrations-/Kompatibilitätstests: ausschließlich auf den neuen
  V0012-Zielstand und den nun verbindlichen Anonymisierungsvertrag angepasst.

Bereits im Arbeitsverzeichnis vorhandene Änderungen aus früheren Sprints
wurden nicht zurückgesetzt, gelöscht oder sachfremd überarbeitet.

## Bewusst unveränderte Komponenten

- Inventory Read/Write, Availability und Snapshot
- Trade Lifecycle, Reservation, Shipping, Receipt und Problembehandlung
- Trade Coverage, Top Match und Smart Requests
- Notificationtypen und Notification-Historie
- Ratingfinalität und Ratingaggregation
- Friendship-State-Machine und S29-Nutzerblockierung
- S32-/S33-Security-Verträge und S34-Deploymentarchitektur
- lokale Entwicklungsdatenbank, S00-Fixture und bestehende Backups

## Testmatrix

| Bereich | Nachweis |
| --- | --- |
| V0012 | Forward, Wiederholung, Default, CHECK und fail-closed Backout |
| Deaktivierung | Passwortpflicht, Zustandswechsel, sofortige Sessioninvalidierung |
| Reaktivierung | korrekte Credentials, keine Login-Session vor Bestätigung, explizites CSRF-POST |
| Anonymisierung | Passwort + Checkbox, irreversible Identität, Username wiederverwendbar |
| Trade-Gate | laufende Zustände blockiert; terminale Zustände erlaubt und Historie erhalten |
| Datenschutz | persönliche Datenkategorien entfernt; historische Trades/Ratings erhalten |
| Sichtbarkeit | Login, Profil, Suche, Matching und neue Interaktionen nur für `active` |
| Anzeige | historische Identität ausschließlich „Gelöschter Nutzer“ |
| Export-Grundlage | read-only Dateninventar, keine Mutation/Datei/UI |
| Regression | vollständiges S01–S35-Gate zweimal ohne Fehler oder Skip |

S35-spezifischer Befehl:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest tests.test_s35_account_lifecycle_privacy_performance -v
```

Ergebnis: 7 von 7 Tests erfolgreich in 0,432 Sekunden.

Vollständiger, exakt geforderter Gate-Befehl:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest discover -s tests -p "test_s*.py" -v
```

- finaler Lauf 1: 510 von 510 Tests erfolgreich, 5,719 Sekunden
- finaler Lauf 2: 510 von 510 Tests erfolgreich, 5,676 Sekunden
- übersprungene Tests: 0
- bekannte `ResourceWarning`-Hinweise zu älteren SQLite-Testverbindungen sind
  sichtbar, verursachen aber keinen Testfehler

## Development-Start und technische Abnahme

Der reale Development-Start wurde mit Python 3.13.15, einer isolierten
temporären V0012-Datenbank und ohne festes Secret geprüft. Das Terminal zeigte
den verbindlichen Hinweis
`Temporary development secret active – sessions reset on restart.`.
`/login` und `/healthz` antworteten jeweils HTTP 200. Der Server wurde nach dem
Smoke wieder beendet.

- Syntaxprüfung: erfolgreich; zwei bereits bekannte `SyntaxWarning`-Hinweise
  in `webapp.py` bleiben außerhalb des S35-Scopes
- `git diff --check`: ohne Befund
- produktive oder lokale Fachdaten: nicht verändert
- ausschließlich temporäre Test- und Messdaten unter `/private/tmp`

## Performance-Baseline

Die Details und der reproduzierbare Befehl stehen in
`Dokumentation/Product Bible/roadmap/s35-performance-baseline.md`.

Datensatz: exakt 100 Nutzer, 10 Alben, 100.000 Stickerpositionen, 2.000
Trades, 5.000 Notifications und 1.000 Freundschaften. Gemessen wurde mit
Gunicorn 26.0.0, SQLite V0012, einem Worker, 20 Threads und 20 gleichzeitigen
Requests. Die temporäre Messdatenbank bestand beide SQLite-Integritätsprüfungen.

| Ablauf | P95 | Fehler | Freigabe |
| --- | ---: | ---: | --- |
| Login | 8,278 ms | 0/20 | bestanden |
| Home | 115,485 ms | 0/20 | bestanden |
| Sammlung | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Album | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Stickerwall | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Suche | 1.472,898 ms | 0/20 | Release-Blocker |
| Tradebörse | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Dealansicht | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Notifications | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Profil | 1.918,630 ms | 0/20 | Release-Blocker |

Damit ist die geforderte Fehlerquote von 0 % für mehrere Kernseiten ebenfalls
nicht erfüllt. Diese Befunde sind reale Release-Blocker, keine Testfehler des
Account Lifecycles. Eine Optimierung wurde nicht vorgezogen.

## Manueller Smoke-Vertrag

Der Product Owner kann die sichtbaren Abläufe reproduzierbar mit zwei aktiven
Konten und je einem vollständig abgeschlossenen sowie einem laufenden Trade
prüfen:

1. **Deaktivieren:** Im eigenen Profil aktuelles Passwort eingeben und Konto
   deaktivieren. Erwartet: Logout; alte Session ist ungültig; normaler Login
   erzeugt noch keine Session.
2. **Reaktivieren:** Richtige Zugangsdaten eingeben. Erwartet: ausschließlich
   „Konto reaktivieren“; erst dessen Bestätigung erstellt die Session und das
   Konto ist wieder `active`.
3. **Laufender Trade:** Anonymisierung mit Passwort und Checkbox versuchen.
   Erwartet: keine Datenänderung und exakt
   „Dein Konto besitzt noch laufende Tauschaktionen. Bitte schließe diese
   zuerst vollständig ab.“
4. **Nur terminale Trades:** Laufenden Trade vollständig abschließen und erneut
   anonymisieren. Erwartet: Logout, keine Wiederherstellung und früherer
   Username kann neu registriert werden.
5. **Historie:** Mit dem Gegenkonto den abgeschlossenen Trade öffnen. Erwartet:
   Positionen, Timeline, Versand/Empfang, Probleme und Bewertungen bleiben;
   Partnername ist „Gelöschter Nutzer“.
6. **Ausschluss:** Login, Profil-URL, Suche, Matching und neue Interaktion für
   den anonymisierten Nutzer prüfen. Erwartet: kein Login, kein Profil, kein
   Such-/Matchtreffer und keine neue Anfrage.

Die HTTP-/Service-Happy-Paths und Fehlerfälle wurden automatisiert ausgeführt.
Es wird nicht behauptet, dass dieser separate visuelle Product-Owner-Smoke in
einem Browser bereits manuell abgenommen wurde.

## Bekannte Grenzen und Release Readiness

- Account Lifecycle, Datenschutzregeln, V0012, Integrität, Tests und
  Development-Start: grün
- S35-Performance-Baseline: vollständig und reproduzierbar
- Public-Beta-Release: **blockiert** durch die ausgewiesenen P95- und
  Fehlerquotenverstöße
- Datenexport: nur technische Grundlage; kein Download, ZIP oder UI
- S34-Backups bleiben unverändert ihrem bestehenden Retentionsvertrag
  unterworfen
- Performanceoptimierung und erneute Baseline benötigen einen gesondert
  priorisierten Auftrag; sie sind kein stillschweigender Teil von S35

## Offene Punkte für S36

S36 wurde nicht begonnen. Es wurden keine S36-Fachentscheidungen oder
Vorarbeiten vorgenommen. Die Performance-Release-Blocker müssen vor einer
Public Beta separat priorisiert und nach einer freigegebenen Behebung mit dem
identischen Baselinevertrag erneut gemessen werden.

## Scope-Bestätigung

- ausschließlich S35 umgesetzt
- keine Arbeiten an S36 begonnen
- keine lokale Entwicklungsdatenbank oder S00-Fixture migriert
- keine produktiven Daten verändert
- kein Commit erstellt
- kein Push durchgeführt
