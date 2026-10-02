# S16 – Empfang je Seite und sichere Bestandsbuchung

Stand: 2026-08-02

## Zweck und Scope

S16 ergänzt den seit S15 seitenbezogenen Versand um die vollständige
Empfangsbestätigung je Empfänger. Ein Eingang wird erst dann physisch gebucht,
wenn genau der jeweilige Empfänger den Erhalt der vollständigen Sendung
bestätigt. Der erste Empfang bucht nur diese Seite; erst der zweite Empfang
schließt den Trade ab.

Nicht Bestandteil sind Teilempfang, falsche, beschädigte oder verlorene
Sticker, Problemfälle, Chat, Bewertung, Tracking, Fristen oder automatischer
Support. Der Service kennt ausschließlich „vollständig empfangen“ oder „noch
nicht empfangen“.

## Versioniertes Empfangsmodell V0004

V0004 ergänzt `trade_receipt_status` mit genau einer Zeile je Lifecycle-Trade:

- `requester_received` und `requester_received_at`,
- `partner_received` und `partner_received_at`,
- `updated_at`,
- `trade_id` als eindeutiger Fremdschlüssel auf `trades`.

Die Seite bezeichnet hier den **Empfänger**:

- `requester_received`: Der Anfrageersteller hat die vom Partner gesendeten
  Positionen erhalten.
- `partner_received`: Der Anfrageempfänger hat die vom Anfrageersteller
  gesendeten Positionen erhalten.

Checks erlauben nur `0/1` und koppeln jede Bestätigung an genau einen
Zeitstempel. V0004 übernimmt bestehende V0003-Lifecycle-Trades in den Zuständen
`accepted`, `partially_shipped`, `shipped` oder `partially_received` mit zwei
offenen Empfangsseiten. Legacy-Trades ohne Lifecycle-Zuordnung bleiben
unverändert und lesbar.

Der Backout nach V0003 ist nur erlaubt, solange noch keine Seite einen Empfang
bestätigt hat. Nach der ersten realen Bestandsbuchung scheitert er fail-closed.

## Berechtigungs- und Zustandsregeln

`TradeReceiptService.receive()` akzeptiert ausschließlich:

1. einen Trade mit installiertem V0004- und V0003-Schema,
2. einen am Trade beteiligten Nutzer,
3. den Legacy-Status `accepted`,
4. einen Lifecycle in `partially_shipped`, `shipped` oder
   `partially_received`,
5. einen bestätigten Versand der Gegenseite,
6. vollständige Lifecycle-Positionen mit `to_user_id` gleich dem bestätigenden
   Nutzer.

Der Nutzer kann keinen Empfänger und keine fremde Seite übergeben. Die Route
leitet ausschließlich die aktuelle Session-Nutzer-ID weiter. Eine
Empfangsbestätigung vor dem Versand der Gegenseite, durch einen fremden Nutzer
oder in einem falschen Lifecycle verändert weder Status noch Bestand.

## Atomare Buchungsregel

Der gesamte Empfang einer Seite läuft unter `BEGIN IMMEDIATE`:

1. Trade, Lifecycle, Beteiligung und Versand der Gegenseite prüfen.
2. Bereits bestätigten Empfang als idempotenten No-op erkennen.
3. Alle Positionen mit `to_user_id = aktueller Empfänger` vollständig laden.
4. Jede Positionsmenge über `InventoryWriteService.add()` einbuchen.
5. Genau den Empfangsmarker dieser Seite und seinen ersten Zeitstempel setzen.
6. Ein `receipt_confirmed`-Lifecycle-Event schreiben.
7. Lifecycle auf `partially_received` setzen oder bei zwei Empfängen den
   kontrollierten Abschluss durchführen.
8. Gemeinsam committen oder vollständig zurückrollen.

Es gibt keinen Positionsparameter und keine Teilmenge. Entweder werden alle
eingehenden Positionen der Seite gebucht oder keine.

## Inventory-Abbildung

Vor Empfang gilt für eine versendete eingehende Position:

```text
incoming_transit = Positionsmenge
physical         = unverändert
assigned         = unverändert
available        = unverändert
```

Nach Empfang gilt:

```text
incoming_transit = 0
physical         = physical + Positionsmenge
assigned         = min(physical, 1)
available        = max(physical - assigned - reserved, 0)
```

Die physische Buchung aktualisiert die bestehende `stickers.quantity` und
`duplicates`-Kompatibilität ausschließlich über den Inventory Write Service.
Albumfortschritt und Availability werden anschließend aus derselben zentralen
Inventory-Leseprojektion abgeleitet. Es existiert keine separate
Fortschrittsbuchung und damit keine zweite Zählquelle.

Die Transitprojektion berücksichtigt den Versand der sendenden Seite nur,
solange die empfangende Seite noch nicht bestätigt hat. So verschwindet nur
der Transit des bestätigenden Empfängers; die Sendung der anderen Seite bleibt
unabhängig unterwegs.

## Erster und zweiter Empfang

```text
kein Empfang
  ├─ requester empfängt → requester_received=1 → partially_received
  └─ partner empfängt   → partner_received=1   → partially_received

partially_received
  └─ andere Seite empfängt
       → beide received=1
       → lifecycle_state=completed
       → trade_requests.status=completed
```

Nach dem ersten Empfang erhält ausschließlich diese Seite ihre Positionen.
Der Legacy-Trade bleibt `accepted`. Versand und Empfang bleiben unabhängig:
Eine Seite darf eine bereits angekommene Gegensendung bestätigen, bevor sie
den eigenen Versand bestätigt. Ein späterer eigener Versand bewahrt deshalb
`partially_received`.

## Kontrollierter Abschluss

Nur der Übergang vom ersten zum zweiten Empfang führt gemeinsam aus:

- `trades.lifecycle_state = completed`,
- `trades.completed_at` setzen,
- `trade_requests.status = completed`,
- Legacy-Bestätigungsmarker auf `1/1` setzen,
- `completed`-Lifecycle-Event schreiben,
- die bestehenden zwei Abschlussbenachrichtigungen wiederverwenden,
- die bestehenden Album- und globalen Trophy-Hooks ausführen.

Die alte `complete_trade()`-Bestandsfunktion wird dabei bewusst **nicht**
erneut aufgerufen: S15 hat den physischen Ausgang bereits beim Versand
abgezogen und S16 hat den Eingang je Empfänger gebucht. Ein erneuter
Altabschluss würde beide Seiten doppelt verändern. Wiederverwendet werden die
bestehenden Abschlussnebenwirkungen und das Legacy-Abschlussmapping.

## Idempotenz und Fehlercodes

Der Empfangsmarker wird mit einem zustandsgebundenen Update gesetzt. Unter der
sofortigen SQLite-Schreibsperre kann nur der erste Aufruf buchen. Wiederholungen
liefern `ALREADY_RECEIVED` mit dem ursprünglichen Zeitpunkt und erzeugen keine
weiteren Inventory-, Event-, Notification- oder Trophy-Schreibvorgänge.

Stabile Ergebniswerte:

- `RECEIVED`
- `ALREADY_RECEIVED`
- `NOT_SHIPPED`
- `INVALID_TRADE_STATE`
- `UNAUTHORIZED`
- `TRANSACTION_ERROR`

Bei einem Fehler wird die gesamte Transaktion zurückgerollt.

## Minimale Bedienoberfläche

Die bestehende Dealansicht zeigt „Empfang bestätigen“ nur, wenn:

- V0004 verfügbar ist,
- der aktuelle Nutzer beteiligt ist,
- die Gegenseite versendet hat,
- der aktuelle Nutzer noch nicht empfangen hat.

Nach Bestätigung wird der Zustand deaktiviert als „Empfang bestätigt“
dargestellt. Es wurden keine CSS- oder Designänderungen vorgenommen.

## Tests und Datenbankschutz

`tests/test_s16_trade_receipt.py` arbeitet je Test auf einer eigenen
temporären Kopie der kanonischen S00-Fixture und migriert ausschließlich diese
Kopie gezielt bis V0004. Abgedeckt sind beide Seiten und Reihenfolgen,
Zwischenzustand, zweiter Abschluss, Transit, Physical, Assigned, Available,
Fortschritt, Retry, Berechtigung, Lifecycle, Versandvoraussetzung,
Trophy-/Notification-Einmaligkeit, V0003→V0004 und Legacy-Lesbarkeit.

Pflichtgate:

```bash
python3 -m unittest discover -s tests -p "test_s*.py" -v
```

Die lokale Standarddatenbank und die kanonische S00-Fixture sind niemals
Testziele.

## Bewusst nicht umgesetzt: S17+

- Teilempfang oder einzelne empfangene Positionen,
- falsche, beschädigte, fehlende oder verlorene Sticker,
- Problemworkflow oder Schuldentscheidung,
- Chat, Bilder oder Bewertung,
- Tracking oder Versanddienstleister,
- Fristen, Eskalationen oder automatischer Support,
- Home- oder Notification-Historienfunktionen,
- Designpolitur.
