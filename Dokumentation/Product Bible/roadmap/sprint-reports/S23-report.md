# Sprint-Report S23 – Typisierte Notifications mit Zielobjekt

Stand: 2026-08-07

## Ergebnis

S23 ist umgesetzt und release-ready. Neue freigegebene Trade-Notifications
werden ab V0006 mit einem stabilen Typ, genau einem kanonischen Zielobjekt und
einem datenbankseitig eindeutigen Deduplizierungsschlüssel gespeichert.
Bestehende Notifications bleiben ohne semantische Rekonstruktion als
`legacy` lesbar. Es wurden weder S24-Klickverhalten noch Notification-Historie,
Badge-Redesign oder Mark-as-read-UX vorgezogen.

## Ziel und Snapshot des Vertrags

V0006 ergänzt `notifications` ausschließlich um:

- `notification_type`,
- `target_type`,
- `target_id`,
- `source_event_id`,
- `dedupe_key`.

Der verbindliche Katalog ist auf genau diese sieben Typen begrenzt:

| Typ | Empfänger | Kanonisches Ziel |
| --- | --- | --- |
| `trade_request_created` | Empfänger der manuellen Anfrage | `trade_request` / Request-ID |
| `smart_trade_request_created` | Empfänger der Smart-Anfrage | `trade_request` / Request-ID |
| `trade_accepted` | ursprünglicher Absender | `trade` / Lifecycle-Trade-ID |
| `trade_shipped` | Gegenseite des Versenders | `trade` / Lifecycle-Trade-ID |
| `trade_received` | Gegenseite des Empfängers | `trade` / Lifecycle-Trade-ID |
| `trade_shipping_overdue` | Nutzer mit überfälligem eigenem Versand | `trade` / Lifecycle-Trade-ID |
| `trade_receipt_overdue` | Nutzer mit ausstehender Empfangsbestätigung | `trade` / Lifecycle-Trade-ID |

Problemstatus, Tradeabschluss, Ablehnung und der 48-Stunden-Ablauf einer
Smart-Anfrage wurden nicht als neue Typen eingeführt. Vorhandene Hooks
außerhalb des S23-Katalogs bleiben als Legacy-Kompatibilität erhalten.

## Architektur und Datenfluss

Der neue `TypedNotificationService` ist die einzige S23-Komponente für
Validierung, Speicherung, DTO-Lesen, Deduplizierung, sichere Zielauflösung und
lazy Fristprojektion.

### Request vor Annahme

```text
bestehende Request-Validierung
→ trade_requests INSERT
→ typisierte Notification mit target_type=trade_request
→ gemeinsamer Commit
```

Die Request-ID ist vor Entstehung eines Lifecycle-Trades zugleich die stabile
Source-Event-ID.

### Annahme, Versand und Empfang

```text
bestehender Fachpfad
→ vorhandener Lifecycle-Trade bzw. vorhandener Fachstatus
→ eindeutiges Lifecycle-Event je Seite
→ typisierte Notification mit target_type=trade
```

Die Annahmeprojektion läuft im vorhandenen Transaktions-Callback. Versand und
Empfang verwenden nach dem unveränderten Fachservice einen kurzen,
idempotenten Adapter. Beim Empfang wird das bereits vom Receipt-Pfad erzeugte
`receipt_confirmed`-Event gelesen. Retry-Aufrufe wiederholen keine Fachbuchung
und erzeugen keine zweite Notification.

### Lazy Fristen

Die beiden freigegebenen Fristtypen werden ohne Hintergrundprozess beim Öffnen
von Tradeübersicht, albumbezogener Tradeübersicht, Dealansicht oder bestehendem
Notificationbereich projiziert. Versand verwendet die bestehende
Fünf-Werktage-Regel, Empfang die bestehende 14-Kalendertage-Regel. Ein offener
eigener Problembericht unterdrückt wie bisher den Empfangshinweis. Es findet
keine Trade- oder Statusmutation statt.

## DTOs und Deduplizierung

Neu sind die immutable DTOs:

- `NotificationTargetDTO`,
- `TypedNotificationDTO`,
- `NotificationCreateResultDTO`.

Normale Ereignisse verwenden:

```text
recipient_id:notification_type:source_event_id
```

Lazy Fristen ohne Source-Event verwenden:

```text
recipient_id:notification_type:target_type:target_id
```

Ein partieller Unique Index auf `dedupe_key` und `INSERT OR IGNORE` sichern
Retry und parallele Erzeugung transaktional gegen Duplikate ab.

## Neue Dateien

- `App/Database/migrations/0006_typed_notifications.up.sql`
- `App/Database/migrations/0006_typed_notifications.down.sql`
- `App/services/typed_notifications.py`
- `tests/test_s23_typed_notifications.py`
- `Dokumentation/Product Bible/roadmap/s23-typed-notifications.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S23-report.md`

## Geänderte Dateien

- `App/webapp.py`
  - typisierte Projektion an manueller und smarter Request-Erzeugung,
    Annahme, Versand, Empfang und vollständiger Problemauflösung angebunden,
  - lazy Fristprojektion ausschließlich an den freigegebenen read-only
    Einstiegspunkten aufgerufen,
  - Schema-Fallback hält den bestehenden V0005-Legacypfad lauffähig.
- `Dokumentation/Product Bible/roadmap/README.md`
  - S23-Spezifikation und -Report verlinkt,
  - S24 nur als nächster offener Sprint bezeichnet.

## Unveränderte Komponenten

- Inventory einschließlich Read/Write, Guard, Availability und Snapshot,
- TradeCoverageService und TopMatchOptimizationService,
- SmartTradeRequestService,
- TradeReservationService,
- TradeShippingService,
- TradeReceiptService,
- TradeProblemService,
- bestehende Fachregeln für Annahme, Versand, Empfang, Probleme und Abschluss,
- bestehende Notification-Shell und Read-State-Route,
- UI, CSS und Navigation.

## Testmatrix

| Bereich | Abdeckung |
| --- | --- |
| Migration | V0006 Up, Wiederholung, Legacy-Erhalt, Down und fail-closed Down mit typisierten Daten |
| Katalog | exakt sieben Typen; Problemtypen abgewiesen |
| Requests | manuell und Smart eindeutig typisiert; korrekter Empfänger und Request-Ziel |
| Annahme | ursprünglicher Absender; Lifecycle-Ziel; Retry genau einmal |
| Versand | beide Seiten getrennt; Gegenempfänger; eindeutiges Event; Retry |
| Empfang | beide Seiten getrennt; Gegenempfänger; vorhandenes Receipt-Event; Retry |
| Fristen | Versand und Empfang lazy genau einmal; keine Smart-48-h-Notification |
| Einstiegspunkte | Tradeübersicht, Album-Tradeübersicht, Deal und Notifications |
| Parallelität | konkurrierende Erzeugung ergibt durch Unique Key genau eine Zeile |
| Sicherheit | Zielauflösung nur für Empfänger und berechtigten Tradebeteiligten |
| Legacy | weiterhin lesbar, Typ `legacy`, kein Ziel- oder Text-Backfill |
| Seiteneffekte | keine Inventory- oder Tradezustandsmutation durch Projektion |
| Regression | vollständige S01–S23-Suite |

## Testbefehle und Ergebnisse

Gezielter ausführbarer Modulbefehl:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s23_typed_notifications -v
```

Ergebnis: **13 Tests, 13 erfolgreich**.

Der Ausdruck `python3 -m unittest tests.test_s23_* -v` ist kein ausführbarer
`unittest`-Modulname, weil der Stern innerhalb eines Modulnamens nicht durch
die Shell expandiert wird. Deshalb wurde der konkrete Modulname verwendet.

Vollständiges Gate:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

- finaler Lauf 1: **370 Tests, 370 erfolgreich**,
- finaler Lauf 2: **370 Tests, 370 erfolgreich**.

## Migration und Release Readiness

- lokale Anwendungsdatenbank read-only geprüft: **V0005**,
- lokale Anwendungsdatenbank migriert: **nein**,
- V0006 ausschließlich auf einer temporären Kopie geprüft,
- erster Up-Lauf: Änderung `(6,)`, danach **V0006**,
- wiederholter Up-Lauf: keine Änderung `()`, weiterhin **V0006**,
- Down-Lauf ohne typisierte Daten: Änderung `(6,)`, danach **V0005**,
- Down-Lauf mit typisierten Daten: erwartungsgemäß fail-closed,
- `PRAGMA integrity_check` auf lokaler Datenbank sowie temporärer Up-/Down-Kopie: **ok**,
- `PRAGMA foreign_key_check`: **keine Befunde**,
- SHA-256 der lokalen Datenbank vor/nach der isolierten Prüfung identisch,
- kanonische S00-Fixture ausschließlich als Quelle temporärer Tests verwendet
  und durch Test-Hashkontrollen unverändert,
- ausschließlich temporäre Testdaten verwendet,
- keine lokale oder produktive Migration ausgeführt.

## Bekannte Grenzen und offene Punkte für S24

- S23 speichert und autorisiert das kanonische Ziel, macht Notifications aber
  noch nicht klickbar.
- Es gibt bewusst keinen `origin=notifications`, Rückwegkontext oder neuen
  Navigation-Stack.
- Notification-Historie, Badge-Redesign, Mark-as-read-UX und UI-Redesign sind
  nicht Bestandteil von S23.
- Fristen werden ausschließlich lazy an den freigegebenen Einstiegspunkten
  erzeugt; es gibt keinen Hintergrundprozess.
- Bestehende Legacy-Zeilen bleiben absichtlich ohne semantisch rekonstruiertes
  Ziel.

## Scope-Bestätigung

- ausschließlich S23 umgesetzt,
- S24 nicht begonnen,
- keine Änderung an S17–S22-Fachlogik,
- keine Änderung an Inventory, Snapshot, Coverage, TopMatch, Smart Requests,
  Reservierung, Versand, Empfang oder Problemen,
- keine Notification-UI, kein Klickverhalten und keine Historienseite,
- keine Migration der lokalen Anwendungs- oder Produktdatenbank,
- kein Commit,
- kein Push.
