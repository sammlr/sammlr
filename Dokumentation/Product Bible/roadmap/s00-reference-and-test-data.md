# S00 – Referenzstand und Testdatenstrategie

| Feld | Wert |
| --- | --- |
| Status | S00-Artefakt |
| Stand | 2026-07-28 |
| Verbindliche Grundlage | [Development Roadmap V1, Sprint S00](development-roadmap-v1.md#s00--referenzstand-und-testdatenstrategie) |
| Anwendungscode | unverändert |
| Bestehende Datenbanken | unverändert |

Diese Notiz dokumentiert ausschließlich den reproduzierbaren,
datenschutzgerechten Ausgangspunkt aus Sprint S00. Sie definiert keine Tests,
Schemaänderungen oder Produktfunktion.

## Referenzstand

| Merkmal | Referenz |
| --- | --- |
| Repository-Branch bei Sprintbeginn | `feature/wm-special-trophies` |
| HEAD bei Sprintbeginn | `4ecb92f0ba5755535798c5b235f0915a07739ef4` |
| vorhandene Beschreibung | `boerse-v1-31-g4ecb92f-dirty` |
| aktiver Einstieg | `App/webapp.py` |
| Standard-Datenbank | `App/Database/sammlr.db` |
| Standard-Startbefehl | `python3 App/webapp.py` |
| lokale Zieladresse | `http://127.0.0.1:8080` |
| Python bei S00-Prüfung | `3.9.6` |
| Flask bei S00-Prüfung | `3.1.3` |
| SQLite bei S00-Prüfung | `3.51.0` |

Der Arbeitsbaum war bereits vor S00 nicht sauber. Insbesondere waren
`App/webapp.py` und mehrere `.DS_Store`-Dateien geändert; die Product-Bible-
Dokumentation lag unversioniert vor. S00 erklärt diese Änderungen nicht zu
einem neuen Referenz-Commit und verändert sie nicht.

### Referenz-Commit- und Tag-Konvention

- Der fokussierte S00-Abschlusscommit trägt gemäß Roadmap die Nachricht
  `test: establish anonymized sammlr reference fixture`.
- Ein Referenztag wird erst auf einem bewusst freigegebenen, sauberen Commit
  gesetzt.
- Format: `sammlr-reference-s00-vN`, beginnend mit
  `sammlr-reference-s00-v1`.
- Ein gesetzter Referenztag wird nicht verschoben. Korrekturen erhalten die
  nächste Versionsnummer.
- Commit-ID, Tag und Fixture-Prüfsumme werden bei einer Freigabe gemeinsam in
  dieser Notiz aktualisiert.

In S00 wurde weder ein Commit noch ein Tag erzeugt, weil sachfremde,
vorbestehende Änderungen im Arbeitsbaum liegen.

## Aktiver Einstieg und Datenbankauswahl

`App/webapp.py` ist der aktive lokale Einstieg. Ohne Konfiguration öffnet die
Anwendung `App/Database/sammlr.db`. Für einen isolierten Lauf akzeptiert sie
den Pfad aus der Umgebungsvariable `DATABASE_PATH`.

Ein S00-Lauf verwendet immer eine Arbeitskopie der Fixture:

```sh
s00_run_db="$(mktemp /private/tmp/sammlr-s00-run.XXXXXX)"
cp App/Database/sammlr_reference_s00.db "$s00_run_db"
DATABASE_PATH="$s00_run_db" python3 App/webapp.py
```

Damit greift der Lauf weder auf die Standard-Datenbank noch auf eine
Produktivdatei zu. Die kanonische Fixture bleibt ebenfalls unverändert.

## Fixture-Artefakte

| Datei | Rolle | SHA-256 bei S00-Abschluss |
| --- | --- | --- |
| `App/Database/sammlr_reference_s00.sql` | kanonische, lesbare Quelle | `0477be18d41a6839954385c8400af9310c50024f5283ea98adaf0b135cda3ba5` |
| `App/Database/sammlr_reference_s00.db` | direkt nutzbare SQLite-Fixture | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` |

Die SQL-Quelle enthält absichtlich kein `DROP TABLE` und kein
`CREATE TABLE IF NOT EXISTS`. Sie ist ausschließlich für eine neue, leere
SQLite-Datei bestimmt und bricht bei einem bereits vorhandenen Schema ab.

### Inhalt und Mindestdatensätze

| Tabelle | Datensätze | S00-Zweck |
| --- | ---: | --- |
| `albums` | 3 | mehrere Albumkontexte |
| `users` | 3 | mehrere vollständig synthetische Nutzer |
| `user_albums` | 4 | unterschiedliche Albumzuordnungen |
| `stickers` | 10 | Mengen 1–4 und daraus abgeleitete Dubletten |
| `trade_requests` | 1 | vollständiger Trade mit Status `completed` |
| `notifications` | 2 | synthetische Abschlussmeldungen für beide Seiten |
| `unlocked_trophies` | 1 | bestehende Tabelle besitzt einen Mindestdatensatz |

Alle Primärschlüssel und Zeitstempel sind explizit gesetzt. Der Trade besitzt
die ID `1`, beide Bestätigungen stehen auf `1`, und die JSON-Listen lauten
deterministisch `["2"]` und `["4"]`. Die Stickermengen beschreiben den Zustand
nach diesem abgeschlossenen Trade.

## Datenherkunft und Datenschutz

Die Fixture ist keine Kopie und kein Auszug aus `sammlr.db` oder einem Backup.

- Tabellen- und Spaltenstruktur stammen aus einer rein lesenden
  Schemaabfrage von `App/Database/sammlr.db` und dem bestehenden `init_db()` in
  `App/webapp.py`.
- Album-IDs und öffentliche Album-Metadaten entsprechen den bereits
  vorhandenen Sammlr-Katalogkontexten.
- Trade-Status und JSON-Format wurden aus den bestehenden Lese- und
  Schreibpfaden technisch abgeleitet.
- Nutzer, Namen, Zugangsdaten, Besitzstände, Zeitstempel, Benachrichtigungen
  und der Trade wurden eigens für S00 erfunden.
- Die Fixture enthält keine E-Mail-Adresse, Anschrift, echte Kennung oder
  sonstige aus einer Produktivdatei übernommene Nutzerinformation.
- Vorhandene Seed-Dateien wurden geprüft, aber nicht wiederverwendet, weil sie
  Bestandsdateien verändern und keine isolierte Mehrnutzer-Referenzfixture
  darstellen.

## Reproduzierbare Neuerzeugung

Vom Repository-Wurzelverzeichnis aus:

```sh
s00_build_db="$(mktemp /private/tmp/sammlr-s00-build.XXXXXX)"
sqlite3 "$s00_build_db" < App/Database/sammlr_reference_s00.sql
sqlite3 "$s00_build_db" "PRAGMA integrity_check;"
shasum -a 256 "$s00_build_db"
```

Erwartet werden `ok` und, mit der bei S00 eingesetzten SQLite-Version, die oben
dokumentierte Datenbank-Prüfsumme. Die SQL-Datei ist die kanonische Quelle,
falls eine andere SQLite-Version ein binär abweichendes, aber inhaltlich
gleiches Dateilayout erzeugt.

## S00-Prüfnachweis

Die folgenden Prüfungen wurden manuell über die SQLite-CLI ausgeführt; es
wurden keine Testdateien oder Testfälle geschrieben.

| Prüfung | Ergebnis |
| --- | --- |
| `PRAGMA integrity_check` | `ok` |
| vorhandene Fachtabellen | exakt die sieben dokumentierten Tabellen |
| Mindestdatensätze | alle sieben Tabellen nicht leer |
| deterministische Nutzer-IDs | `1`, `2`, `3` |
| deterministische Trade-ID | `1` |
| vollständiger Trade | `completed`, beide Bestätigungen `1` |
| Mengenbandbreite | Minimum `1`, Maximum `4` |
| Neuaufbau aus SQL | inhaltlich erfolgreich |
| isolierte App-Vorbereitung | ausschließlich über Fixture-Arbeitskopie möglich |
| Standard-Datenbank verändert | nein |

### Wiederholbare Kontrollabfrage

```sh
sqlite3 -header -column App/Database/sammlr_reference_s00.db \
  "PRAGMA integrity_check;
   SELECT COUNT(*) AS users FROM users;
   SELECT COUNT(*) AS albums FROM albums;
   SELECT MIN(quantity), MAX(quantity) FROM stickers;
   SELECT id, status, from_confirmed, to_confirmed
   FROM trade_requests;"
```

Erwartet: `ok`, drei Nutzer, drei Alben, Mengen von `1` bis `4` sowie Trade
`1` mit `completed`, `1`, `1`.

## Zu schützende Dateien

- `App/Database/sammlr.db` bleibt die vorhandene Standard-Datenbank und wird
  für Fixture-Läufe nicht geöffnet.
- Datenbanken in `App/Database/Database:Backups` und `Backups` bleiben
  unverändert.
- `App/Database/sammlr_reference_s00.db` ist die kanonische Fixture und wird
  vor einem Lauf kopiert.
- Der synthetische abgeschlossene Trade in der Fixture ist der reproduzierbare
  Referenzfall; ein realer abgeschlossener Trade wurde weder gelesen noch
  kopiert.

## Offene Beobachtungen für spätere Sprints

Diese Punkte wurden in S00 ausdrücklich nicht bearbeitet:

- Es existiert noch keine eigenständige automatisierte Teststruktur. Das
  Schreiben von Regressionstests gehört ab S01 in die Roadmap.
- Der Arbeitsbaum enthält vorbestehende, sachfremde Änderungen. Ein
  Referenztag benötigt später einen bewusst freigegebenen sauberen Commit.
- Die aktive Schemaanlage liegt in `App/webapp.py`; bestehende Datenbanken
  zeigen historisch gewachsene Spaltenreihenfolgen. S00 ändert oder
  vereinheitlicht das Schema nicht.
- `requirements.txt` nennt Abhängigkeiten ohne Versionsbindung. S00 verändert
  das Abhängigkeitsmanagement nicht.
- Mehrere historische Datenbank- und Seed-Dateien liegen in Backup-Bereichen.
  S00 bewertet, bereinigt oder migriert diese Dateien nicht.
- Der bestehende Standardnutzer und bestehende Zugangsdaten im
  Anwendungscode sind kein Bestandteil der Fixture-Strategie. Eine
  Security-Bearbeitung ist ausdrücklich nicht Teil von S00.

## S00-Abgrenzung und Abschluss

Erstellt wurden nur die synthetische Fixture, ihre kanonische SQL-Quelle und
diese technische Referenznotiz. Es wurden keine Tests, Features,
Security-Änderungen, Navigation, Inventory- oder Trade-Engine-Arbeiten
vorgezogen. Anwendungscode, Templates, Styles, JavaScript und bestehende
Datenbanken blieben unverändert.
