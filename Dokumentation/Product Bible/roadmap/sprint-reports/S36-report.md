# Sprintbericht S36 – Datenexport und Compliance-Grundlagen

Stand: 2026-08-09

## Ziel und Ergebnis

S36 stellt einen echten, synchronen Datenexport bereit. Ein angemeldeter
aktiver Nutzer kann nach erneuter Passwortprüfung ein einzelnes,
menschenlesbar formatiertes UTF-8-JSON-Dokument mit seinen Sammlr-Daten direkt
herunterladen. Der Export bleibt read-only, wird nicht serverseitig
persistiert und verwendet keinen Hintergrundjob.

Zusätzlich existieren funktionale Seiten für Datenschutzerklärung, Impressum
und Exporthinweise. Die Texte sind ausdrücklich technische Grundlagen; ihre
juristische Endfassung bleibt einer späteren fachjuristischen Prüfung
vorbehalten.

S36 ist vollständig umgesetzt. Es wurde keine Migration erzeugt, keine
Retention- oder Anonymisierungsregel verändert, keine Performanceoptimierung
vorgezogen und keine Arbeit an S37 oder S38 begonnen.

## Geltungsrang

Die ältere Development Roadmap V1 beschreibt S36 noch als Accessibility- und
finalen Design-Patch. Die aktuelle ausdrückliche Product-Owner-Klärung vom
2026-08-09 definiert S36 stattdessen ausschließlich als Datenexport,
Compliance-Grundlagen und Exportarchitektur. Diese neuere verbindliche
Entscheidung wurde umgesetzt und im S36-Vertrag transparent dokumentiert; der
ältere Roadmaptext wurde nicht stillschweigend fachlich umgeschrieben.

## Architektur und Datenfluss

Der vollständige Vertrag steht in
`Dokumentation/Product Bible/roadmap/s36-data-export-compliance.md`.

```text
GET /profil/datenexport
  -> bestehender Session-/Accountguard
  -> Passwortformular + Exporthinweise

POST /profil/datenexport
  -> bestehender CSRF-Schutz
  -> AuthSecurityService.password_matches
  -> UserDataExportService.export_for_user(current_user_id)
  -> deterministisches UserDataExportDTO
  -> json.dumps(ensure_ascii=False, indent=2)
  -> direkter UTF-8 Attachment-Response
```

`UserDataExportService` ist die einzige Exportquelle. Der Service liest die
kanonischen Tabellen und erzeugt keine zweite Inventory-, Trade-, Rating-,
Privacy-, Community- oder Notificationlogik. Seine API mutiert nicht und ruft
weder `commit` noch einen Schreibservice auf.

## Exportstruktur

Das Dokument besitzt die stabilen Wurzelbereiche:

- `format_version` und `subject_user_id`
- `profile` und `account`
- `favorites`
- `albums` einschließlich `visibility` und `trade_pool_enabled`
- `inventory` mit Positionen, Quantity, Doppelte und Summen
- `trades` mit Legacy-Anfragen und Lifecycle-Historie
- `ratings`
- `notifications`
- `trophies`
- `community` mit Freundschaften, Anfragen, Blockierungen und Aktivität
- `login_security` mit personenbezogenen Login-Throttle-Daten des aktuellen
  Usernames

Lifecycle-Trades enthalten Positionen, Events, Reservierungen,
Versand-/Empfangsstatus sowie Problemreports und deren Positionen. JSON-Felder
wie Tradepakete und Eventpayloads werden für einen menschenlesbaren Export als
echte JSON-Strukturen ausgegeben.

Passwort, Passwort-Hash, Passwortschema, `auth_version`, Sessions, CSRF-Token,
Secrets und Observability-Daten sind ausgeschlossen.

## Berechtigungs- und Datenschutzgrenze

- Der ausführbare Exportweg ist nicht öffentlich und liegt nur im eigenen
  authentifizierten Profil.
- Ein anonymer GET wird zum Login umgeleitet.
- POST verlangt die bestehende Session, CSRF und das aktuelle Passwort.
- Ein falsches Passwort liefert HTTP 403 und erzeugt keinen Export.
- Exportiert werden nur direkte Eigentümerdaten oder Datensätze, an denen der
  Nutzer fachlich beteiligt ist.
- Andere Nutzer erscheinen ausschließlich als numerische Referenz in eigenen
  Trade- oder Communitybeziehungen. Fremde Profile, Namen, Usernames,
  Sammlungen und unabhängige Daten werden nicht zugeladen.
- Die öffentlichen Compliance-Seiten enthalten keinen ausführbaren
  Exportlink. Sie erläutern lediglich den geschützten Ablauf.

## Determinismus, UTF-8 und große Sammlungen

Alle Listen werden über fachliche Schlüssel und stabile IDs sortiert. Das
Dokument enthält keinen flüchtigen Exportzeitpunkt, sodass ein unveränderter
Datenbestand bytegleich exportiert wird. JSON nutzt `ensure_ascii=False`, zwei
Leerzeichen Einrückung und eine abschließende neue Zeile.

Der Großmengentest ergänzt isoliert 10.000 gültige Stickerpositionen und weist
nach, dass jede Position vollständig sowie in stabiler Reihenfolge exportiert
wird. Dieser Test ist eine Vollständigkeitsprüfung, keine vorgezogene
Performanceoptimierung.

## Neue Dateien

- `App/services/user_data_export.py`
- `tests/test_s36_user_data_export_compliance.py`
- `Dokumentation/Product Bible/roadmap/s36-data-export-compliance.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S36-report.md`

## Geänderte Dateien

- `App/webapp.py`: zentralen Exportservice eingebunden; geschützte
  GET-/POST-Exportroute, authentifizierten Profileinstieg sowie funktionale
  Datenschutz-, Impressums- und Exporthinweisseiten ergänzt.
- `Dokumentation/Product Bible/roadmap/README.md`: S36-Vertrag, Report und
  Abschlussstatus verlinkt.

Bereits vorhandene Änderungen früherer Sprints im Arbeitsverzeichnis wurden
nicht zurückgesetzt, gelöscht oder sachfremd bearbeitet.

## Unveränderte Komponenten

- S35 Account Lifecycle, Anonymisierung und Retention
- Inventory Read/Write, Availability und Snapshot
- Trade Lifecycle, Reservierung, Versand, Empfang und Probleme
- Coverage, TopMatch und Smart Requests
- Ratings, Privacy und Community-State-Machine
- Notificationtypen, -historie und -retention
- S32-/S33-Securityverträge
- S34 Backup, Recovery, Deployment und Observability
- Datenbankschema V0012
- lokale Entwicklungsdatenbank und S00-Fixture

## Testmatrix

| Anforderung | Nachweis |
| --- | --- |
| vollständiger Nutzer | alle Exportbereiche einschließlich Lifecycle-/Problemhistorie vorhanden |
| leerer Nutzer | vollständige stabile Struktur mit leeren Kategorien |
| große Sammlung | 10.000 zusätzliche Positionen vollständig und geordnet |
| Berechtigung | anonymer Export nicht erreichbar; nur aktuelle Nutzer-ID |
| Passwort | korrektes aktuelles Passwort erforderlich; falsch = HTTP 403 |
| CSRF | Export-POST ohne Token = HTTP 403 |
| JSON-Struktur | versioniertes Wurzeldokument und strukturierte JSON-Unterfelder |
| UTF-8 | Umlaute und Emoji bleiben direkt UTF-8-kodiert |
| deterministische Reihenfolge | zwei Exporte unveränderter Daten sind bytegleich |
| Datenabgrenzung | fremder Sticker, Klarname und Username fehlen |
| sensible Authdaten | Passwort, Hash, Schema, Auth-Version und CSRF fehlen |
| read-only | `connection.total_changes` bleibt beim Serviceaufruf unverändert |
| Compliance | alle drei Informationsseiten öffentlich erreichbar, kein öffentlicher Exportlink |
| Regression | vollständiges S01–S36-Gate zweimal grün |

## Testergebnisse

S36-spezifisch:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest tests.test_s36_user_data_export_compliance -v
```

Ergebnis: 7 von 7 Tests erfolgreich in 0,079 Sekunden.

Vollständiges Gate:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
  -m unittest discover -s tests -p "test_s*.py" -v
```

- Lauf 1: 517 von 517 Tests erfolgreich in 6,682 Sekunden
- Lauf 2: 517 von 517 Tests erfolgreich in 6,648 Sekunden
- übersprungene Tests: 0

Die bereits bekannten SQLite-`ResourceWarning`-Hinweise und zwei vorhandene
`SyntaxWarning`-Hinweise in `webapp.py` bleiben sichtbar, verursachen aber
keinen Fehler. Sie wurden wegen des engen S36-Scopes nicht fachfremd
refaktoriert.

## Technische Abnahme

- Python: CPython 3.13.15 aus dem freigegebenen Sammlr-Venv
- Syntaxprüfung: erfolgreich; nur die zwei bekannten Warnungen
- `git diff --check`: ohne Befund
- keine Migration; erwarteter Anwendungsschemastand bleibt V0012
- lokale Entwicklungsdatenbank: weiterhin V0007
- lokales `PRAGMA integrity_check`: `ok`
- lokales `PRAGMA foreign_key_check`: ohne Befund
- SHA-256 lokale Entwicklungsdatenbank unverändert:
  `db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`
- SHA-256 S00-Fixture unverändert:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`
- ausschließlich isolierte temporäre Testdaten verwendet

## Bekannte Grenzen und offene Product-Owner-Fragen

Es bestehen keine offenen Product-Owner-Fragen für den freigegebenen
S36-Umfang.

Bewusst verbleibende Grenzen:

- Datenschutzerklärung und Impressum sind technische Funktionsfassungen und
  benötigen vor öffentlicher Freigabe eine juristische Endprüfung sowie finale
  Betreiberangaben.
- Es gibt scopegemäß kein ZIP, keinen Hintergrundjob und keine serverseitig
  gespeicherte Exportdatei.
- Bestehende Retention, Backups und S35-Anonymisierung bleiben unverändert.
- Die in S35 dokumentierten Performance-Release-Blocker bleiben bestehen;
  S36 durfte und hat sie nicht optimiert.

## Release Readiness und Scope-Bestätigung

Der S36-Export- und Compliance-Umfang ist release-ready und vollständig
regressionsgeprüft. Die übergeordnete Public-Beta-Freigabe bleibt unabhängig
davon aufgrund der S35-Performance-Baseline blockiert.

- ausschließlich S36 umgesetzt
- keine UI-Politur oder Performanceoptimierung
- keine neue Community- oder Fachlogik
- keine Migration oder Datenbankänderung
- keine lokale Entwicklungsdatenbank oder Fixture verändert
- S37 und S38 nicht begonnen
- kein Commit erstellt
- kein Push durchgeführt
