# Sprintbericht S18 – Trade Lifecycle Timeline und Fälligkeiten

Stand: 2026-08-04

## Ergebnis

Sprint S18 wurde als ausschließlich read-only UI-Schicht umgesetzt. Jede
Dealansicht zeigt eine relationale Lifecycle-Timeline mit vorhandenen
Zeitstempeln, offenen Schritten, Problemen und Abschluss. Statuschips sind in
Dealansicht und beiden Tradeboards vereinheitlicht. Gelbe Hinweise markieren
überfälligen eigenen Versand sowie einen seit 14 Tagen ausstehenden Empfang,
ohne Zustand, Daten oder Notifications zu verändern.

## Beschreibung

Die Timeline visualisiert:

- Anfrage gesendet,
- Anfrage angenommen,
- Sticker reserviert,
- eigenen Versand und Versand der Gegenseite,
- Problem gemeldet/offen/gelöst,
- eigenen Empfang und Bestätigung der Gegenseite,
- Trade abgeschlossen.

Alle Rollen werden aus Sicht des angemeldeten Nutzers bezeichnet. Vorhandene
UTC-Zeitstempel werden nach `Europe/Berlin` übersetzt und als Datum plus Uhrzeit
angezeigt. Legacy-Trades bleiben ohne erfundene Zeitpunkte lesbar.

Die Versandfälligkeit verwendet die verbindlichen fünf Werktage ab dem
frühesten vorhandenen Reservierungs-/Annahmezeitpunkt. Der Empfangshinweis
erscheint ab 14 Kalendertagen nach dem Versand der Gegenseite. Beide Werte
existieren nur während des Renderns; es wird nichts persistiert.

## Betroffene Dateien

Geändert:

- `App/webapp.py`
  - read-only Zeitformatierung und Berlin-Zeitzone
  - Timeline-/Chip-/Hinweisprojektion
  - Timeline in der Dealansicht
  - einheitliche Chips und Hinweise in globalem und albumbezogenem Tradeboard
  - Profil-Tradearchiv nutzt bei Lifecycle-Trades `completed_at`
- `App/static/style.css`
  - Styles ausschließlich für S18-Timeline, Chips und gelbe Hinweise
- `Dokumentation/Product Bible/roadmap/README.md`
  - S18-Beschreibung und Bericht verlinkt

Neu:

- `tests/test_s18_trade_lifecycle_timeline.py`
  - reine Darstellungs-, Zeit-, Legacy- und Read-only-Tests
- `Dokumentation/Product Bible/roadmap/s18-trade-lifecycle-timeline.md`
  - Eventkatalog, Fristentscheidung und Darstellungskontrakt
- `Dokumentation/Product Bible/roadmap/sprint-reports/S18-report.md`
  - dieser Bericht

Nicht geändert wurden Inventory-Code, Migrationen,
`TradeReservationService`, `TradeShippingService`, `TradeProblemService` und
`TradeReceiptService`.

## Screens / geprüfte Zustände

| Screen | Sichtbares Ergebnis |
| --- | --- |
| Offene Anfrage | Chip `Offen`; gesendete Anfrage mit Zeit, Annahme/Reservierung offen |
| Angenommener Deal | Chip `Reserviert`; Annahme und Reservierung mit Zeit, Versand offen |
| Versand läuft | Chip `Versand läuft`; eigene und fremde Versandseite getrennt |
| Teilweise empfangen | Chip `Teilweise erhalten`; eigener Empfang erledigt, Gegenseite offen |
| Problem offen | gelber Chip; Problem gemeldet und offen in Timeline |
| Problem gelöst | Meldung und Auflösung bleiben mit beiden Zeiten sichtbar |
| Überfällig | gelber Hinweis für Versand oder ausstehenden Empfang, kein Statuswechsel |
| Abgeschlossen | grüner Chip; Abschlusszeit in Timeline und Profilarchiv |
| Legacy completed | abgeschlossen lesbar; unbekannte historische Zeiten ausdrücklich markiert |

Es wurden keine künstlichen Screenshots oder Mockups committed. Sämtliche
Screenzustände werden durch echte gerenderte HTML-Antworten auf temporären
V0005-Datenbanken geprüft.

## Tests

S18-spezifisch:

```bash
python3 -m unittest tests.test_s18_trade_lifecycle_timeline -v
```

Ergebnis:

```text
Ran 13 tests in 0.101s
OK
```

Vollständiges Gate:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Ergebnis beider vollständiger Läufe:

```text
Lauf 1: Ran 256 tests in 0.998s – OK
Lauf 2: Ran 256 tests in 0.998s – OK
```

## Smoke-Test-Anleitung

1. Anwendung gegen eine **temporäre V0005-Testdatenbank** starten.
2. Als Teilnehmer eine offene Anfrage öffnen:
   - Chip `Offen`,
   - Anfragezeit sichtbar,
   - Annahme und Reservierung als offene Kreise.
3. Anfrage annehmen und Deal öffnen:
   - Chip `Reserviert`,
   - Annahme-/Reservierungszeit sichtbar.
4. Nur eine Seite als versendet markieren:
   - Chip `Versand läuft`,
   - richtige Seite mit Haken und lokalisierter Uhrzeit,
   - andere Seite offen.
5. Beide Seiten versenden, nur eine Seite empfangen:
   - Chip `Teilweise erhalten`,
   - Empfangsseiten korrekt aus Sicht beider Nutzer vertauscht.
6. Einen S17-Problemfall auf temporären Daten anlegen:
   - Chip `Problem offen`,
   - `Problem … gemeldet` plus Zeit,
   - `Problem offen` in Timeline.
7. Problem auflösen:
   - `Problem gelöst` plus Zeit,
   - frühere Meldung bleibt sichtbar.
8. Für eine reine UI-Probe Zeitstempel nur in der temporären Testdatenbank
   zurückdatieren:
   - eigener Versand nach fünf Werktagen: gelber Versandhinweis,
   - fremder Versand vor mindestens 14 Tagen: „Empfang steht noch aus“.
9. Beide Empfänge bestätigen:
   - Chip `Abgeschlossen`,
   - Abschlusszeit aus `trades.completed_at`,
   - Profilarchiv zeigt Abschluss- statt Anfragezeit.
10. Als jeweils andere beteiligte Person prüfen, dass „eigener“ und
    „Gegenseite“ korrekt wechseln.

Keiner der zustandsverändernden Schritte dieser Anleitung darf gegen die
lokale Produktdatenbank laufen.

## Ausgeführter read-only Smoke-Test

Ergänzend wurde ausschließlich per HTTP-GET eine bereits vorhandene lokale
Dealansicht gelesen; es wurde kein Tradezustand ausgelöst und keine Datenzeile
verändert:

```text
GET http://127.0.0.1:8080/trades/30 → HTTP 200
```

Nachgewiesen wurden im gerenderten HTML:

- `Trade Timeline`,
- Chip `Problem offen`,
- Anfrage, Annahme und Reservierung,
- beide Versandseiten,
- beide Empfangsseiten,
- Problemzustand und offener Abschluss,
- Sammlr-Datum `04.08.2026` mit lokalisierter Uhrzeit.

Der bereits vorhandene lokale Migrationsstand blieb V0005; es wurde kein
Migration Runner aufgerufen. `PRAGMA integrity_check` lieferte `ok`. Die
SHA-256-Prüfsumme der lokalen Datenbank war unmittelbar vor und nach dem
read-only Smoke identisch:

```text
87a508f3381bc8c73e86ae323c86786363261524b1fbd751d2361ef7b98e4931
```

Die kanonische S00-Fixture blieb ebenfalls unverändert:

```text
21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

## Scope- und Schutzbestätigung

- Ausschließlich S18-Darstellung wurde umgesetzt.
- Es wurde kein Refactoring durchgeführt.
- Bestandslogik und alle Trade-Services blieben unverändert.
- Es wurden keine neuen Tabellen oder Migrationen erstellt.
- Die lokale Produktdatenbank wurde nicht migriert.
- Es wurden keine Erinnerungen, Push-Nachrichten oder Eskalationen ergänzt.
- Es wurde kein Commit und kein Push durchgeführt.
