# S13 – Versionierte Migrationen und Lifecycle-Grundschema

Stand: 2026-08-01

## Zweck und Sprintgrenze

S13 schafft eine kontrollierte, versionierte Grundlage für spätere
Trade-Lifecycle-Sprints. Das aktive Produktmodell bleibt in diesem Sprint
unverändert `trade_requests`. Die neuen Tabellen werden weder durch Routen noch
durch Trade-, Inventory- oder Notification-Code gelesen oder beschrieben.

S13 enthält ausdrücklich keine Reservierungen, Versand-/Empfangslogik,
Statusübergänge, UI oder automatische Übernahme von Legacy-Trades.

## Migrationsentscheidung

Neue Schemaentwicklung erfolgt ab S13 zentral über:

- `App/Database/migration_runner.py` für Planung, Ausführung, Ledger,
  Prüfsummenprüfung und Backout,
- `App/Database/migrations/<version>_<name>.up.sql` für Vorwärtsmigrationen,
- `App/Database/migrations/<version>_<name>.down.sql` für Backouts.

Der Runner verlangt immer eine explizite SQLite-Verbindung oder beim CLI-Aufruf
einen expliziten Datenbankpfad. Er besitzt keinen Standardpfad zur
Produktivdatenbank und wird nicht beim Import der Anwendung ausgeführt. Tests
arbeiten ausschließlich mit temporären leeren Datenbanken oder Kopien der
S00-Fixture.

Historische Bootstrap-Logik der bestehenden Anwendung bleibt aus
Kompatibilitätsgründen unverändert. Sie ist kein Erweiterungspunkt für neue
Schemaänderungen. Sämtliche mit S13 neu eingeführte Struktur liegt ausschließlich
in einer versionierten Migration.

## Versions- und Integritätsmodell

Die Tabelle `schema_migrations` enthält:

| Feld | Bedeutung |
| --- | --- |
| `version` | eindeutige, aufsteigende Migrationsversion |
| `name` | stabiler technischer Migrationsname |
| `checksum` | SHA-256 über Up- und Down-SQL |
| `applied_at` | Zeitpunkt der erfolgreichen Anwendung |

Bereits angewendete Versionen werden nicht erneut ausgeführt. Weichen Name oder
Prüfsumme später von der protokollierten Version ab, stoppt der Runner mit einem
Driftfehler. Eine angewendete Migration darf daher nicht nachträglich verändert,
sondern nur durch eine neue Version ergänzt werden.

Die S13-Version lautet:

```text
0001_trade_lifecycle_foundation
```

`PRAGMA user_version` wird nicht umgedeutet oder verändert; die bestehende
S00-Fixture behält ihren Wert `1`.

## Ausführung auf einer Kopie

Vorwärts bis zur neuesten Version:

```text
python3 -m App.Database.migration_runner up --database /absoluter/pfad/zu/testkopie.db
```

Backout bis vor S13:

```text
python3 -m App.Database.migration_runner down --database /absoluter/pfad/zu/testkopie.db --target 0
```

Der Pfad muss auf eine bewusst gewählte Testkopie zeigen. Ein wiederholter
Vorwärtslauf liefert eine leere Änderungsmenge und verändert weder Schema noch
Daten.

## Lifecycle-Grundmodell

### `trades`

Der neue technische Trade-Kopf enthält:

- eine eigene ID,
- die optionale eindeutige Verbindung `legacy_trade_request_id`,
- beide Beteiligten,
- `lifecycle_state` als noch nicht aktiv ausgewerteten Zustandswert,
- `created_at`, `updated_at` und optional `completed_at`.

S13 schreibt keine Zeilen in diese Tabelle. Insbesondere wird ein bestehender
`completed`-Trade nicht kopiert oder umgedeutet. Der Zustandswert bleibt in S13
bewusst ohne neue State-Machine; zulässige Übergänge gehören in spätere Sprints.

### `trade_positions`

Eine Position beschreibt die spätere fachliche Bewegungsrichtung eines
Stickerbestands:

- Trade,
- Absender und Empfänger,
- Album und Stickercode,
- positive Menge,
- Erstellzeitpunkt.

Die Kombination aus Trade, Richtung, Album und Stickercode ist eindeutig. Damit
ist eine adressierbare Positionsgrundlage vorhanden, ohne schon Bestand zu
binden. Es gibt keine Reservierungstabelle, kein Reservierungsfeld und keine
Availability-Anbindung.

### `trade_events`

Ein Event enthält:

- Trade,
- technischen Ereignistyp,
- optionalen Akteur,
- optionales JSON-Payload-Feld,
- `occurred_at`.

S13 erzeugt keine Events. Eventtypen, Idempotenzregeln und die produktive
Historienprojektion werden erst in späteren Lifecycle-Sprints festgelegt.

## Trade/Request-Kompatibilität

Das Legacy-Modell bleibt die einzige aktive Produktquelle:

```text
trade_requests
├── give_codes / get_codes (bestehende JSON-Pakete)
├── status
├── from_confirmed / to_confirmed
└── created_at
```

Die neue optionale Spalte `trades.legacy_trade_request_id` bildet lediglich den
späteren eindeutigen Anker für eine kontrollierte Zuordnung. In S13 gilt:

- keine automatische Zuordnung,
- keine Datenkopie,
- kein Dual Write,
- keine Änderung bestehender Statuswerte,
- keine Änderung der Tradehistorie,
- keine Änderung der JSON-Pakete.

Der S00-Trade mit `status='completed'`, beiden Bestätigungen und den Paketen
`["2"]` / `["4"]` bleibt vor, während und nach Vorwärtsmigration sowie Backout
bytegenau auf Zeilenebene lesbar.

## Transaktion und Wiederholbarkeit

Jede Ausführungsrichtung läuft innerhalb der SQLite-Transaktion der übergebenen
Verbindung. Der Ledger-Eintrag wird erst zusammen mit dem erfolgreichen Up-SQL
geschrieben. Beim Backout werden abhängige Tabellen in umgekehrter Reihenfolge
entfernt und anschließend der Ledger bereinigt.

Geprüfte Sequenzen:

```text
leer → V0001
Fixture → V0001
Fixture → V0001 → V0001 (No-op)
Fixture → V0001 → V0000
Fixture → V0001 → V0000 → V0001
```

## Backout-Plan

Für S13 ist der Backout verlustfrei, weil die Anwendung noch keine neuen
Lifecycle-Daten schreibt:

1. Nur mit einer gesicherten Datenbankkopie arbeiten.
2. Vorwärtsmigration ausführen.
3. Legacy-Trade, JSON-Pakete, Schema und Testgate prüfen.
4. Bei Abbruch `down --target 0` auf derselben Kopie ausführen.
5. Legacy-Schema und Legacy-Daten mit dem Zustand vor der Migration vergleichen.

Sobald spätere Sprints echte Lifecycle-Daten schreiben, darf dieser S13-Backout
nicht ungeprüft verwendet werden. Dann sind ein eigener Datenexport/-backfill und
eine neue versionierte Backout-Entscheidung erforderlich.

## Sicherheits- und Scope-Regeln

- Migrationstests dürfen niemals `App/Database/sammlr.db` als Ziel verwenden.
- Die S00-Fixture wird nur kopiert und nicht migriert.
- Keine Migration wird beim Anwendungsimport oder Request automatisch gestartet.
- Kein Legacy-Trade wird gelöscht, verändert oder automatisch dupliziert.
- Keine Reservierungs-, Versand-, Empfangs- oder Notificationlogik ist enthalten.
- Keine UI- oder CSS-Datei ist Bestandteil von S13.

## Offene Punkte für S14

Nicht in S13 umgesetzt:

- atomare Reservierung ausgehender Positionen bei Annahme,
- Availability-Recheck innerhalb derselben Transaktion,
- produktive Zuordnung eines Legacy-Requests zu einem Lifecycle-Trade,
- Idempotenz- und Konfliktregeln für die Annahme,
- Freigabe zukünftiger Reservierungen bei zulässigem Ende.
