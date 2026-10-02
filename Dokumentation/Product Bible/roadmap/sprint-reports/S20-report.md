# Sprint-Report S20 – Markt- und persönliche Trade-Abdeckung

Stand: 2026-08-06 · finalisiert nach manuellem Debug-Smoke und Rückbau

## Ziel und Ergebnis

S20 ist umgesetzt. Der neue read-only `TradeCoverageService` liefert Community Market Coverage und persönliche Trade-Abdeckung als zwei getrennte, unveränderliche und erklärbare DTOs. Sämtliche Mengen und Zustände stammen ausschließlich aus `InventoryReadService.snapshot(...)` aus S19.

Es wurden keine Empfehlungen, Rankings, Top Matches, automatischen Angebote oder UI-Elemente ergänzt.

## Neue Dateien

- `App/services/trade_coverage.py`
- `tests/test_s20_market_coverage.py`
- `Dokumentation/Product Bible/roadmap/s20-market-coverage.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S20-report.md`

## Geänderte Dateien

- `Dokumentation/Product Bible/roadmap/README.md`
  - S20-Vertrag und S20-Report verlinkt,
  - S21 als nächsten regulären offenen Sprint ausgewiesen.

Anwendungscode außerhalb des neuen read-only Coverage-Service wurde für S20 nicht geändert. Insbesondere blieben `App/webapp.py`, Inventory-Schreibpfade, Trade-, Reservations-, Shipping-, Receipt- und Problem-Services sowie sämtliche Migrationen unangetastet.

## Verwendete Snapshotdaten

S20 liest aus S19 ausschließlich:

- `missing`
- `physical`
- `effective_available`
- indirekt die bereits dort berücksichtigten Werte `reserved`, `incoming_transit` und `outgoing_transit`

Der Coverage-Service enthält kein SQL und keine eigene Availability-Berechnung. Er ruft ausschließlich `InventoryReadService.snapshot(...)` auf und bildet Mengen von Stickercodes.

## Berechnungsformeln

### Community Market Coverage

```text
M = physisch fehlende unterschiedliche Katalogcodes des Nutzers
A = Codes aus M, die bei mindestens einem anderen betrachteten Nutzer
    effective_available > 0 besitzen
U = M − A

Marktabdeckung = int(|A| / |M| * 100), falls |M| > 0
```

Mehrere Nutzer mit demselben Code werden als Vereinigungsmenge einmal gezählt.

### Persönliche Trade-Abdeckung

```text
M = physisch fehlende unterschiedliche Katalogcodes des Nutzers
P = Codes aus M mit physical > 0 beim Gegenüber
E = Codes aus M mit effective_available > 0 beim Gegenüber

persönliche Abdeckung = int(|E| / |M| * 100), falls |M| > 0
```

`P` und `E` werden getrennt ausgegeben. Ein physisch vorhandener, aber nicht verfügbarer Sticker erhöht ausschließlich `P`.

Bei `|M| = 0` ist der Prozentwert mathematisch nicht definiert und deshalb `None`; `has_missing=False` verhindert eine erfundene Produktaussage.

## Marktabdeckung und persönliche Abdeckung

`CommunityMarketCoverageDTO` enthält Zähler und Codelisten für fehlend, community-verfügbar und nicht verfügbar sowie Community-Größe, Scope und Confidence.

`PersonalTradeCoverageDTO` enthält Zähler und Codelisten für fehlend, beim Gegenüber physisch vorhanden und beim Gegenüber effektiv verfügbar sowie Scope und Confidence.

Beide Kennzahlen zählen unterschiedliche Codes, keine Kopien. Sie sind Momentaufnahmen für die explizit übergebenen Nutzer und kein Versprechen, dass ein Trade zustande kommt.

## Architektur des TradeCoverageService

`TradeCoverageService` erhält einen bereits geöffneten
`InventoryReadService` per Konstruktor. Seine beiden öffentlichen Lesepfade
`community_market_coverage(...)` und `personal_trade_coverage(...)` fordern
für jeden explizit übergebenen Nutzer genau den S19-Snapshot des betrachteten
Albums an. Der Service enthält weder SQL noch Schreibzugriffe, Statuswechsel,
Reservierungen oder Partnerermittlung.

Die Ergebnisse sind eingefrorene DTOs. Zähler, Codelisten, `scope` und
`confidence` bleiben gemeinsam verfügbar, damit keine Prozentzahl ohne ihre
fachliche Bezugsmenge verwendet werden muss.

## Finaler manueller Debug-Smoke

Der abschließende isolierte Smoke-Test verwendete vier synthetische Nutzer in
einer temporären, aus der S00-Fixture erzeugten V0005-Datenbank. Die technische
Debug-Ansicht zeigte die Snapshotwerte und Coverage-Ergebnisse nebeneinander.
Alle erwarteten Werte waren für einen Menschen anhand der Bestände,
Reservierung, Transitrichtung und Codelisten nachvollziehbar.

Exakte Konstellation:

| Sicht | physisch vorhanden | effektiv verfügbar | Abdeckung |
|---|---:|---:|---:|
| Valentin Debug: Community | 10 fehlend | 6 community-verfügbar | 60 % |
| Valentin → Anna Debug | 5 | 4 | 40 % |
| Valentin → Mehmet Debug | 3 | 3 | 30 % |
| Valentin → Sofia Debug | 1 | 0 | 0 % |

Für Valentin Debug waren exakt die Codes **241–250** fehlend.

- Community-verfügbar: **241, 242, 243, 244, 246, 247**
- nicht verfügbar: **245, 248, 249, 250**
- Anna physisch vorhanden: **241, 242, 243, 244, 245**
- Anna effektiv verfügbar: **241, 242, 243, 244**
- Mehmet physisch und effektiv verfügbar: **244, 246, 247**
- Sofia physisch vorhanden, aber nicht effektiv verfügbar: **248**
- Sofia incoming_transit, weiterhin physisch fehlend: **249**

Code 244 lag bei Anna und Mehmet effektiv verfügbar vor, wurde in der
Community-Vereinigungsmenge aber korrekt nur einmal gezählt.

### Reservierter Code 245

Anna besaß Code 245 zweimal. Eine Kopie war dem Album zugeordnet, die zweite
Kopie aktiv reserviert. Damit galt `physical=2`, `assigned=1`, `reserved=1`
und `effective_available=0`. Der Code erhöhte deshalb die physische
persönliche Abdeckung, aber weder Annas effektive Abdeckung noch die
Community-Marktabdeckung.

### Incoming und outgoing transit

Code 249 war von Anna an Sofia versendet. Der gemeinsame S19-Snapshot zeigte
bei Sofia `incoming_transit=1`, aber weiterhin `physical=0`, `missing=true`
und `effective_available=0`. Korrespondierend war die Position auf der
Absenderseite als `outgoing_transit` erklärbar. Transit wurde nicht als
Community-Angebot gezählt und erzeugte keine eigene S20-Geschäftsregel.

Die vollständigen Messwerte stehen im
[Debug-Smoke-Bericht](S20-debug-smoke-report.md) und im ergänzenden
[Debug-Start-Smoke-Bericht](S20-debug-start-smoke-report.md). Die temporäre
Route, der Builder, die Debug-Tests und die externe Debug-Datenbank wurden nach
der erfolgreichen Prüfung vollständig entfernt.

## Keine Produktentscheidungen außerhalb S20

- keine Partnerauswahl oder Partnerbewertung
- keine Sortierung nach Abdeckung
- keine Prüfung des eigenen Gegenangebots
- keine konfliktfreie Kombination mehrerer Trades
- keine Empfehlung oder automatische Anfrage
- keine UI, kein neues Wording und keine Prozentdarstellung im Produkt
- kein Caching oder Performanceprojekt

Die ganzzahlige Prozentrechnung folgt der bestehenden Sammlr-Konvention; exakte Zähler und Codelisten bleiben vollständig erhalten. Scope und Confidence machen die Aussagegrenze explizit.

## Testergebnisse

Gezielt:

```bash
python3 -m unittest tests.test_s20_market_coverage -v
```

Ergebnis: **15 Tests, OK**.

Vollständiges Gate, nach dem finalen DTO-Vertrag zweimal ausgeführt:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Lauf 1: **322 Tests, OK**
- Lauf 2: **322 Tests, OK**

Diese beiden Läufe wurden nach dem vollständigen Rückbau der temporären
Debug-Infrastruktur am 06.08.2026 erneut ausgeführt. Die gezielten 15
regulären S20-Tests waren ebenfalls vollständig grün.

Abgedeckt sind 0 %, 100 %, Teilabdeckung, persönliche und gegenseitig unterschiedliche Abdeckung, Reservierung, eingehender und ausgehender Transit, unveränderter Snapshot, unverändertes Inventory, mehrere Nutzer, mehrere Alben, Problemfall und Problemauflösung.

Alle neuen Tests verwenden ausschließlich temporäre Kopien der kanonischen S00-Fixture und migrieren nur diese Kopien kontrolliert bis V0005.

## Release Readiness

- lokaler Migrationsstand read-only geprüft: **V0005**
- neue Migration erforderlich: **nein**
- Migration ausgeführt: **keine**
- `PRAGMA integrity_check`: **ok**
- `PRAGMA foreign_key_check`: **keine Befunde**
- lokale Entwicklungsdatenbank im Closeout-Testfenster unverändert; finale
  Prüfsumme siehe `S20-closeout-report.md`
- kanonische S00-Fixture unverändert: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`
- Syntaxprüfung erfolgreich
- beide vollständigen Gates reproduzierbar grün
- `git diff --check`: **ohne Befund**
- Anwendung ohne `SAMMLR_DEBUG_COVERAGE` auf isolierter Datenbankkopie
  gestartet
- entfernte Route `/debug/trade-coverage`: **HTTP 404**
- normale Tauschzentrale auf derselben isolierten Kopie: **HTTP 200**

## Offene Punkte für S21

- konfliktfreie Nutzung begrenzter eigener Sticker über mehrere Partner
- Top-Match-Auswahl und gemeinsame Ressourcenbelegung
- deterministische Optimierung und Tie-Breaks
- Ranking beziehungsweise priorisierte Darstellung erst im ausdrücklich freigegebenen S21-Scope
- verbindliche Priorisierung der Zielfunktion Fortschritt gegenüber
  Tradeanzahl
- vollständige deterministische Tie-Break-Reihenfolge
- konkretes Performancebudget und verbindliche realistische Fixture

Keiner dieser Punkte wurde begonnen.

## Scope-Bestätigung

- ausschließlich S20 „Markt- und persönliche Trade-Abdeckung“ umgesetzt
- S19 Snapshot unverändert wiederverwendet
- S21 nicht begonnen
- keine Tradeempfehlungen, kein Ranking und keine Partner-Sortierung
- keine Mutation, Reservierung oder Tradeerzeugung
- keine UI-Änderung
- keine Migration und keine Schemaänderung
- kein Commit
- kein Push
