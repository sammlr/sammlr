# S15 – Versandstatus je Seite und Unterwegs-Zustand

Stand: 2026-08-02

## Zweck und Sprintgrenze

S15 erlaubt beiden Beteiligten eines angenommenen S14-Trades, ausschließlich
den Versand ihrer eigenen ausgehenden Positionen unabhängig zu bestätigen.
Der Versand überführt die aktiven Reservierungen dieser Seite atomar in einen
nachvollziehbaren Versandzustand, reduziert den physischen Bestand beim Absender
und projiziert dieselben Positionen beim Empfänger als `incoming_transit`.

Der Trade bleibt nach ein- oder beidseitigem Versand offen. S15 enthält keine
Empfangsbestätigung, keine Bestandsbuchung beim Empfänger, keinen Teilempfang,
keine Problemfälle und keinen automatischen Abschluss.

## Versionierte Migration V0003

S15 ergänzt ausschließlich über den S13-Migrationsmechanismus:

```text
0003_trade_shipping_status
```

Dateien:

- `App/Database/migrations/0003_trade_shipping_status.up.sql`
- `App/Database/migrations/0003_trade_shipping_status.down.sql`

Es gibt kein Startup-`ALTER` und keine automatische Migration in
`App/webapp.py`. V0003 wird nur auf einem explizit gewählten Datenbankpfad
ausgeführt.

## Versandstatusmodell

### `trade_shipping_status`

Die Tabelle besitzt genau eine Zeile je Lifecycle-Trade:

| Feld | Bedeutung |
| --- | --- |
| `trade_id` | eindeutiger FK auf `trades` |
| `requester_shipped` | Versandstatus des Anfrageerstellers, `0/1` |
| `requester_shipped_at` | unveränderter erster Versandzeitpunkt dieser Seite |
| `partner_shipped` | Versandstatus des Anfrageempfängers, `0/1` |
| `partner_shipped_at` | unveränderter erster Versandzeitpunkt dieser Seite |
| `updated_at` | letzter Statuswechsel einer Seite |

Constraints koppeln jeden bestätigten Status zwingend an einen Zeitstempel und
jeden offenen Status an einen leeren Zeitstempel.

V0003 legt für bereits bestehende Lifecycle-Trades in einem versandfähigen
Zustand eine leere Statuszeile an. Neue S14-Annahmen erzeugen dieselbe Zeile
atomar innerhalb der Annahmetransaktion. Legacy-Trades ohne Lifecycle werden
nicht nachträglich migriert.

## Erlaubte Zustandskombinationen

```text
requester=0, partner=0  → niemand versendet
requester=1, partner=0  → nur Anfrageersteller versendet
requester=0, partner=1  → nur Anfrageempfänger versendet
requester=1, partner=1  → beide Seiten versendet
```

Die erste Versandbestätigung setzt `trades.lifecycle_state` auf
`partially_shipped`; die zweite auf `shipped`. Der bestehende Legacy-Status
bleibt `accepted`, weil S15 den Deal noch nicht abschließt.

Eine Seite wartet nicht auf die andere. Jede Reihenfolge ist zulässig. Der
erneute Aufruf einer bereits bestätigten Seite ist ein idempotenter No-op.

## Berechtigungsregeln

Versand ist nur zulässig, wenn:

- ein eindeutiger Lifecycle-Trade zur Legacy-Anfrage existiert,
- der Legacy-Status `accepted` ist,
- der Lifecycle-Zustand `accepted`, `partially_shipped` oder `shipped` ist,
- der Akteur Anfrageersteller oder Anfrageempfänger ist,
- ausschließlich die ausgehenden Positionen des Akteurs gewählt werden,
- jede dieser Positionen noch vollständig aktiv reserviert ist.

Die Route enthält keine auswählbare „Seite“. Der angemeldete Nutzer kann daher
nur den eigenen Versand auslösen. Ein fremder Nutzer, offener Trade oder Trade
mit fehlenden Reservierungen bleibt vollständig unverändert.

## Atomarer Versandübergang

`TradeShippingService.ship()` besitzt die Transaktionsgrenze:

```text
BEGIN IMMEDIATE
  1. Legacy- und Lifecycle-Zustand laden
  2. Beteiligung und eigene Seite bestimmen
  3. bestehenden Seitenstatus prüfen
  4. alle eigenen Positionen und aktiven Reservierungen validieren
  5. eigene Reservierungen auf released / reason=shipped setzen
  6. eigene physische Mengen über InventoryWriteService reduzieren
  7. eigenen Seitenstatus und ersten Zeitstempel setzen
  8. Lifecycle auf partially_shipped oder shipped setzen
COMMIT
```

Jeder fachliche oder technische Fehler führt zum vollständigen Rollback. Es
gibt weder teilweise ausgebuchte Positionen noch einen Versandstatus ohne
passenden Bestandsübergang.

## Inventory- und Transit-Semantik

Vor Versand einer Position gilt nach S14:

```text
physical = assigned + reserved + available
```

Beim Versand derselben Position:

- die aktive Reservierung wird nachvollziehbar mit `release_reason='shipped'`
  freigegeben,
- `physical` des Absenders sinkt über den zentralen Write Service um die
  versendete Menge,
- `reserved` des Absenders sinkt um dieselbe Menge,
- `available` des Absenders bleibt dadurch korrekt gebunden beziehungsweise
  unverändert,
- beim Empfänger steigt `incoming_transit` um dieselbe Positionsmenge.

Beispiel:

```text
vor Versand:   physical=3, assigned=1, reserved=1, available=1
nach Versand:  physical=2, assigned=1, reserved=0, available=1
Empfänger:     incoming_transit=1
```

`incoming_transit` wird aus Tradeposition und eindeutigem Seitenstatus zentral
abgeleitet. Es wird nicht als zweite Mengenzeile gespeichert und kann dadurch
nicht doppelt gezählt werden.

Für den Empfänger gilt ausdrücklich:

- `incoming_transit` ist nicht `physical`,
- `incoming_transit` ist nicht `assigned`,
- `incoming_transit` ist nicht `available`,
- `incoming_transit` verändert keine gesammelte Menge und keinen
  Albumfortschrittswert.

Erst ein späterer, ausdrücklich nicht in S15 enthaltener Empfangsübergang darf
den eingehenden Transit in physischen Bestand überführen.

## Reservierungsnachweis

S15 löscht Reservierungen nicht. Die versendete Seite bleibt anhand von

- Lifecycle-Trade,
- Tradeposition,
- ursprünglicher reservierter Menge,
- `created_at`,
- `state='released'`,
- `released_at`,
- `release_reason='shipped'`

vollständig nachvollziehbar. Reservierungen der noch nicht versendeten
Gegenseite bleiben `active` und schützen deren Bestand weiterhin über den
Inventory Guard.

## Idempotenz

Wiederholtes Bestätigen derselben Seite liefert `ALREADY_SHIPPED` und:

- behält den ersten Versandzeitpunkt,
- reduziert keinen Bestand erneut,
- verändert keine Reservierung erneut,
- verdoppelt kein `incoming_transit`,
- erzeugt keine Notification oder Trophy.

S15 führt bewusst keinen neuen Versand-Notificationtyp ein.

## Schutz vor dem Legacy-Abschluss

Der bestehende generische Bestätigungs-/Abschlussflow bleibt für Legacy-Trades
ohne V0003 unverändert. Für einen Lifecycle-Trade mit Versandstatus wird er
gesperrt, weil er die bereits beim Versand ausgebuchten Positionen sonst doppelt
buchen und einen noch nicht implementierten Empfang vorwegnehmen würde.

Auch der bestehende pauschale `failed`-Pfad bleibt nach dem ersten Versand
gesperrt. Eine Rückabwicklung versendeter physischer Positionen wäre ein
Problem-/Empfangsfall und gehört ausdrücklich nicht in S15. Vor dem ersten
Versand bleibt das bestehende S14-Ende `failed` zulässig.

## Stabile Ergebniszustände

| Code | Bedeutung |
| --- | --- |
| `SHIPPED` | eigener Versand vollständig atomar bestätigt |
| `ALREADY_SHIPPED` | idempotente Wiederholung ohne Mutation |
| `INVALID_TRADE_STATE` | Trade oder Lifecycle nicht versandfähig |
| `UNAUTHORIZED` | Nutzer ist nicht am Trade beteiligt |
| `MISSING_RESERVATIONS` | eigene Positionen sind nicht vollständig aktiv reserviert |
| `TRANSACTION_ERROR` | technischer Fehler; vollständiger Rollback |

Die Codes sind UI-neutrale String-Enums in einem unveränderlichen DTO.

## Einfache Status-UI

Die bestehende Dealansicht zeigt ohne Design Patch:

- „Eigener Versand noch offen“ oder den bestätigten eigenen Versand,
- „Gegenseite hat noch nicht versendet“ oder „Gegenseite hat versendet“,
- „Erwartete Sticker sind unterwegs“, sobald die Gegenseite versendet hat,
- einen POST-Button ausschließlich für den eigenen offenen Versand.

Nach Bestätigung wird der eigene Button deaktiviert dargestellt. Bestehende
Tradeübersichten verweisen für Lifecycle-Trades auf diese Dealansicht, statt den
alten Abschlussdialog anzubieten. Es wurden keine Tracking-, Label-,
Versicherungs-, Home- oder Notification-Oberflächen ergänzt und keine CSS-Datei
geändert.

## Migration und sicherer Backout

Vorwärts auf einer Testkopie:

```text
python3 -m App.Database.migration_runner up --database /absoluter/pfad/testkopie.db
```

Backout vor dem ersten Versand:

```text
python3 -m App.Database.migration_runner down --database /absoluter/pfad/testkopie.db --target 2
```

Die Down-Migration ist fail-closed. Sobald mindestens eine Seite Versand
bestätigt hat, verhindert ein Constraint das Entfernen von V0003 und erhält
Status, Ledger und Daten. Das ist erforderlich, weil physische Mengen bereits
ausgebucht wurden. Nach erster Nutzung benötigt ein Backout einen eigenen
versionierten Recovery-Plan; S15 stellt keinen Empfang oder Versand-Rollback
nach.

## Testvertrag

Die S15-Suite prüft unter anderem:

- alle vier Seitenkombinationen,
- unabhängige Reihenfolge und eigene Berechtigung,
- offene/fremde/inkonsistente Trades,
- idempotente Zeitstempel und Bestandsbewegung,
- Sender-Physical und Empfänger-Transit,
- unveränderte Empfänger-Physical-/Fortschrittswerte,
- S08-Balance und nichtnegative Availability,
- nachvollziehbare Reservierungsüberführung,
- einfache Dealstatus-UI,
- Schutz vor Legacy-Doppelbuchung und pauschalem Fehlerende,
- Migration, No-op, leerer und fail-closed Backout,
- Legacy-`completed`-Trade,
- unveränderte Notifications, Trophäen und kanonische Datenbanken.

## Bewusst nicht umgesetzt: S16+

- Empfangsbestätigung oder Bestandszugang beim Empfänger,
- Teilempfang,
- falsche, beschädigte oder verlorene Sendungen,
- Problemprozess oder Rückabwicklung nach Versand,
- Trackingnummer, Versanddienstleister, Label oder Versicherung,
- Chat, Bilder oder Bewertung,
- Versandfrist oder automatischer Abschluss,
- neue Home-Aufgaben oder Notification-Historie,
- Designpolitur.
