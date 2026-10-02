# S17 Inventory-Bug-Untersuchung

Stand: 2026-08-03

## Ergebnis

**Verdacht nicht bestätigt.** In keinem reproduzierten Fall wurde eine als
fehlend, falsch, beschädigt oder verloren gemeldete offene Menge beim
Problem-POST eingebucht. Direkter `TradeProblemService` und echte
Flask-POST-Route erzeugten dieselben Datenbankwerte:

- Bei `correct_received = 0` blieben `stickers.quantity`, Physical, Assigned
  und Available unverändert.
- Bei `correct_received = 2` von `expected = 3` stiegen Quantity und Physical
  exakt um 2; genau 1 blieb ungebucht und `incoming_transit`.
- Ein identischer Retry veränderte weder Inventory, Transit noch Bericht.
- Erst die ausdrücklich ausgelöste spätere Problemauflösung buchte die noch
  offene erwartete Restmenge.

Der Eindruck einer falschen Buchung ist anhand der vorhandenen lokalen Daten
erklärbar: Zwei lokale Problemberichte wurden zunächst korrekt mit einer
offenen Menge gespeichert und 26 beziehungsweise 48 Sekunden später über die
Problemauflösung vollständig gebucht. Außerdem zeigt „Du bekommst“ weiterhin
die vertraglich erwarteten Positionen, nicht den real gebuchten Bestand. Die
Historie zeigt nach einer Auflösung die gesamte inzwischen korrekt gebuchte
Menge, ohne Anfangs- und spätere Auflösungsbuchung getrennt auszuweisen.

## Untersuchungsaufbau

Alle Reproduktionen liefen auf jeweils neu erstellten temporären Kopien der
kanonischen S00-Fixture. Jede Kopie wurde ausschließlich mit dem vorhandenen
Migration Runner bis V0005 migriert. Die lokale Datenbank wurde nur read-only
abgefragt und nicht migriert oder verändert.

Für jeden Fall wurden separat ausgeführt:

1. Trade anlegen, akzeptieren und Versand der Gegenseite bestätigen.
2. Vorwerte messen.
3. Problem einmal direkt über `TradeProblemService.report()` melden.
4. Denselben Fall auf einer neuen Kopie über den echten Flask-Endpunkt
   `POST /trade/<id>/problem` melden.
5. Direkt danach alle Werte messen.
6. Identische Meldung erneut absenden und erneut messen.
7. Problem über Service beziehungsweise
   `POST /trade/<id>/problem/resolve` auflösen und erneut messen.

Die echte Route wurde mit Flask-Testclient, realer Session, echter
Formularauswertung, echten DTOs und der temporären SQLite-Datenbank ausgeführt.
Es wurden keine Servicefunktionen gemockt.

## Messgrößen und Notation

Die Tabellen verwenden:

- `q`: `stickers.quantity`
- `d`: `stickers.duplicates`
- `p`: InventoryReadService Physical
- `a`: Assigned
- `v`: Available
- `t`: `incoming_transit`
- `e/i/o`: gespeicherte erwartete / anfänglich korrekt erhaltene / offene
  Menge

Vor jeder Problemmeldung war der Legacy-Status `accepted` und der Lifecycle
`partially_shipped`. Nach jeder unvollständigen Meldung war der Legacy-Status
weiterhin `accepted` und der Lifecycle `problem_open`.

## Vorher-/Nachherwerte A–E

Service und Route lieferten in allen folgenden Fällen exakt dieselben Werte:

| Fall | Vor Meldung q/d/p/a/v/t | Nach Meldung q/d/p/a/v/t | Report e/i/o, Typ | Nach identischem Retry | Nach Auflösung q/d/p/a/v/t |
| --- | --- | --- | --- | --- | --- |
| A: 0/1, fehlend | 0/0/0/0/0/1 | 0/0/0/0/0/1 | 1/0/1, `missing` | unverändert | 1/0/1/1/0/0 |
| B: 0/1, falsch | 0/0/0/0/0/1 | 0/0/0/0/0/1 | 1/0/1, `wrong_sticker` | unverändert | 1/0/1/1/0/0 |
| C: 0/1, beschädigt | 0/0/0/0/0/1 | 0/0/0/0/0/1 | 1/0/1, `damaged` | unverändert | 1/0/1/1/0/0 |
| D: Sendung verloren | 0/0/0/0/0/1 | 0/0/0/0/0/1 | 1/0/1, `shipment_lost` | unverändert | 1/0/1/1/0/0 |
| E: 2/3, fehlend | 0/0/0/0/0/3 | 2/0/2/1/1/1 | 3/2/1, `missing` | unverändert | 3/2/3/1/2/0 |

Die Auflösungswerte sind kein Fehler: Die Auflösung wurde im Test bewusst als
„offene erwartete Restmenge ist später korrekt eingetroffen“ ausgelöst. Sie
buchte jeweils exakt den zuvor offenen Rest und setzte den Lifecycle auf
`partially_received`; der Legacy-Trade blieb `accepted`, weil die andere Seite
noch nicht empfangen hatte.

Bei Fall E bleibt das Legacy-Feld `duplicates` beim erstmaligen Erzeugen einer
Stickerzeile mit Menge 2 zunächst 0. Der zentrale Inventory Read Service
berechnet Available trotzdem korrekt als 1. Beim späteren Update auf Menge 3
wird `duplicates` auf 2 synchronisiert. Das ist das bereits vorhandene,
absichtlich vom Inventory-Adapter bewahrte Insert-Verhalten und kein Beleg für
eine Buchung der fehlenden Menge. Es wurde im Rahmen dieser Untersuchung nicht
verändert.

## Fall D mit mehreren Positionen

Die vollständig verlorene Sendung wurde zusätzlich mit zwei erwarteten
Positionen geprüft. Die Route erhielt absichtlich andere Mengen-/Problemfelder
zusammen mit dem gesetzten `shipment_lost`-Feld; die Formularauswertung setzte
für **alle** erwarteten Positionen verbindlich Menge 0 und Typ
`shipment_lost`.

| Position | Vor q/d/p/a/v/t | Nach Service | Nach Route | Report e/i/o |
| --- | --- | --- | --- | --- |
| Code 1 | 0/0/0/0/0/1 | 0/0/0/0/0/1 | 0/0/0/0/0/1 | 1/0/1 |
| Code 2 | 1/0/1/1/0/1 | 1/0/1/1/0/1 | 1/0/1/1/0/1 | 1/0/1 |

Beide Berichte blieben `problem_open`; ein identischer Retry lieferte
`ALREADY_IDENTICAL` und änderte keine Menge.

## Fall F: gemischte Sendung

Die Sendung enthielt zwei erwartete Positionen. Code 1 wurde vollständig,
Code 2 mit korrekt erhaltener Menge 0 als fehlend gemeldet.

| Position | Vor q/d/p/a/v/t | Nach Meldung q/d/p/a/v/t | Report e/i/o, Typ | Nach Retry | Nach Auflösung |
| --- | --- | --- | --- | --- | --- |
| Code 1, vollständig | 0/0/0/0/0/1 | 1/0/1/1/0/0 | 1/1/0, kein Problem | unverändert | unverändert |
| Code 2, fehlend | 1/0/1/1/0/1 | 1/0/1/1/0/1 | 1/0/1, `missing` | unverändert | 2/1/2/1/1/0 |

Damit wurde ausschließlich die vollständig erhaltene Position sofort gebucht.
Die fehlende Position blieb bis zur expliziten Auflösung vollständig
unverändert.

## Service-vs.-Route-Vergleich

Direkter Service:

- erste Meldung: `PARTIAL_RECEIPT_RECORDED`
- identischer Retry: `ALREADY_IDENTICAL`
- spätere Auflösung: `PROBLEM_RESOLVED`

Echte Flask-Route:

- erste Meldung: Redirect mit „Problem und erhaltene Mengen gespeichert“
- identischer Retry: Redirect mit „Identische Meldung bereits verarbeitet“
- spätere Auflösung: Redirect mit „Problem aufgelöst“

Alle zwölf Hauptläufe – A bis F jeweils einmal Service und einmal Route –
hatten identische Vor-/Nachherwerte. Zusätzlich war auch die mehrpositionige
Verlustmeldung in beiden Pfaden identisch.

## Eingrenzung der möglichen Fehlerstellen

### Formularauswertung

Kein Fehler reproduziert. `report_trade_problem()` lädt ausschließlich die an
den aktuellen Nutzer gerichteten Lifecycle-Positionen. Zahlenfelder werden als
Integer in die DTOs übernommen. Bei `shipment_lost` werden Menge 0 und Typ
`SHIPMENT_LOST` für jede Position erzwungen.

### DTO-Erzeugung und Validierung

Kein Fehler reproduziert. Das DTO bewahrt die Formularmenge. `_normalize()`
verlangt jede erwartete Position genau einmal, begrenzt die Menge auf
`0..expected`, verlangt bei offener Menge einen erlaubten Problemtyp und weist
widersprüchliche oder fremde Positionen ab.

### InventoryWriteService-Aufruf

Kein Überbuchungsfehler reproduziert. `_book()` überspringt Mengen `<= 0` und
ruft `InventoryWriteService.add()` ausschließlich mit der normalisierten
`correct_received`-Menge auf. Fall E zeigte exakt einen Delta-Zugang von 2;
Fall F buchte nur die vollständig erhaltene Position.

### Transitprojektion

Kein Fehler reproduziert. Die Projektion zieht ausschließlich
`initial_received_quantity` und später `resolution_received_quantity` von der
erwarteten Positionsmenge ab. Bei 0/1 blieb Transit 1, bei 2/3 blieb Transit 1,
beim vollständig erhaltenen Teil von Fall F wurde nur dessen Transit 0.

### Anzeige

Hier liegt die nachvollziehbare Ursache des Verdachts:

1. „Du bekommst“ zeigt weiterhin das vereinbarte Tradepaket. Diese Liste ist
   Erwartung/Vertrag und keine Inventory-Bestätigung.
2. Bei einem offenen Testbericht zeigte die Dealansicht gleichzeitig korrekt
   `Problem offen`, `erwartet 1`, `korrekt erhalten 0` und `offen 1`.
3. Der Auflösungsbutton lautet „Offene Restmenge vollständig erhalten“. Seine
   Betätigung bedeutet fachlich, dass der Rest später korrekt angekommen ist,
   und bucht ihn deshalb absichtlich.
4. Nach Auflösung zeigt die Historie `position.booked_quantity`, also
   `initial_received_quantity + resolution_received_quantity`, als „korrekt
   erhalten“. Sie trennt die Erstmeldung und spätere Buchung in dieser Zeile
   nicht. Lediglich „Problem aufgelöst“ und der Auflösungszeitpunkt zeigen den
   zweiten Schritt.

Die UI kann daher nach einer versehentlichen oder missverstandenen Auflösung
so wirken, als sei der ursprünglich fehlende/falsche Sticker bereits bei der
Meldung gebucht worden. Die Datenbankhistorie widerlegt das.

## Vorhandene lokale Daten

Die lokale V0005-Datenbank wurde read-only untersucht. Sie enthält zwei
aufgelöste Berichte mit insgesamt sechs Positionen und keinen offenen Bericht.
Es gibt keine negativen oder überhöhten Reportmengen und keinen negativen
Transitrest.

Besonders relevant:

- Trade 28, Code `CRO18`: initial korrekt erhalten 0, Typ `wrong_sticker`;
  Bericht um `20:52:48` erstellt. Um `20:53:36` wurde exakt 1 als später
  eingetroffene Restmenge aufgelöst und erst dann gebucht.
- Trade 29, Code `13`: initial korrekt erhalten 0, Typ `missing`; Bericht um
  `21:00:26` erstellt. Um `21:00:52` wurde exakt 1 aufgelöst und erst dann
  gebucht.

Die Lifecycle-Events bestätigen jeweils die Reihenfolge
`problem_reported → problem_resolved → receipt_confirmed`. Beide Trades sind
weiterhin Legacy `accepted` und Lifecycle `partially_received`, weil die
andere Empfangsseite offen ist. Die aktuell sichtbare Menge 1 stammt somit aus
der dokumentierten Auflösung, nicht aus der ursprünglichen 0-Meldung.

**Risiko für vorhandene lokale Daten:** Es wurde kein technischer Hinweis auf
Bestandskorruption durch den untersuchten S17-Pfad gefunden. Falls die beiden
Auflösungsbuttons fachlich versehentlich betätigt wurden, bildet die Datenbank
die Benutzeraktion technisch korrekt ab; ob der Sticker physisch tatsächlich
später angekommen ist, kann der Code nicht entscheiden. Es wurde keine
Korrektur oder Rückbuchung vorgenommen.

## Kritische Bewertung der bestehenden S17-Tests

Ausgeführt:

```bash
python3 -m unittest tests.test_s17_trade_problems_partial_receipt -v
```

Ergebnis:

```text
Ran 27 tests in 0.181s
OK
```

Die vorhandenen Tests prüfen die verdächtige Mengenlogik direkt am Service und
an echten temporären Datenbankwerten umfassend: 29/30, Menge 0 bei falsch,
beschädigt und verloren, Transit, Retry und Auflösung.

Die Route ist jedoch nur teilweise abgesichert: Ein bestehender Side-Effect-
Test sendet tatsächlich eine 0/1-`missing`-Meldung per Flask-POST und löst sie
danach per Route auf; der UI-Test prüft das begrenzte GET-Formular. Vor der
Auflösung behauptet dieser Routentest aber nicht ausdrücklich alle Inventory-
und Reportwerte. Die Fälle A–F werden im committed Testbestand überwiegend
über den Service geprüft. Die jetzige Untersuchung hat diese Lücke
diagnostisch geschlossen, aber gemäß Auftrag keinen neuen Test geschrieben.

## Ursache und Schweregrad

- **Bestandsfehler:** nicht reproduzierbar; kein bestätigter Defekt.
- **Ursache des Eindrucks:** erwartete Vertragsposten unter „Du bekommst“ plus
  eine Historienzeile, die nach Auflösung initiale und spätere korrekte Mengen
  summiert; außerdem bucht der bewusst ausgelöste Auflösungsbutton den Rest.
- **Schweregrad Bestandsintegrität:** keiner nach aktuellem Befund.
- **Schweregrad UX/Fehlbedienungsrisiko:** niedrig bis mittel, weil die
  Auflösung eine reale Bestandsbuchung auslöst und der zeitliche Unterschied
  anschließend nur indirekt erkennbar ist.

Ein S17.1-Bestandsfix ist nach diesen Messungen nicht gerechtfertigt.

## Erforderliche Nacharbeit und Empfehlung für morgen

Empfohlen wird ein kleiner, separat freizugebender S17.1-Härtungsschritt:

1. Permanente Flask-POST-Regressionstests für A–F ergänzen und vor/nach
   Meldung, Retry und Auflösung dieselben DB-/DTO-Werte wie in diesem Bericht
   behaupten.
2. In der Dealansicht „Du bekommst“ als „Vereinbart / erwartet“ kennzeichnen.
3. Die Problemhistorie getrennt als „bei Meldung korrekt erhalten“ und
   „später bei Auflösung erhalten“ darstellen.
4. Vor der Auflösung eindeutig bestätigen lassen, dass der offene Rest jetzt
   physisch korrekt eingetroffen ist und anschließend eingebucht wird.
5. Vor einer manuellen Korrektur der lokalen Trades 28/29 fachlich klären, ob
   die Auflösung tatsächlich versehentlich erfolgte. Keine automatische
   Rückbuchung vornehmen.

Das sind Empfehlungen; in dieser Untersuchung wurde nichts davon umgesetzt.

## Unverändertheitsbestätigung

- Es wurden ausschließlich temporäre Datenbanken und read-only Abfragen der
  lokalen Entwicklungsdatenbank verwendet.
- Die lokale Datenbank wurde weder migriert noch durch Test- oder
  Produktaktionen verändert.
- SHA-256 der lokalen Datenbank vor und nach der Untersuchung:
  `cf34bf79cffe63521b46a552fc3863c455567fadd0e3a9e03b61ed17e97efcc9`.
- SHA-256 der kanonischen S00-Fixture vor und nach der Untersuchung:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Es wurden keine Anwendungscode-, Test-, Migrations- oder
  Datenbankschemaänderungen vorgenommen.
- Neu erstellt wurde ausschließlich dieser Untersuchungsbericht.
- Es wurde kein Refactoring, kein neuer Sprint, kein Commit und kein Push
  durchgeführt.
