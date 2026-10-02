# Sprintbericht S16 – Empfang je Seite und sichere Bestandsbuchung

Stand: 2026-08-02

## Ergebnis

Sprint S16 wurde ausschließlich im vorgegebenen Umfang umgesetzt. Jede
beteiligte Seite kann den vollständigen Empfang ausschließlich der an sie
gerichteten, zuvor von der Gegenseite versendeten Positionen bestätigen.

Der erste Empfang bucht nur den Bestand dieses Empfängers und hält den Trade
`accepted`/`partially_received`. Der zweite Empfang schließt den Legacy- und
Lifecycle-Trade ab. Alle Bestandsänderungen laufen über den bestehenden
Inventory Write Service; Retry, fremde Nutzer und ungültige Zustände erzeugen
keine Doppel- oder Teilbuchung.

## Neue Dateien

- `App/Database/migrations/0004_trade_receipt_status.up.sql`
  - versionierter Empfangsstatus je Seite
- `App/Database/migrations/0004_trade_receipt_status.down.sql`
  - leerer Backout und fail-closed Schutz nach erstem Empfang
- `App/services/trade_receipt.py`
  - atomarer, autorisierter und idempotenter Receipt-Service
  - Status- und Ergebnis-DTOs mit stabilen Codes
- `tests/test_s16_trade_receipt.py`
  - S16-Service-, Inventory-, UI-, Migrations- und Legacy-Tests
- `Dokumentation/Product Bible/roadmap/s16-trade-receipt.md`
  - Buchungsregeln, Zustände und Legacy-Mapping
- `Dokumentation/Product Bible/roadmap/sprint-reports/S16-report.md`
  - dieser Sprintbericht

## Geänderte Dateien

- `App/services/inventory.py`
  - eingehenden Transit nach bestätigtem Empfang ausschließlich der
    betreffenden Seite aus der Projektion entfernt
- `App/services/trade_shipping.py`
  - späteren eigenen Versand im bereits `partially_received` befindlichen
    Trade erlaubt und Empfangszustand dabei bewahrt
- `App/webapp.py`
  - Receipt-Service und POST-Route integriert
  - bestehende Dealansicht um den zustandsgebundenen Empfangsknopf ergänzt
  - Abschlussbenachrichtigungen als gemeinsam genutzten bestehenden Hook
    extrahiert
  - Trophy-Hooks ausschließlich nach dem zweiten Empfang ausgeführt
- `tests/test_s15_trade_shipping.py`
  - abgeschlossenen S15-Vertrag explizit auf Zielversion V0003 fixiert
- `Dokumentation/Product Bible/roadmap/README.md`
  - ausschließlich S16-Spezifikation und Bericht verlinkt

Es wurde keine CSS-Datei für S16 verändert. Bereits vorher vorhandene
Arbeitsbaumänderungen wurden weder S16 zugerechnet noch zurückgesetzt.

## V0004 und Lifecycle

`trade_receipt_status` speichert je Lifecycle-Trade:

- `requester_received` plus ersten Zeitpunkt,
- `partner_received` plus ersten Zeitpunkt,
- `updated_at`.

Bestehende V0003-Lifecycle-Trades werden mit zwei offenen Empfangsmarkern
übernommen. Ein Backout ist nur ohne reale Empfangsbuchung möglich.

Erlaubte fachliche Übergänge:

```text
partially_shipped/shipped
  → erster Empfang  → partially_received / Legacy accepted
  → zweiter Empfang → completed / Legacy completed
```

Wenn eine Gegensendung bereits eingetroffen ist, bevor der Empfänger selbst
versendet hat, bleibt der Lifecycle auch nach dem späteren eigenen Versand
`partially_received`.

## Sichere Bestandsbuchung

Eine Seite darf ausschließlich bestätigen, wenn:

- sie Teilnehmer und tatsächlicher Empfänger ist,
- die Gegenseite ihren Versand bestätigt hat,
- Legacy- und Lifecycle-Zustand empfangsfähig sind,
- vollständige Lifecycle-Positionen für sie existieren.

Alle eingehenden Positionen werden gemeinsam über
`InventoryWriteService.add()` gebucht. Es gibt weder Positionseingabe noch
Teilmenge. Danach gilt für diese Seite:

- `incoming_transit = 0`,
- `physical` steigt um die Positionsmenge,
- `assigned` wird weiterhin aus Physical korrekt abgeleitet,
- `available` bleibt nichtnegativ und höchstens Physical,
- Fortschritt wird aus der zentralen Inventory-Projektion aktualisiert.

## Abschluss und Idempotenz

Der zweite Empfang setzt gemeinsam:

- Lifecycle und Legacy-Trade auf `completed`,
- `completed_at`,
- die bestehenden Legacy-Bestätigungsmarker,
- ein `completed`-Event,
- genau zwei bestehende Abschlussbenachrichtigungen.

Anschließend werden die bestehenden Trophy-Hooks kontrolliert ausgelöst. Die
alte pauschale `complete_trade()`-Bestandsbuchung wird nicht erneut ausgeführt,
weil Ausgang und Eingang bereits seitenbezogen gebucht sind.

Wiederholter Empfang liefert `ALREADY_RECEIVED` und bewahrt:

- Inventory-Menge,
- Fortschritt,
- ursprünglichen Empfangszeitpunkt,
- genau ein Receipt-Event,
- genau eine Trophy-Freischaltung,
- genau eine Abschlussbenachrichtigung je Seite.

## Testübersicht

Pflichtbefehl:

```bash
python3 -m unittest discover -s tests -p "test_s*.py" -v
```

Ergebnis beider vollständiger Läufe:

```text
Ran 216 tests
OK
```

Zusätzlich wurde vor dem Gate gezielt ausgeführt:

```bash
python3 -m unittest tests.test_s15_trade_shipping tests.test_s16_trade_receipt -v
```

Ergebnis:

```text
Ran 40 tests
OK
```

S16 deckt mindestens ab:

1. Empfang durch Anfrageersteller,
2. Empfang durch Anfrageempfänger,
3. beide Empfänge,
4. Abschluss ausschließlich nach dem zweiten Empfang,
5. seitenbezogene Transitauflösung,
6. korrekten Physical-Zugang,
7. Fortschrittsanstieg,
8. korrekte Availability und S08-Balance,
9. Trophy genau einmal,
10. Abschlussbenachrichtigung genau einmal je Seite,
11. idempotenten Retry,
12. fremden Nutzer,
13. falschen Lifecycle und fehlenden Versand,
14. leere Migration, Wiederholung, Backout und V0003→V0004,
15. lesbaren Legacy-`completed`-Trade,
16. Receipt vor eigenem Versand und später bewahrten Zwischenzustand,
17. zustandsgebundene Dealansicht.

## Schutz der kanonischen Datenbanken

Alle S16-Migrationen und Fachtests liefen ausschließlich auf temporären
Datenbanken oder temporären Kopien. Die lokale Standarddatenbank wurde nicht
auf V0004 migriert. Die kanonische S00-Fixture blieb unverändert:

```text
sammlr_reference_s00.db: 21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

`git diff --check` war ohne Befund.

## Offene Punkte für S17 und später

Nicht begonnen oder vorbereitet wurden:

- Teilempfang,
- falsche, beschädigte, fehlende oder verlorene Sticker,
- Problemworkflow, Rückabwicklung oder Schuldentscheidung,
- Chat, Bilder oder Bewertung,
- Tracking, Dienstleister oder Versandautomatisierung,
- Fristen, Eskalationen oder automatischer Support,
- Home- und Notification-Historienfunktionen,
- Designänderungen.

## Scope-Bestätigung

- Ausschließlich Sprint S16 wurde umgesetzt.
- Sprint S17 wurde nicht begonnen.
- Es wurden keine Teilempfangs- oder Problemfunktionen umgesetzt.
- Es wurden kein Chat, keine Bewertung und keine Fristen ergänzt.
- Es wurde kein automatischer Support ergänzt.
- Es wurden keine CSS- oder Designänderungen vorgenommen.
- Es wurde kein Commit und kein Push durchgeführt.
