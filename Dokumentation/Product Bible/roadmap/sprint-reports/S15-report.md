# Sprintbericht S15 – Versandstatus je Seite und Unterwegs-Zustand

Stand: 2026-08-02

## Ergebnis

Sprint S15 wurde ausschließlich im vorgegebenen Umfang umgesetzt. Auf einer
explizit bis V0003 migrierten Datenbank kann jede beteiligte Seite unabhängig
den Versand ausschließlich ihrer eigenen ausgehenden Positionen bestätigen.

Der Versandübergang läuft atomar:

- Beteiligung, Lifecycle, Positionen und aktive Reservierungen werden geprüft,
- die eigenen Reservierungen werden nachvollziehbar als `shipped` freigegeben,
- die eigenen physischen Mengen werden über den Inventory Write Service
  reduziert,
- der eigene Status und erste Versandzeitpunkt werden gespeichert,
- dieselben Positionen erscheinen beim Empfänger zentral als
  `incoming_transit`.

Der Legacy-Trade bleibt auch nach beidseitigem Versand `accepted`. Es wurde kein
Empfang, Teilempfang oder automatischer Abschluss umgesetzt.

## Neue Dateien

- `App/Database/migrations/0003_trade_shipping_status.up.sql`
  - versioniertes seitenbezogenes Versandstatusmodell
- `App/Database/migrations/0003_trade_shipping_status.down.sql`
  - leerer Backout und fail-closed Schutz nach erstem Versand
- `App/services/trade_shipping.py`
  - atomarer, seitenbezogener und idempotenter Versandservice
  - Shipping-Status-DTO und stabile Ergebniszustände
- `tests/test_s15_trade_shipping.py`
  - S15-Migrations-, Service-, Inventory-, UI- und Berechtigungstests
- `Dokumentation/Product Bible/roadmap/s15-trade-shipping-transit.md`
  - verbindlicher Versand-/Transit-Vertrag
- `Dokumentation/Product Bible/roadmap/sprint-reports/S15-report.md`
  - dieser Sprintbericht

## Geänderte Dateien

- `App/services/inventory_availability.py`
  - `incoming_transit` als eigenständigen, nicht physischen Wert ergänzt
- `App/services/inventory.py`
  - Transitprojektion aus Tradeposition und versendeter Seite ergänzt
  - eingehenden Transit auch für noch nicht physisch vorhandene Codes
    darstellbar gemacht
- `App/services/trade_reservations.py`
  - leeren V0003-Seitenstatus bei neuer erfolgreicher Annahme innerhalb
    derselben Transaktion ergänzt
- `App/webapp.py`
  - POST-Route für die eigene Versandbestätigung
  - einfache seitenbezogene Statusdarstellung in der Dealansicht
  - Tradeübersichten auf den Versandstatus statt alten Abschlussdialog gelenkt
  - generischen Abschluss für V0003-Trades gegen Doppelbuchung geschützt
  - pauschales `failed` nach erstem Versand gesperrt
- `tests/test_s14_trade_reservations.py`
  - abgeschlossenen S14-Vertrag explizit auf Zielversion V0002 fixiert
- `Dokumentation/Product Bible/roadmap/README.md`
  - ausschließlich S15-Spezifikation und Bericht verlinkt

Weitere bereits vorhandene Änderungen im Arbeitsverzeichnis wurden weder S15
zugerechnet noch zurückgesetzt. Die vorhandene Änderung an
`App/static/style.css` ist keine S15-Änderung; S15 hat keine CSS-Datei geändert.

## Versandstatus und Zeitstempel

`trade_shipping_status` enthält genau eine Zeile je Lifecycle-Trade:

- `requester_shipped` und `requester_shipped_at`,
- `partner_shipped` und `partner_shipped_at`,
- `updated_at`,
- eindeutigen FK `trade_id`.

Checks erzwingen Statuswerte `0/1` und koppeln einen bestätigten Status an einen
gesetzten Zeitstempel. Ein offener Status darf keinen Versandzeitpunkt besitzen.

V0003 erzeugt leere Statuszeilen für bereits bestehende versandfähige
Lifecycle-Trades. Neue S14-Annahmen erzeugen die Statuszeile innerhalb ihrer
bestehenden atomaren Annahmetransaktion.

## Erlaubte Übergänge

```text
0 / 0 → requester 1 / partner 0 → partially_shipped
0 / 0 → requester 0 / partner 1 → partially_shipped
1 / 0 → requester 1 / partner 1 → shipped
0 / 1 → requester 1 / partner 1 → shipped
```

Wiederholungen einer bereits versendeten Seite sind No-ops. Keine Seite wartet
auf die andere. Nach `shipped` bleibt der Legacy-Trade `accepted`, da Empfang
und Abschluss erst in späteren Sprints definiert werden.

## Berechtigungsregeln

Der Versandservice akzeptiert ausschließlich:

- einen am Trade beteiligten Nutzer,
- Legacy-Status `accepted`,
- Lifecycle `accepted`, `partially_shipped` oder `shipped`,
- die eigenen ausgehenden Positionen,
- vollständig aktive und mengenidentische Reservierungen dieser Positionen.

Die Route besitzt keinen Parameter für eine fremde Seite. Anfrageersteller und
Anfrageempfänger können daher jeweils nur ihren eigenen Versand bestätigen.
Fremde Nutzer, offene Trades oder inkonsistente Reservierungen erzeugen keine
Mutation.

## Transaktionsgrenze

`TradeShippingService.ship()` führt unter `BEGIN IMMEDIATE` gemeinsam aus:

1. Legacy- und Lifecycle-Zustand prüfen.
2. Beteiligung und eigene Seite bestimmen.
3. eigenen bisherigen Status prüfen.
4. eigene Positionen und aktive Reservierungen vollständig validieren.
5. eigene Reservierungen auf `released`, Grund `shipped`, setzen.
6. physische Mengen über `InventoryWriteService` reduzieren.
7. eigenen Status und ersten Zeitpunkt setzen.
8. Lifecycle auf `partially_shipped` oder `shipped` setzen.
9. gemeinsam committen.

Jeder Fehler rollt Reservierungen, Bestände, Versandstatus und Lifecycle
vollständig zurück.

## Inventory- und Transit-Semantik

Beim Versand sinken beim Absender `physical` und `reserved` um dieselbe Menge.
Damit bleibt dessen `available` korrekt:

```text
vorher:  physical=3, assigned=1, reserved=1, available=1
nachher: physical=2, assigned=1, reserved=0, available=1
```

Beim Empfänger steigt `incoming_transit`. Dieser Wert erhöht weder `physical`,
`assigned`, `available` noch gesammelte Menge oder Albumfortschrittsprozent.

Transit wird nicht als zweite Bestandszeile gespeichert. Der Inventory Read
Service leitet ihn aus gerichteter Tradeposition und eindeutigem Seitenstatus
ab. Dadurch wird jede versendete Position genau einmal gezählt.

Die Reservierung bleibt als Historie mit ursprünglicher Menge, Erstell- und
Freigabezeitpunkt sowie `release_reason='shipped'` nachvollziehbar. Die
Reservierungen der noch nicht versendeten Gegenseite bleiben aktiv.

## Idempotenz

Ein wiederholter eigener Versand liefert `ALREADY_SHIPPED` und:

- erhält den ersten Zeitstempel,
- reduziert Physical nicht erneut,
- verändert die Reservierung nicht erneut,
- erhöht Transit nicht erneut,
- erzeugt keine Notification und keine Trophy.

S15 führt keinen neuen Notificationtyp ein.

## Schutz des bestehenden Tradeflows

Legacy-Trades ohne V0003 verwenden weiterhin den bestehenden generischen
Abschluss und bestanden sämtliche S02-Regressionstests.

Für V0003-Trades ist der alte generische Abschluss gesperrt, weil er nach der
physischen Versandbuchung dieselbe Position doppelt ausbuchen und einen
Empfangszugang vorwegnehmen würde. Nach dem ersten Versand ist auch der
pauschale Legacy-`failed`-Pfad gesperrt; eine Rückabwicklung versendeter
Positionen wäre ein ausdrücklich ausgeschlossener Problem-/Empfangsfall. Vor
dem ersten Versand bleibt das bestehende S14-Ende `failed` zulässig.

## Stabile Ergebniszustände

- `SHIPPED`
- `ALREADY_SHIPPED`
- `INVALID_TRADE_STATE`
- `UNAUTHORIZED`
- `MISSING_RESERVATIONS`
- `TRANSACTION_ERROR`

Alle Zustände sind UI-neutrale String-Enums in einem unveränderlichen DTO.

## Einfache Status-UI

Die bestehende Dealansicht zeigt funktional:

- eigenen offenen beziehungsweise bestätigten Versand,
- offenen beziehungsweise bestätigten Versand der Gegenseite,
- „Erwartete Sticker sind unterwegs“, sobald die Gegenseite versendet hat,
- einen POST-Button ausschließlich für den eigenen noch offenen Versand.

Es wurden keine CSS-Politur, Trackingfelder, Versandlabels oder neue globale
Home-/Notification-Oberflächen ergänzt.

## Migration und Backout

Vorwärtsmigration wurde auf leeren temporären Datenbanken und temporären
Fixture-Kopien geprüft. Wiederholte Ausführung ist ein No-op.

Der Backout auf V0002 funktioniert, solange keine Seite versendet hat. Nach dem
ersten Versand bricht die Down-Migration fail-closed ab und erhält Status,
Ledger und Daten. Das verhindert einen Schemaabbau nach bereits erfolgter
physischer Ausbuchung. Ein späterer Backout benötigt einen eigenen versionierten
Recovery-Plan.

## Testübersicht

S15-spezifischer Testbefehl:

```text
python3 -m unittest tests.test_s15_trade_shipping -v
```

Ergebnis: 24 von 24 Tests erfolgreich.

Geprüft wurden:

1. Angenommener Trade startet mit zwei offenen Seiten.
2. Nur Anfrageersteller versendet eigene Positionen.
3. Nur Anfrageempfänger versendet eigene Positionen.
4. Beide Seiten versenden unabhängig; Trade wird nicht abgeschlossen.
5. Eine Seite kann die andere nicht bestätigen.
6. Fremder Nutzer bleibt ohne Wirkung.
7. Offener Trade kann nicht versendet werden.
8. Fehlende aktive Reservierung blockiert atomar.
9. Wiederholter Versand ist idempotent.
10. Seitenzeitpunkte werden genau einmal gespeichert.
11. Transit steigt ausschließlich beim Empfänger.
12. Transit erhöht Physical, assigned, available oder Fortschritt nicht.
13. Sender-Availability bleibt korrekt und nichtnegativ.
14. Wiederholung zählt Transit nicht doppelt.
15. Reservierungen bleiben vollständig nachvollziehbar.
16. Dealansicht zeigt beide seitenbezogenen Zustände und Transit.
17. Legacy-Abschluss kann S15-Bestand nicht doppelt buchen.
18. Pauschales Legacy-`failed` ist nach Versand gesperrt.
19. Versand erzeugt weder Notification noch Trophy.
20. Alle Ergebniszustände sind stabil und UI-neutral.
21. Migration, No-op und leerer Backout funktionieren.
22. Backout nach Versand scheitert sicher.
23. Bestehender `completed`-Legacy-Trade bleibt lesbar.
24. Produktivdatenbank und kanonische Fixture bleiben unverändert.

Vollständiges Gate, zweimal ausgeführt:

```text
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Abschlusslauf 1: 199 von 199 Tests erfolgreich (`OK`).
- Abschlusslauf 2: 199 von 199 Tests erfolgreich (`OK`).

## Schutz der kanonischen Datenbanken

Vor und nach beiden Abschlussläufen waren die Prüfsummen identisch:

- `App/Database/sammlr.db`:
  `70f2e8f55b441931372d3a422fbe3dd455630418bdc0ab0de412af6c59b27a26`
- `App/Database/sammlr_reference_s00.db`:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`

Migrationen liefen ausschließlich auf temporären Datenbanken und Kopien. Die
bereits vorhandene benutzerverwaltete Änderung an `sammlr.db` wurde weder
migriert noch zurückgesetzt. `git diff --check` war ohne Befund.

## Bewusst offene Punkte für S16+

Nicht begonnen oder vorbereitet wurden:

- Empfangsbestätigung und Bestandszugang beim Empfänger,
- Teilempfang,
- automatische Dealabschlüsse,
- falsche, beschädigte oder verlorene Sendungen,
- Rückabwicklung physisch versendeter Positionen,
- Tracking, Dienstleister, Label oder Versicherung,
- Chat, Bilder oder Bewertung,
- Fristen,
- neue Home-Aufgaben oder Notification-Historie,
- Designpolitur.

## Scope-Bestätigung

- Ausschließlich Sprint S15 wurde umgesetzt.
- Sprint S16 wurde nicht begonnen.
- Es wurden keine Empfangs- oder Teilempfangsfunktionen umgesetzt.
- Es wurden keine Problemfälle, Tracking-, Label- oder Versicherungsfunktionen
  umgesetzt.
- Es wurden keine Bewertungen ergänzt.
- Es wurden keine neuen Notificationtypen umgesetzt.
- Es wurde keine CSS-Datei für S15 geändert.
- Legacy-Tradehistorie, Papierlisten- und bestehende nicht migrierte
  Abschlussflows blieben kompatibel.
- Produktivdatenbank und kanonische Fixture wurden nicht migriert oder verändert.
- Es wurde kein Commit erstellt und kein Push durchgeführt.
