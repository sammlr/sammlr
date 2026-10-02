# S32 – Authentifizierung, Secrets und CSRF

Stand: 2026-08-09

## Ziel und verbindlicher Scope

S32 schützt Nutzerkonten und bestehende schreibende POST-Aktionen vor der
Public Beta. Der Sprint umfasst ausschließlich Passwort-Hashing mit
kontrollierter Legacy-Migration, Secret- und Sessionkonfiguration,
sessiongebundenen CSRF-Schutz sowie persistentes Login-Throttling. Bestehende
Fachlogik, Routenbesitz und Produktzustände bleiben unverändert.

Mutierende GET-Routen werden in S32 ausschließlich inventarisiert. Ihre
Umstellung auf sichere HTTP-Methoden gehört verbindlich zu S33.

## Architektur

```text
SAMMLR_ENV + SAMMLR_SECRET_KEY
  -> Flask-Secret- und Cookievertrag
  -> signierte Browser-Session
     -> user_id + auth_version + csrf_token

POST Request
  -> globaler CSRF-Guard
  -> Login oder bestehende Auth-/Fachroute

Login
  -> AuthSecurityService
     -> LoginThrottleService (Username + Client-IP)
     -> Legacy/Kanonisch prüfen
     -> optional atomare Migration/Rehash
     -> Throttle-Reset
  -> alte Session vollständig löschen
  -> neue nicht permanente Session + neues CSRF-Token

Authentifizierter Request
  -> users.auth_version gegen Session prüfen
  -> Abweichung: Session löschen, erneuter Login
```

Die Security-Komponenten verwenden bestehende SQLite-Verbindungen. Es gibt
keine Kryptografie-Eigenimplementierung, keinen externen Identity Provider und
keinen externen Rate-Limit-Store.

## Passwortvertrag

- Kanonisches Verfahren:
  `werkzeug.security.generate_password_hash(..., method="scrypt:32768:8:1")`.
- Prüfung ausschließlich mit `check_password_hash(...)` für als
  `werkzeug_scrypt` gekennzeichnete Datensätze.
- Werkzeug-Standardsalt mit 16 Zeichen.
- Keine inhaltliche Hash-Heuristik: `users.password_scheme` ist die alleinige
  Quelle für `legacy_plaintext` oder `werkzeug_scrypt`.
- Neue Registrierungen speichern ausschließlich kanonische Hashes.
- Ein Legacy-Passwort wird nur nach erfolgreichem Klartextvergleich innerhalb
  derselben Auth-Transaktion überschrieben.
- Ein gültiger, aber nicht kanonisch parametrierter Werkzeug-Hash wird nur nach
  erfolgreicher Prüfung neu gehasht.
- Fehlgeschlagene Authentifizierung verändert weder Passwort noch Scheme.

## Migration V0010 und Backout

V0010 ergänzt `users` um:

- `password_scheme` mit ausschließlich `legacy_plaintext` und
  `werkzeug_scrypt`,
- `auth_version` als positive Ganzzahl mit Startwert `1`.

Bestehende Nutzer werden explizit als `legacy_plaintext` markiert. Zusätzlich
entsteht die persistente normalisierte Tabelle `login_throttle`, deren
Primärschlüssel aus normalisiertem Username und Client-IP besteht.

Der Backout ist fail-closed. Sobald ein Datensatz
`password_scheme='werkzeug_scrypt'` besitzt, verweigert die Down-Migration den
Backout. Sie stellt niemals Klartext wieder her, löscht keine Hashes und setzt
kein Passwort zurück.

## Secret- und Umgebungsvertrag

Verbindlicher Umgebungsname ist `SAMMLR_ENV`:

- `production`: `SAMMLR_SECRET_KEY` ist Pflicht; fehlt es, wird der Start
  verweigert.
- `testing`: ein explizit injiziertes festes Testsecret ist Pflicht.
- `development`: Der bestehende direkte lokale Entwicklungsstart
  `python3 App/webapp.py` wird ausdrücklich als Development erkannt. Alternativ
  kann `SAMMLR_ENV=development` gesetzt werden. Ein gesetztes Secret wird
  verwendet; andernfalls entsteht ein kryptografisch zufälliges, nur für
  diesen Prozess gültiges Secret und exakt der Hinweis
  `Temporary development secret active – sessions reset on restart.`
- Ein fehlender oder unbekannter Modus gilt nicht stillschweigend als
  Entwicklung.

Secrets werden weder in Code noch Dokumentation gespeichert. Es gibt keine
Secret-Fallback-Liste; ein bewusster Secretwechsel beendet bestehende Sessions.

## Sessionvertrag

- `SESSION_COOKIE_HTTPONLY=True`
- `SESSION_COOKIE_SAMESITE="Lax"`
- Produktion: `SESSION_COOKIE_SECURE=True`
- explizite lokale Entwicklung und Tests: `SESSION_COOKIE_SECURE=False`
- keine Domain-Weitung
- `session.permanent=False`

Nach erfolgreichem Login wird die gesamte vorherige Session gelöscht. Danach
werden ausschließlich `user_id`, `auth_version`, optional der bestehende
Username-Komfortwert und ein neu erzeugtes CSRF-Token gesetzt. Bei jedem
authentifizierten Request muss die Sessionversion der DB-Version entsprechen.

Eine erfolgreiche Passwortänderung erhöht `auth_version`, löscht die aktuelle
Session und verlangt einen erneuten Login. Accountlöschung löscht die Session
vollständig.

## CSRF-Modell

S32 verwendet einen sessiongebundenen Synchronizer-Token aus 32 sicher
zufälligen Bytes in hexadezimaler Darstellung. Serverseitig wird
constant-time verglichen.

- Schutzgrenze: jede produktive mutierende POST-Route.
- Übertragung: verstecktes Feld `_csrf_token` oder Header `X-CSRF-Token`.
- Fehlend oder falsch: HTTP 403 vor jeder Fachmutation.
- Token entsteht beim ersten Formular-GET und rotiert nach erfolgreichem
  Login.
- HTML-Formulare erhalten das versteckte Feld zentral in der
  Response-Projektion; der vorhandene Stickerwall-Fetch nutzt den Header.
- Es gibt keine pauschale Debug- oder API-Ausnahme.

Der Testclient reicht bei bestehenden Regressionen denselben echten Token mit
ein. S32-Negativtests können diese Testhilfe ausdrücklich abschalten; dies ist
keine produktive CSRF-Ausnahme.

## Login-Throttling

Schlüssel:

```text
normalisierter Username + Client-IP
```

Regeln:

- Versuche 1–5 innerhalb von 15 Minuten werden normal als fehlgeschlagen
  behandelt.
- Danach gilt für exakt diese Kombination eine 15-minütige Sperre.
- Ein Request während der Sperre liefert HTTP 429 und ausschließlich
  „Anmeldung momentan nicht möglich. Bitte versuche es später erneut.“
- Ein erfolgreicher Login setzt den Datensatz dieser Kombination sofort
  zurück.
- Username und IP werden für Tests über stabile Eingaben beziehungsweise
  injizierbare Provider geliefert; die Clock ist injizierbar.
- Throttling schreibt keine S29-User-Activity.

Unbekannte und bekannte Nutzernamen erhalten bei falschen Zugangsdaten
denselben sichtbaren Text: „Benutzername oder Passwort ist falsch.“
Registrierungsfehler werden ausschließlich als „Registrierung nicht möglich.
Bitte prüfe deine Angaben.“ ausgegeben.

## Sensible Kontoaktionen

Passwortänderung und Accountlöschung verlangen das aktuelle Passwort erneut.
Ein falscher Wert liefert ausschließlich „Passwort konnte nicht bestätigt
werden.“ und erzeugt keine Mutation.

## Mutierende GET-Restlücken für S33

Folgende vorhandene GET-Pfade verändern heute persistente Daten oder
Sessionzustand und sind deshalb ausdrücklich nicht als CSRF-geschützt zu
behaupten:

- `/debug-seed-now` – ersetzt eine Datenbankdatei,
- `/logout` – löscht die Session,
- `/favorit/toggle/<album_id>` und `/favorit/setzen/<album_id>`,
- `/alben/hinzufuegen/<album_id>`,
- `/add/<album_id>/<code>`, `/remove/<album_id>/<code>` und `/undo`,
- `/notifications/<id>/open` und `/notifications/<id>/read`,
- bestehende lazy Notification-Fristprojektionen auf Home, Tradeübersicht,
  Deal- und Notificationansicht,
- vorhandene Startup-Schreibarbeit in `init_db()`.

Die Trade-GET-Aliasse für Accept, Decline, Confirm und Cancel führen nur noch
zu Hinweisen und mutieren den Trade nicht. S32 ergänzt keine neue mutierende
GET-Route und verschiebt keine der genannten Routen vorzeitig auf POST.

## Berechtigungen, Datenfluss und Seiteneffekte

CSRF ersetzt keine Authentifizierung und keine Objektberechtigung. Nach dem
globalen Requestguard bleiben sämtliche bestehenden Fachprüfungen in ihren
Routen und Services verbindlich. Auth-Schreibvorgänge betreffen ausschließlich
Passworthash, Scheme, Auth-Version und den passenden Throttle-Datensatz.

Unverändert bleiben Inventory, Trade Lifecycle, Snapshot, Coverage, TopMatch,
Smart Requests, Shipping, Receipt, Problems, Ratings, Notifications als
Fachsystem, Operational Home, Privacy, Community und S31-Darstellung.

## Bekannte Risiken und Schutzmaßnahmen

- Aussperrung: Legacy-Login und Rehash werden auf V0010-Kopien getestet; bei
  Fehlern erfolgt keine Passwortmutation.
- Rollback: irreversible sichere Hashes blockieren den Down-Lauf.
- CSRF-Regression: alle bestehenden POST-Happy-Paths laufen mit echtem Token
  durch das vollständige Gate.
- Enumeration: Login-, Registrierung- und Throttle-Texte sind unabhängig von
  Benutzerexistenz.
- Proxy-IP-Vertrauen: S32 verwendet bewusst `request.remote_addr` und vertraut
  ohne spätere Betriebskonfiguration keinem beliebigen Forwarded-Header.
- Mutierende GETs bleiben als offenes S33-Risiko ausdrücklich sichtbar.

## Nicht enthalten

SSO, OAuth, MFA, Passkeys, E-Mail-Passwortreset, externe Rate-Limit-
Infrastruktur, Debugroutenbereinigung, Umstellung mutierender GETs,
Datenbank-Constraints außerhalb V0010 und alle Arbeiten an S33.

## Verbindliche lokale Python-Runtime

Sammlr S32 wird lokal mit dem offiziellen CPython 3.13 ausgeführt. Der bei der
Abnahme verwendete Interpreter ist:

```text
/usr/local/bin/python3.13
Python 3.13.15
hashlib.scrypt: True
```

Das macOS-System-Python unter `/usr/bin/python3` bleibt unverändert. Die
Projektabhängigkeiten wurden für die Abnahme ausschließlich in einer mit
Python 3.13 erzeugten, isolierten virtuellen Umgebung installiert. Ein lokaler
Development-Start ohne `SAMMLR_SECRET_KEY` ist nur im expliziten
Development-Modus zulässig und muss den dokumentierten temporären-Secret-Hinweis
ausgeben.
