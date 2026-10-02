# S20 – Temporärer Trade-Coverage-Debug-Smoke

Stand: 06.08.2026

> Historischer Prüfbericht: Die hier beschriebene temporäre Route, der Builder,
> die Debug-Tests und die externe Debug-Datenbank wurden nach erfolgreichem
> S20-Closeout am 06.08.2026 vollständig entfernt. Die Startanleitung ist nicht
> mehr ausführbar und dokumentiert ausschließlich den damaligen Smoke-Test.

## Ergebnis

Die isolierte technische Debug-Prüfung bestätigt die S20-Berechnungen. Der
Flask-Endpunkt liefert die erwarteten Community- und persönlichen Kennzahlen
und liest dafür ausschließlich den bestehenden `TradeCoverageService` und den
S19-`InventoryReadService.snapshot(...)`. Es wurde keine zweite
Availability-Berechnung ergänzt.

Die Prüfung ist weder eine normale Produktansicht noch ein neues Feature. Sie
ist ohne explizite Aktivierung nicht erreichbar und besitzt keine Formulare,
Buttons oder schreibenden Aktionen.

## Isolierte Debug-Datenbank

- Quelle: `App/Database/sammlr_reference_s00.db`
- Temporäres Ziel: `/private/tmp/sammlr-s20-debug-coverage-20260806.db`
- Zielversion: V0005
- Integritätscheck: `ok`
- Debug-Marker: `s20-trade-coverage-v1`
- Album: `vfl` (bestehender Katalog mit 250 Codes)
- Nutzer: Valentin Debug (ID 4), Anna Debug (ID 5), Mehmet Debug (ID 6),
  Sofia Debug (ID 7)

Erstellung:

```bash
python3 App/Database/create_s20_debug_coverage_db.py \
  --database /private/tmp/sammlr-s20-debug-coverage-20260806.db
```

Der Builder akzeptiert ausschließlich die kanonische S00-Fixture als Quelle,
verweigert die lokale Standarddatenbank und die S00-Fixture als Ziel und
überschreibt keine existierende Datei. Die Migration und sämtliche Seed-Daten
liegen nur in der neu angelegten temporären Kopie.

## Exakte synthetische Bestände

Valentin Debug:

- physical 1 für Codes 1–240
- physical 2 für Codes 4 und 5
- exakt fehlend: 241–250

Anna Debug:

- physical 2 für 241, 242, 243 und 244; jeweils effective_available 1
- physical 2 für 245; davon assigned 1 und reserved 1,
  effective_available 0

Mehmet Debug:

- physical 2 und effective_available 1 für 244, 246 und 247
- 244 überschneidet sich absichtlich mit Annas Angebot

Sofia Debug:

- physical 1 für 248; assigned 1 und effective_available 0
- physical 0 und incoming_transit 1 für 249; effective_available 0 und
  weiterhin missing

Code 250 ist bei keinem Debug-Nutzer verfügbar. Die Reservierung für 245 und
der Versandtransit für 249 werden durch gültige isolierte Lifecycle-Datensätze
abgebildet.

## Erwartet gegen tatsächlich gemessen

| Kennzahl | Erwartet | Tatsächlich |
|---|---:|---:|
| Valentin fehlend | 10 | 10 |
| Community-verfügbar | 6 | 6 |
| Community-nicht verfügbar | 4 | 4 |
| Marktabdeckung | 60 % | 60 % |
| Valentin → Anna: physisch vorhanden | 5 | 5 |
| Valentin → Anna: effektiv verfügbar | 4 | 4 |
| Valentin → Anna: Abdeckung | 40 % | 40 % |
| Valentin → Mehmet: physisch vorhanden | 3 | 3 |
| Valentin → Mehmet: effektiv verfügbar | 3 | 3 |
| Valentin → Mehmet: Abdeckung | 30 % | 30 % |
| Valentin → Sofia: physisch vorhanden | 1 | 1 |
| Valentin → Sofia: effektiv verfügbar | 0 | 0 |
| Valentin → Sofia: Abdeckung | 0 % | 0 % |

Community-verfügbar sind exakt 241, 242, 243, 244, 246 und 247. Die
Überschneidung bei 244 wird in der Vereinigungsmenge genau einmal gezählt.
Nicht verfügbar sind 245, 248, 249 und 250.

## Debug-Endpunkt und Schutzregeln

URL nach lokalem Start:

`http://127.0.0.1:8080/debug/trade-coverage`

Startbefehl aus dem Projektstamm:

```bash
SAMMLR_DEBUG_COVERAGE=1 \
DATABASE_PATH=/private/tmp/sammlr-s20-debug-coverage-20260806.db \
python3 App/webapp.py
```

Der Endpunkt antwortet nur, wenn alle Bedingungen erfüllt sind:

1. `SAMMLR_DEBUG_COVERAGE` ist exakt `1`.
2. Der aktive `DATABASE_PATH` ist weder die lokale Standarddatenbank noch die
   S00-Fixture.
3. Die Datenbank enthält den erwarteten Debug-Marker und alle vier Debug-Nutzer.

Andernfalls antwortet die Route mit HTTP 404. Die Seite zeigt nur technische
Tabellen: Community-Zahlen und Codes, persönliche Zahlen und Codes inklusive
Scope/Confidence sowie die kompakten Snapshot-Felder physical, reserved,
incoming_transit, outgoing_transit, effective_available und missing.

Der Flask-Routenweg wurde mit dem echten Testclient als HTTP GET geprüft
(Status 200). Ein zusätzlicher lokaler Socket-Aufruf war in der isolierten
Ausführungsumgebung nicht erreichbar; für die manuelle Browserprüfung gilt der
oben angegebene Startbefehl.

## Tests

Gezielter Lauf:

```bash
python3 -m unittest tests.test_s20_market_coverage tests.test_s20_debug_coverage -v
```

Ergebnis: 28 Tests, alle erfolgreich.

Die 13 neuen Debug-Smoke-Tests prüfen:

- Aufbau aus S00, Migration V0005 und Debug-Marker
- Sperre ohne Flag, für die normale Produktdatenbank und ohne Marker
- exakte Community-Kennzahlen und Code-Mengen
- Überschneidung ohne Doppelzählung
- exakte persönliche Abdeckung für Anna, Mehmet und Sofia
- reservierter physischer Bestand ohne effektive Verfügbarkeit
- incoming_transit ohne physical und ohne effektive Verfügbarkeit
- GET ohne Datenbankmutation sowie ohne Formulare oder Buttons
- unveränderte lokale Standarddatenbank und S00-Fixture

Vollständiges Gate, zweimal ausgeführt:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Lauf 1: 335 Tests, alle erfolgreich
- Lauf 2: 335 Tests, alle erfolgreich

`git diff --check` wurde erfolgreich ohne Beanstandung ausgeführt.

## Prüfsummen und Unverändertheit

| Datei | SHA-256 vor dem verifizierten Testlauf | SHA-256 danach |
|---|---|---|
| `App/Database/sammlr.db` | `d924b0413f7e3ba0f94829610ef0e513050c6cd08b7e766b1179d3c985d310ba` | `d924b0413f7e3ba0f94829610ef0e513050c6cd08b7e766b1179d3c985d310ba` |
| `App/Database/sammlr_reference_s00.db` | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` |

Temporäre Debug-Datenbank nach Erstellung:
`66f96fcb338aa8d1dd8d312f69b1d9384bc456f8f6d6e730e4c79ab8b85402ea`.

Die vorhandenen Backup-Dateien wurden ausschließlich für die abschließende
Statuskontrolle aufgelistet und nicht verändert.

## Betroffene Dateien

Neu:

- `App/Database/create_s20_debug_coverage_db.py`
- `tests/test_s20_debug_coverage.py`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S20-debug-smoke-report.md`

Geändert:

- `App/webapp.py`: ausschließlich der opt-in Debug-Endpunkt und dessen harte
  Datenbank-/Fixture-Sperre

## Scope-Bestätigung

- Keine Änderung an S19- oder S20-Berechnungslogik.
- Keine Änderung an Trade-, Versand-, Empfangs-, Problem- oder Inventory-
  Schreiblogik.
- Keine Änderung an normaler UI oder normalem Produktverhalten.
- Keine Migration oder Seed-Änderung der lokalen Standarddatenbank.
- Keine Änderung an der kanonischen S00-Fixture.
- Keine Änderung an Backups oder anderen Datenbankkopien.
- Keine produktiven oder lokalen Debug-Nutzerdaten angelegt.
- Kein Commit und kein Push.
