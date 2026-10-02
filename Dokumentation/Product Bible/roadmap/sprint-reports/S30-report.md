# Sprint-Report S30

Stand: 2026-08-09

## Ziel und Scope

S30 führt das verbindliche Sammlr-Designfundament ein und migriert
ausschließlich Home, Sammlung, Album, Tauschbörse, Dealansicht, Notifications
und Profil auf diese tokenbasierte Sprache. Es wurden keine Fachfunktion, kein
Layoutablauf, keine Navigation, kein Header und kein Icon verändert. S31 wurde
nicht begonnen.

## Architektur und Datenfluss

Das Fundament besteht aus zentralen CSS Custom Properties und einer engen
Referenzseiten-Grenze:

```text
S30 Tokenvertrag
  -> :root Design Tokens
  -> semantische Komponentenregeln
  -> .s30-reference-page
  -> sieben bestehende Flask-Seiten
```

Die bestehenden Routen ergänzen ausschließlich eine Seitenklasse. Der
fachliche Datenfluss bleibt vollständig unverändert. Es gibt keine neuen DTOs,
Services, APIs, Reads, Writes oder Seiteneffekte. Header, Bottom-Navigation und
deren Inhalte sind in den S30-Selektoren ausdrücklich ausgeschlossen.

Die vollständige Design- und Scope-Beschreibung steht in
[`s30-design-foundation.md`](../../design-system/s30-design-foundation.md).

## Neue Komponenten und Token

Das Fundament definiert:

- die sieben verbindlichen Typografiestufen,
- das 8-Pixel-Abstandssystem mit den freigegebenen Zwischenstufen,
- fünf Radien,
- exakt drei Schattentokens,
- `#7C3AED` als einzige Corporate-Primärfarbe,
- AA-geprüfte Statusfamilien für fehlend, vorhanden, doppelt, unterwegs,
  offen, erfolgreich, Warnung, Fehler und deaktiviert,
- Primary-, Secondary-, Tertiary- und Danger-Buttons,
- Standard-, Interactive-, Status- und Empty-Karten,
- Input, Select, Checkbox, Radio und Textarea,
- Success-, Warning-, Error- und Info-Feedback,
- sichtbare Fokuszustände und Reduced-Motion-Verhalten.

Die vorhandenen Produktkomponenten bleiben die Referenz; ein separater
Komponentenkatalog wurde nicht gebaut. Offensichtliche leere Zustände auf Home
und Notifications erhielten ausschließlich Links auf bereits bestehende
Einstiege.

## Betroffene Komponenten

- Home: Aufgaben-, Trade-, Placeholder- und Empty-Karten.
- Sammlung: Albumkarten, Fortschritt und vorhandene Einstiegsaktionen.
- Album: Fortschritt, Quick Cards, Sticker-/Statusdarstellung und Formcontrols.
- Tauschbörse: Tabs, Albumgruppen, Partnerkarten und vorhandene Aktionen.
- Dealansicht: Papierfläche, Status, Timeline, Formulare, Modale und Aktionen.
- Notifications: Historienkarten, Status, Aktionen, Pagination und Empty State.
- Profil: Identität, Kennzahlen, Albumkarten, Bewertung und Communitykarten.

## Unveränderte Komponenten

- globaler Header,
- dreiteilige Bottom-Navigation,
- sämtliche bestehenden Icons,
- DOM-Reihenfolge und Seitenlayout,
- Inventory und Inventory Services,
- Trade Lifecycle, Versand, Empfang und Problemfälle,
- Shared Availability Snapshot, Coverage, TopMatch und Smart Requests,
- Notification-Fachsystem und Operational Home,
- Profile, Privacy, Ratings und Communitylogik.

## Dateien

Neu:

- `Dokumentation/Product Bible/design-system/s30-design-foundation.md`
- `tests/test_s30_design_foundation.py`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S30-report.md`

Geändert:

- `App/static/style.css`
- `App/webapp.py`
- `Dokumentation/Product Bible/roadmap/README.md`

In `style.css` wurde das frühere Corporate-Lila `#5D2F86` entsprechend der
verbindlichen Product-Owner-Entscheidung vollständig durch `#7C3AED` ersetzt.
Die eigentliche Komponenten- und Tokenmigration bleibt auf die S30-
Referenzseiten begrenzt.

## Testmatrix

| Bereich | Abdeckung |
|---|---|
| Tokenvertrag | Typografie, Abstände, Radien, Schatten und Primärfarbe exakt |
| Statusfarben | Vordergrund-/Flächenpaare rechnerisch mindestens WCAG 2.2 AA |
| Komponenten | Buttons, Karten, Formulare, Feedback, Empty State, Modal |
| Scope | exakt sieben Seitenmarker; Header und Navigation ausgeschlossen |
| Hardcodes | keine Farb-Hardcodes außerhalb des zentralen S30-Tokenblocks |
| Mobile | explizite Referenzbreiten 390 px und 430 px |
| Accessibility | Fokusindikator, native Controls, Reduced Motion, Kontrast |
| Flask | sieben reale GET-Pfade liefern HTTP 200 und behalten ihre Shell |
| Seiteneffekte | Inventory-, Trade- und Reservationstabellen bleiben unverändert |
| Regression | vollständige S01–S30-Suite zweimal |

## Testergebnisse

S30-spezifisch:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s30_design_foundation -v
```

Ergebnis: **8 Tests, alle erfolgreich**.

Der übergebene Platzhalter `python3 -m unittest tests.test_s30_* -v` ist als
unquotierter zsh-Dateiglob nicht direkt ausführbar. Daher wurde das konkrete
S30-Modul ausgeführt.

Vollständiges Gate, zweimal:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

- Lauf 1: **453 Tests, alle erfolgreich**, 4,875 s.
- Lauf 2: **453 Tests, alle erfolgreich**, 4,927 s.

Zusätzlich erfolgreich:

- bytecodefreier AST-Syntaxcheck für `App/webapp.py` und den S30-Test,
- `git diff --check`,
- `PRAGMA integrity_check`: `ok`,
- `PRAGMA foreign_key_check`: keine Befunde.

## Release Readiness

- S30 benötigt keine Migration und erzeugt keine Migration.
- Aktuell vorhandene höchste Migration im Repository: V0009.
- Lokale Entwicklungsdatenbank: V0007; sie wurde für S30 weder migriert noch
  als Testziel verwendet.
- SHA-256 lokale Entwicklungsdatenbank bei Abschluss:
  `5131bbdceffa239ea9fd8e9e4b32cfd93f8a7d6a87dcc3b74416efac10815e05`.
- SHA-256 kanonische S00-Fixture:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Sämtliche neuen Tests laufen ausschließlich auf temporären S00-Kopien und
  sichern lokale Datenbank sowie kanonische Fixture gegen Veränderung.
- Die vollständigen Gates blieben ebenfalls ohne Hashänderung innerhalb ihrer
  jeweiligen Testläufe. Der lokale Hash unterscheidet sich vom Wert des
  vorherigen S29-Reports. Kein S30-Implementierungs- oder Migrationsbefehl hatte
  die lokale Datenbank als Ziel; mangels eines zu Turnbeginn erzeugten Backups
  wird der laufende lokale Stand nicht spekulativ zurückgesetzt.

Damit ist S30 technisch releasebereit. Die Referenzseiten bilden das Fundament
für die spätere, ausdrücklich nicht vorgezogene globale Migration in S31.

## Bekannte Grenzen und offene Punkte für S31

- Nicht referenzierte Produktseiten verwenden weiterhin die historischen CSS-
  Schichten.
- Header, Navigation und Icons sind weiterhin absichtlich unverändert.
- Eine globale Bereinigung historischer Selektoren und Hardcodes ist S31.
- Es gibt bewusst keinen separaten Komponentenkatalog und kein
  Animationssystem.
- Tabletoptimierung, großes Redesign und Layoutreorganisation wurden nicht
  begonnen.

## Scope-Bestätigung

- Ausschließlich S30 wurde umgesetzt.
- S31 wurde nicht begonnen oder vorbereitet.
- Es wurden keine Produktentscheidungen über die Product-Owner-Klärung hinaus
  getroffen.
- Es wurden keine Fachlogik, kein Datenbankschema, keine Migration, keine
  Services, Header, Navigation oder Icons verändert.
- Es wurde kein Commit erstellt.
- Es wurde kein Push durchgeführt.
