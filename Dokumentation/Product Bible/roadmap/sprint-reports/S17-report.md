# Sprintbericht S17 – Problemfälle und Teilempfang

Stand: 2026-08-03

## Ergebnis

Sprint S17 wurde ausschließlich im vorgegebenen Umfang umgesetzt. Ein
Empfänger kann je erwarteter Tradeposition die physisch korrekt erhaltene
Menge dokumentieren. Nur diese Menge wird über den bestehenden Inventory Write
Service gebucht. Fehlende, falsche, beschädigte oder verlorene Restmengen
bleiben ungebucht, als Transit offen und historisch sichtbar.

Ein offener Bericht hält Lifecycle und Legacy-Trade offen. Die minimale
Auflösung bucht ausschließlich die noch offene erwartete Restmenge. Erst wenn
beide Seiten vollständig empfangen haben und kein Problem offen ist, wird der
kontrollierte S16-Abschluss mit den bestehenden Trophy- und Notification-Hooks
ausgeführt. Der direkte S16-Weg „Alles vollständig erhalten“ bleibt erhalten.

## Neue Dateien

- `App/Database/migrations/0005_trade_problems_partial_receipt.up.sql`
  - versionierte Berichte und Positionen für Teilempfang/Problemhistorie
- `App/Database/migrations/0005_trade_problems_partial_receipt.down.sql`
  - leerer Backout und fail-closed Schutz bei vorhandener Historie
- `App/services/trade_problems.py`
  - atomarer Problem-/Teilempfangsservice, DTOs und stabile String-Enums
- `tests/test_s17_trade_problems_partial_receipt.py`
  - 27 S17-Service-, Inventory-, UI-, Migrations- und Legacy-Tests
- `Dokumentation/Product Bible/roadmap/s17-trade-problems-partial-receipt.md`
  - verbindliche Problemfall-, Mengen-, Lifecycle- und Supportgrenzen
- `Dokumentation/Product Bible/roadmap/sprint-reports/S17-report.md`
  - dieser Sprintbericht

## Geänderte Dateien

- `App/services/inventory.py`
  - eingehenden Transit um bereits korrekt gebuchte Anfangs- und
    Auflösungsmengen reduzieren
- `App/services/trade_receipt.py`
  - bestehenden Abschluss in eine gemeinsam genutzte seitenbezogene Funktion
    gekapselt; Abschluss zusätzlich gegen offene S17-Berichte geschützt
  - vollständigen S16-Empfang bei bereits offenem Bericht abgewiesen
- `App/services/trade_shipping.py`
  - zwingenden `problem_open`-Zustand bei einem späteren Versand bewahrt
- `App/webapp.py`
  - Problemstatus und unveränderliche Historie in Dealansicht/-liste angezeigt
  - schlichtes, mengenbegrenztes Problemformular sowie POST- und
    Auflösungsroute integriert
  - S16-Standardbutton eindeutig als „Alles vollständig erhalten“ belassen
- `Dokumentation/Product Bible/roadmap/README.md`
  - ausschließlich S17-Spezifikation und diesen Bericht verlinkt

Keine CSS-Datei wurde für S17 verändert. Bereits vorhandene, nicht committete
Änderungen aus S03–S16 und lokale Metadateien wurden weder S17 zugerechnet noch
zurückgesetzt.

## Problemfallmatrix und Buchungsregeln

Erlaubte Problemtypen sind ausschließlich:

- `missing`
- `wrong_sticker`
- `damaged`
- `shipment_lost`

Je erwarteter eingehender Position gilt
`0 <= correct_received <= expected`. Nur `correct_received` wird gebucht.
Falsch mitgesendete oder beschädigte Sticker werden nicht automatisch
übernommen. Bei einer vollständig verlorenen Sendung müssen alle Positionen
Menge 0 und `shipment_lost` tragen.

Alle erwarteten Positionen müssen genau einmal eingegeben werden. Freie
Ersatzcodes, fremde Positionen, fehlende oder doppelte Positionen und negative,
nicht-ganzzahlige oder überhöhte Mengen werden abgewiesen. Ein Trade mit
offenem Bericht bleibt `accepted`/`problem_open` und erzeugt weder Trophy noch
Abschlussnotification.

## Transit, Inventory und Auflösung

Die zentrale Transitprojektion berechnet die offene Menge je Position als:

```text
expected - initial_received_quantity - resolution_received_quantity
```

Damit werden bei 29 von 30 genau 29 Physical gebucht und 1 bleibt im Transit.
Availability, Assigned und Guard bleiben unter dem S08–S12-Vertrag. Bei der
minimalen späteren Auflösung werden ausschließlich die offenen erwarteten
Reste gebucht. Anfangsbuchung, Problemtyp, Erstellungszeitpunkt und Historie
bleiben unverändert.

## Lifecycle und Abschluss

Zulässige S17-Übergänge:

```text
partially_shipped/shipped/partially_received
  → Teil-/Problemempfang → problem_open
problem_open
  → Rest korrekt eingetroffen → partially_received oder completed
```

Ein späterer eigener Versand darf `problem_open` nicht verdecken. `completed`
entsteht ausschließlich, wenn beide Empfangsseiten vollständig bestätigt und
alle Berichte aufgelöst sind. Der gemeinsame S16-Abschluss setzt Legacy- und
Lifecycle-Status und löst die bestehenden Side Effects höchstens einmal aus.

## Stabile Ergebniszustände

- `FULLY_RECEIVED`
- `PARTIAL_RECEIPT_RECORDED`
- `ALREADY_IDENTICAL`
- `PROBLEM_RESOLVED`
- `INVALID_QUANTITY`
- `CONFLICTING_REPORT`
- `NOT_SHIPPED`
- `INVALID_TRADE_STATE`
- `UNAUTHORIZED`
- `TRANSACTION_ERROR`

Identische Retries verändern weder Bestand, Transit, Bericht, Zeitpunkte noch
Side Effects. Widersprüchliche Retries überschreiben die gespeicherte
physische Wahrheit nicht.

## Berechtigung, Atomarität und UI

Nur der anhand von Session und Lifecycle bestimmte tatsächliche Empfänger darf
seinen Eingang melden oder auflösen. Fremde Nutzer und der Absender für die
andere Seite werden abgewiesen. Versand der Gegenseite, empfangsfähiger Zustand
und vollständige erwartete Positionen sind zwingend.

Berechtigung, Validierung, Inventory-Buchung, Bericht, Transitprojektion,
Lifecycle und Event laufen in einer Transaktion. Ein injizierter technischer
Fehler wurde mit vollständigem Rollback geprüft.

Die Dealansicht verwendet die verbindlichen Texte:

- „Empfang bestätigen – Alles vollständig erhalten“
- „Problem melden / Lieferung unvollständig“
- „Sammlr entscheidet keine Schuldfrage.“

Das Formular enthält ausschließlich Expected, korrekt erhaltene Menge,
Problemtyp und das Kennzeichen für eine verlorene Gesamtsendung. Es enthält
keine Support-, Chat-, Bild-, Ersatzcode-, Bewertungs- oder Fristfelder.

## Migration V0005 und Backout

V0005 ergänzt `trade_receipt_reports` und
`trade_receipt_report_positions`. Datenbank-Constraints schützen Mengen,
Typen, Zustände, Zeitpunkte und die Eindeutigkeit je Trade/Empfänger/Position.
Legacy-Trades und vorhandene V0004-Zeilen werden nicht verändert. Wiederholte
Migration ist ein No-op. Der Backout funktioniert bei leerem S17-Modell und
scheitert bei vorhandener Problemhistorie absichtlich fail-closed.

Migration auf leerer Datenbank, kanonischer Fixture-Kopie, Wiederholung,
leerer Backout und verwendeter Backout wurden ausschließlich auf temporären
Datenbanken geprüft.

## Testübersicht

S17-spezifischer Befehl:

```bash
python3 -m unittest tests.test_s17_trade_problems_partial_receipt -v
```

Ergebnis:

```text
Ran 27 tests in 0.184s
OK
```

Vollständiges Gate, zweimal ausgeführt:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Ergebnisse:

```text
Lauf 1: Ran 243 tests in 0.896s – OK
Lauf 2: Ran 243 tests in 0.899s – OK
```

Abgedeckt sind alle 26 Pflichtfälle: schneller S16-Empfang, 29/30,
Transitanteil und offene Wahrheit, Menge 0 bei Verlust, Mengenvalidierung,
falsche/beschädigte/verlorene Sendung, Dealansicht/History, spätere Auflösung,
exakte Restbuchung, Abschlussinvariante, identischer und widersprüchlicher
Retry, Fremdnutzer/Absender, fehlender Versand, atomarer Fehlerrollback,
Trophy-/Notification-Einmaligkeit, Migration/No-op/Backout,
Legacy-Lesbarkeit und unveränderte kanonische Datenbanken. Ein zusätzlicher
Test fixiert Codes, Typen und die schlichte begrenzte UX.

## Lokale Release Readiness

Beim ersten Prozesscheck war kein lokaler Serverprozess sichtbar; der
anschließend auf Port 8080 identifizierte bestehende Debug-Server verwendete
laut Startkommando, Arbeitsverzeichnis und unverändertem Defaultpfad:

```text
/Users/valy/Desktop/sammlr./App/Database/sammlr.db
```

Vor der Migration wurde über die SQLite-Backup-API erstellt:

```text
/Users/valy/Desktop/sammlr./Backups/sammlr_local_pre_v0005_20260803_211622.db
```

- Stand vorher: V0004
- Backup-Integrität: `ok`
- ausgeführter Befehl:

```bash
python3 -m App.Database.migration_runner up --database '/Users/valy/Desktop/sammlr./App/Database/sammlr.db' --target 5
```

- Ergebnis: `Applied change set: (5,); current version: 5`
- Stand nachher: V0005
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: keine Befunde
- installierte Tabellen: `trade_receipt_reports`,
  `trade_receipt_report_positions`

Der lokale Debug-Server wurde gezielt beendet und neu gestartet. Eltern-/
Reload-Prozess liefen danach aus dem Projektwurzelverzeichnis mit
`App/webapp.py`; Port 8080 antwortete und die bestehende Dealansicht `/trades/27`
lieferte authentifiziert `HTTP 200` gegen V0005.

Die lokale Datenbank enthält derzeit keinen offenen, versendeten und noch nicht
empfangenen Lifecycle-Trade. Deshalb wurde für den read-only Live-Smoke bewusst
kein künstlicher lokaler Trade und keine Produktdatenänderung erzeugt. Die
Sichtbarkeit beider zustandsgebundenen Buttons wurde stattdessen im
S17-UI-Test auf einer isolierten, bis V0005 migrierten Fixture-Kopie geprüft;
derselbe App-Code und das V0005-Schema sind auf dem laufenden lokalen Server
aktiv.

Die kanonische S00-Fixture blieb unverändert:

```text
sammlr_reference_s00.db:
21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

Die neue und beide älteren Sicherungen blieben nach ihrer Erstellung
unverändert. `git diff --check` war ohne Befund.

## Offene Supportgrenzen und S18+

Nicht begonnen oder vorbereitet wurden:

- Fristen und Überfälligkeit,
- vollständige Lifecycle-Historie aus S18,
- Schuldentscheidung oder Beweisprüfung,
- Erstattung, Rücksendung, Ersatzlieferung oder Sanktion,
- Chat, Bilder oder Bewertung,
- Schiedsgericht, Supportautomation oder Versicherung,
- Tracking oder Versanddienstleister,
- Home-Aufgaben, Notification-Historie oder Design Patch.

## Scope-Bestätigung

- Ausschließlich Sprint S17 wurde umgesetzt.
- Sprint S18 wurde nicht begonnen.
- Die normale vollständige S16-Empfangsbestätigung bleibt geschützt.
- Es wurden keine Fristen, kein Chat und keine Bewertung ergänzt.
- Es wurden keine Schuldentscheidung, Supportautomation, Versicherung oder
  Schiedsgericht ergänzt.
- Es wurden keine CSS- oder Designänderungen vorgenommen.
- Kanonische Fixture, ältere Backups und andere Datenbankkopien wurden nicht
  migriert.
- Es wurde kein Commit und kein Push durchgeführt.
