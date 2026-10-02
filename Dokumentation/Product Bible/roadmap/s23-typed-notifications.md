# S23 – Typisierte Notifications mit Zielobjekt

Stand: 2026-08-07

## Ziel

Neue, für S23 freigegebene Trade-Notifications erhalten einen stabilen Typ,
ein kanonisches Zielobjekt und eine transaktional abgesicherte
Deduplizierungsidentität. Bestehende Legacy-Notifications bleiben unverändert
lesbar. S23 baut keine Notification-Historie, kein Badge und keine neue
Klick- oder Read-UX.

## Verbindlicher Eventkatalog

| Notification-Typ | Empfänger | Ziel |
| --- | --- | --- |
| `trade_request_created` | Empfänger der manuellen Anfrage | `trade_request` / Legacy-Request-ID |
| `smart_trade_request_created` | Empfänger der Smart-Anfrage | `trade_request` / Legacy-Request-ID |
| `trade_accepted` | ursprünglicher Absender | `trade` / Lifecycle-Trade-ID |
| `trade_shipped` | Gegenseite des Versenders | `trade` / Lifecycle-Trade-ID |
| `trade_received` | Gegenseite des Empfängers | `trade` / Lifecycle-Trade-ID |
| `trade_shipping_overdue` | Nutzer mit überfälligem eigenem Versand | `trade` / Lifecycle-Trade-ID |
| `trade_receipt_overdue` | Nutzer mit ausstehender Empfangsbestätigung | `trade` / Lifecycle-Trade-ID |

Andere Typen, insbesondere Problem-, Abschluss-, Ablehnungs- oder
Smart-48-Stunden-Fristtypen, werden nicht eingeführt. Bereits vorhandene Hooks
außerhalb dieses Katalogs bleiben aus Kompatibilitätsgründen über den
Legacy-Adapter erhalten.

## V0006-Schema

Die bestehende Tabelle `notifications` erhält:

- `notification_type TEXT NOT NULL DEFAULT 'legacy'`
- `target_type TEXT`
- `target_id INTEGER`
- `source_event_id INTEGER`
- `dedupe_key TEXT`

Ein partieller eindeutiger Index auf `dedupe_key` schützt typisierte Einträge
vor paralleler Doppelanlage. Bestehende Zeilen erhalten ausschließlich durch
den Spalten-Default `notification_type = legacy`; Titel, Text, Ziel und
Bedeutung werden nicht rekonstruiert.

Der Down-Pfad ist fail-closed, sobald nicht-legacy typisierte Zeilen vorhanden
sind. Bei ausschließlich Legacy-Daten rekonstruiert er das unveränderte
V0005-Tabellenformat. Dadurch kann kein typisierter Verlauf stillschweigend
verloren gehen.

## Architektur

### `TypedNotificationService`

Der neue Service besitzt vier Aufgaben:

1. typisierte Notification validieren und mit `INSERT OR IGNORE` anlegen,
2. Datenbankzeilen als immutable DTOs lesen,
3. ein Zielobjekt für den berechtigten Empfänger in einen kanonischen internen
   Pfad auflösen,
4. überfällige Versand- und Empfangszustände lazy projizieren.

Der Service verändert keine Trade-, Inventory-, Reservation-, Shipping-,
Receipt- oder Problemzustände.

### Lifecycle-Adapter

S23 ändert die geschützten Fachservices nicht:

- Annahme: Der vorhandene `on_accepted`-Hook legt ein informatives
  `accepted`-Event und die typisierte Notification innerhalb derselben
  bestehenden Transaktion an.
- Versand: Nach einem erfolgreichen oder wiederholten Route-Aufruf stellt der
  Adapter anhand des vorhandenen Shipping-Status ein eindeutiges
  `shipment_confirmed`-Event je Seite sicher und projiziert daraus die
  Notification. Ein Retry heilt damit auch eine theoretisch zwischen
  Fachcommit und Adapter unterbrochene Projektion.
- Empfang: Der Adapter liest das bereits bestehende `receipt_confirmed`-Event
  je Seite und projiziert daraus die Notification. Direkter Empfang und eine
  spätere vollständige Problemauflösung verwenden denselben Adaptervertrag.

Request-Erzeugung besitzt vor dem Lifecycle kein `trade_events`-Objekt. Hier
ist die gespeicherte Request-ID zugleich die stabile Source-Event-ID.

## DTOs

- `NotificationTargetDTO(target_type, target_id)`
- `TypedNotificationDTO(...)`
- `NotificationCreateResultDTO(notification, created)`

Alle DTOs sind immutable. `target_path_for(...)` gibt nur für den
Notification-Empfänger und einen weiterhin berechtigten Tradebeteiligten einen
internen Pfad zurück. S23 rendert oder öffnet diesen Pfad noch nicht.

## Deduplizierung

Normalfall mit Ereignis:

```text
recipient_id:notification_type:source_event_id
```

Lazy Frist ohne Ereignis:

```text
recipient_id:notification_type:target_type:target_id
```

Der eindeutige Datenbankindex ist die letzte Instanz gegen parallele
Erzeugung. Ein Retry erhält das bereits existierende DTO und meldet
`created = false`.

## Lazy Fristprojektion

Die Projektion wird nur an bereits relevanten GET-Einstiegen aufgerufen:

- globale Tradeübersicht,
- albumbezogene Tradeübersicht,
- Dealansicht,
- bestehender Notificationbereich.

Versandüberfälligkeit verwendet dieselbe S18-Regel: fünf Werktage nach dem
vorhandenen Annahmezeitpunkt, solange der eigene Versand fehlt.

Empfangsüberfälligkeit verwendet dieselbe S18-Regel: 14 Kalendertage nach dem
Versand der Gegenseite, solange der eigene Empfang fehlt. Ein bereits offener
Problembericht dieser Empfängerseite verhindert die Fristnotification analog
zum bestehenden S18-Hinweis.

Es gibt keinen Hintergrundprozess und keine Smart-Request-Ablaufnotification.

## Datenfluss und Transaktionen

### Tradeanfrage

```text
Request validieren → trade_requests INSERT → typisierte Notification
→ gemeinsamer Commit
```

### Annahme

```text
bestehender Reservation-Service → Lifecycle-Trade → accepted Event
→ typisierte Notification → bestehender gemeinsamer Commit
```

### Versand und Empfang

```text
geschützter Fachservice → bestehender Fachcommit
→ idempotenter Event-/Notification-Adapter → eigener kurzer Commit
```

Bei einem Retry wird nur eine fehlende Projektion ergänzt; Fachbuchungen werden
nicht wiederholt.

### Read-Pfade

Legacy- und typisierte Notifications bleiben über den vorhandenen
`unread_notifications(...)`-Adapter lesbar. Die neue DTO-/Zielauflösung ist
eine zusätzliche S23-Service-API und verändert die S06-Shell nicht.

## Seiteneffekte

Erlaubte S23-Schreibvorgänge:

- V0006 auf expliziten Zieldatenbanken,
- typisierte Notification-Zeilen,
- rein informative `accepted`- und `shipment_confirmed`-Lifecycle-Events,
- lazy, deduplizierte Fristnotifications an den freigegebenen Einstiegen.

Nicht erlaubt und nicht enthalten:

- Trade- oder Inventory-Zustandsänderung,
- Problemnotifications,
- Smart-48-Stunden-Fristnotification,
- rückwirkende semantische Typisierung,
- Badge, Historie, Pagination, Klickverhalten oder Mark-as-read-UX,
- `origin=notifications` oder ein neuer Navigation-Stack,
- Arbeit an S24.

## Unveränderte Komponenten

- Inventory und Shared Availability Snapshot,
- Coverage, TopMatch und SmartTradeRequestService,
- TradeReservationService,
- TradeShippingService,
- TradeReceiptService,
- TradeProblemService,
- bestehende Lifecycle-, Versand-, Empfangs- und Problemregeln,
- bestehende Notification-Shell und Read-State-Route.

## Risiken und Gegenmaßnahmen

- **Retry-Duplikate:** semantischer Key plus Unique Index.
- **Parallele Erzeugung:** `INSERT OR IGNORE` gegen denselben Unique Index.
- **Fremdes Ziel:** Empfänger- und Objektberechtigung bei der Zielauflösung.
- **Legacy-Verlust:** Default `legacy`, kein Backfill, fail-closed Backout.
- **Fachservice-Kopplung:** Adapter ausschließlich über vorhandene Callbacks,
  Ergebnisse, Statuszeilen und Events.
- **GET-Seiteneffekt:** ausschließlich die vom Product Owner freigegebene lazy
  Fristprojektion, niemals Fachstatus oder Read-State.

## Testvertrag

Jeder der sieben Typen, Empfänger, Zieltyp/-ID, beide Versand- und
Empfangsseiten, Request-vs.-Lifecycle-Ziel, Smart-Eindeutigkeit, beide lazy
Fristen, Retry, Parallelität, Fremdziel, Legacy-Lesbarkeit, kein Backfill,
V0006 Up/Repeat/Down/fail-closed sowie vollständige S01–S22-Regression.
