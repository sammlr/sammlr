# Sprintbericht S13 – Versionierte Migrationen und Lifecycle-Grundschema

Stand: 2026-08-01

## Ergebnis

Sprint S13 wurde ausschließlich als versionierte Schema- und
Migrationsgrundlage umgesetzt. Der neue Migration Runner kann das
Lifecycle-Grundschema vorwärts, wiederholt und rückwärts auf leeren temporären
Datenbanken sowie Kopien der S00-Fixture ausführen.

Das bestehende `trade_requests`-Modell bleibt alleinige aktive Produktquelle.
Der heutige Tradeflow, abgeschlossene Trades, JSON-Tradepakete und die sichtbare
Historie wurden nicht verändert. Das neue Grundschema enthält nach der Migration
keine automatisch übernommenen Trade-, Positions- oder Eventdaten.

## Neue Dateien

- `App/Database/migration_runner.py`
  - expliziter versionierter SQLite-Migrationsmechanismus
  - Migrationsledger und Prüfsummenprüfung
  - Vorwärts- und Backout-Ausführung
  - CLI mit verpflichtendem Datenbankpfad
- `App/Database/migrations/0001_trade_lifecycle_foundation.up.sql`
  - Lifecycle-Grundschema
- `App/Database/migrations/0001_trade_lifecycle_foundation.down.sql`
  - verlustfreier S13-Backout
- `tests/test_s13_trade_lifecycle_schema.py`
  - isolierte Migrations-, Backout- und Kompatibilitätstests
- `Dokumentation/Product Bible/roadmap/s13-trade-lifecycle-schema.md`
  - Schema-, Migrations- und Backout-Entscheidung
- `Dokumentation/Product Bible/roadmap/sprint-reports/S13-report.md`
  - dieser Sprintbericht

## Geänderte Dateien

- `Dokumentation/Product Bible/roadmap/README.md`
  - Verweise auf S13-Spezifikation und S13-Sprintbericht ergänzt

Keine Route, kein Template, keine CSS-Datei und kein bestehender Trade-,
Inventory- oder Notification-Schreibpfad wurde für S13 geändert. Bereits
vorhandene sachfremde Änderungen im Arbeitsverzeichnis wurden nicht S13
zugerechnet und nicht zurückgesetzt.

## Migrationskonzept

Der zentrale Runner lädt paarige, aufsteigend versionierte
`*.up.sql`-/`*.down.sql`-Dateien. Erfolgreich angewendete Versionen werden in
`schema_migrations` mit Version, Name, SHA-256-Prüfsumme und Zeitpunkt erfasst.

Eigenschaften:

- kein impliziter Pfad zur Produktivdatenbank,
- keine automatische Ausführung beim Anwendungsimport oder Request,
- explizite Testkopie als Ziel,
- bereits angewendete Versionen sind beim Wiederholungslauf No-ops,
- veränderte bereits angewendete Migrationsdateien werden als Drift abgewiesen,
- Vorwärtsmigration und Ledger-Eintrag teilen dieselbe Transaktion,
- Backout läuft in umgekehrter Reihenfolge,
- `PRAGMA user_version` bleibt unverändert.

Vorwärtsbefehl für eine Kopie:

```text
python3 -m App.Database.migration_runner up --database /absoluter/pfad/zu/testkopie.db
```

Backout auf den Zustand vor S13:

```text
python3 -m App.Database.migration_runner down --database /absoluter/pfad/zu/testkopie.db --target 0
```

Die historische Bootstrap-Logik der bestehenden Anwendung wurde aus
Kompatibilitätsgründen nicht refaktoriert. Alle mit S13 neu eingeführten
Schemaänderungen befinden sich ausschließlich in der versionierten Migration.

## Lifecycle-Grundmodell

### Trade

`trades` stellt einen zukünftigen Lifecycle-Kopf bereit:

- optionale eindeutige Verbindung zu einem Legacy-Request,
- beide beteiligten Nutzer,
- noch nicht aktiv ausgewerteter `lifecycle_state`,
- Erstellungs-, Änderungs- und optionaler Abschlusszeitpunkt.

Es wurde keine neue State-Machine aktiviert und kein Statusübergang
implementiert.

### Trade Position

`trade_positions` beschreibt adressierbare, gerichtete Positionen anhand von
Trade, Absender, Empfänger, Album, Stickercode und positiver Menge. Diese
Granularität ist lediglich die spätere Reservierungsgrundlage. Es existieren
keine Reservierungstabelle, kein Reservierungsfeld und keine Availability-
Anbindung.

### Trade Event

`trade_events` kann später einen Ereignistyp, optionalen Akteur, optionales
JSON-Payload und den Ereigniszeitpunkt einem Trade zuordnen. S13 erzeugt keine
Events und definiert keine produktiven Eventtypen.

## Kompatibilität

`trade_requests` wurde weder im Schema noch in seinen Daten verändert. Die neue
optionale Spalte `trades.legacy_trade_request_id` ist ausschließlich ein späterer
Zuordnungsanker; S13 führt keinen Backfill und kein Dual Write aus.

Der bestehende S00-Referenztrade blieb vollständig lesbar:

- ID `1`,
- Status `completed`,
- `from_confirmed=1`,
- `to_confirmed=1`,
- `give_codes='["2"]'`,
- `get_codes='["4"]'`,
- unveränderter Erstellzeitpunkt.

Die Zeile wurde vor und nach Migration sowie nach Backout exakt verglichen. Die
neuen Lifecycle-Tabellen blieben bei der Fixture-Migration leer. Bestehende
Tradehistorie und alle bisherigen Tradeflow-Regressionstests blieben grün.

## Testübersicht

S13-spezifischer Testbefehl:

```text
python3 -m unittest tests.test_s13_trade_lifecycle_schema -v
```

Ergebnis: 9 von 9 Tests erfolgreich.

Geprüft wurden:

- Vorwärtsmigration einer leeren Datenbank,
- Vorwärtsmigration einer temporären S00-Fixture-Kopie,
- mehrfacher Lauf ohne erneute Schemaänderung,
- Lesbarkeit des bestehenden `completed`-Trades,
- Unverändertheit der JSON-Tradepakete,
- Backout auf das exakte Legacy-Schema und die Legacy-Daten,
- Backout auf eine wieder leere Datenbank,
- reproduzierbare Sequenz vorwärts → rückwärts → vorwärts,
- Tabellen, Positionen, Events und Zeitstempel des Grundmodells,
- Positionsconstraints als Grundlage ohne Reservierungen,
- unverändertes `PRAGMA user_version`,
- Schutz der Produktivdatenbank und der kanonischen S00-Fixture.

Vollständiges Testgate, zweimal ausgeführt:

```text
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Abschlusslauf 1: 154 von 154 Tests erfolgreich (`OK`).
- Abschlusslauf 2: 154 von 154 Tests erfolgreich (`OK`).

## Schutz der kanonischen Datenbanken

Die S13-Tests verwenden ausschließlich temporäre Datenbanken und Kopien. Vor
und nach beiden vollständigen Abschlussläufen waren die Prüfsummen identisch:

- `App/Database/sammlr.db`:
  `a6751d5324fe7a598f8f461efcc7ea8d8c3035dce9b8f6261b6b84fad3cc0abd`
- `App/Database/sammlr_reference_s00.db`:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`

Die bereits vor S13 im Arbeitsverzeichnis vorhandene benutzerverwaltete Änderung
an `sammlr.db` wurde nicht als Sprintänderung behandelt und nicht zurückgesetzt.

## Offene Punkte für S14

Folgende S14-Themen wurden lediglich abgegrenzt und nicht umgesetzt:

- atomare Erzeugung echter Reservierungen bei Tradeannahme,
- Availability-Recheck in derselben Transaktion,
- produktive Erzeugung beziehungsweise Zuordnung eines Lifecycle-Trades,
- Konflikt- und Idempotenzregeln bei paralleler oder wiederholter Annahme,
- Freigaberegeln für zukünftige Reservierungen.

Versand, Empfang, Notifications und UI bleiben ebenfalls späteren Sprints
vorbehalten.

## Scope-Bestätigung

- Ausschließlich Sprint S13 wurde umgesetzt.
- Sprint S14 wurde nicht begonnen.
- Es wurden keine Reservierungen implementiert.
- Es wurden keine Versand- oder Empfangszustände aktiviert.
- Es wurden keine UI- oder CSS-Änderungen vorgenommen.
- Es wurden keine Notificationänderungen vorgenommen.
- Der bestehende Tradeflow und alle sichtbaren Produktfunktionen blieben
  unverändert.
- Produktivdatenbank und S00-Fixture wurden nicht migriert oder verändert.
- Es wurde kein Commit erstellt und kein Push durchgeführt.
