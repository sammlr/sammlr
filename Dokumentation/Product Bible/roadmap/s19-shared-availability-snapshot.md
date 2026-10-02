# S19 – Shared Availability Snapshot

Stand: 2026-08-05
Status: umgesetzt

## Ziel und Grenze

S19 stellt für jede Betrachtungseinheit `(Nutzer, Album, Stickercode)` einen zentralen, unveränderlichen Availability Snapshot bereit. Stickerwall, Albumfortschritt, aktive Tradeansichten, Tradevorschläge und der bestehende bilaterale Matcher lesen damit denselben Zustand aus dem `InventoryReadService`.

Der Snapshot ist ausschließlich read-only. Er trifft keine Tradeentscheidung, reserviert und bucht nichts und verändert weder Lifecycle noch Status. Marktdeckung, Ranking, Empfehlungen, Top Matches, Caching und neue UI gehören nicht zu S19.

## Architektur

Der bestehende `InventoryReadService` in `App/services/inventory.py` bleibt die einzige Bestandslesequelle. S19 ergänzt dort:

- `StickerAvailabilitySnapshotDTO` für genau einen Stickercode,
- `AlbumAvailabilitySnapshotDTO` für einen Nutzer und ein Album,
- `InventoryReadService.snapshot(...)` als öffentliche Snapshot-API,
- `AlbumInventoryDTO.availability_snapshot_for(...)` für aktive kompatible Leser,
- eine gemeinsame interne Transitprojektion für eingehende und ausgehende Sicht.

Alle DTOs sind eingefrorene Dataclasses. Das Code-Mapping ist eine `MappingProxyType`-Sicht. Der Snapshot besitzt die Version `S19-v1` und einen gemeinsamen `captured_at`-Zeitpunkt je Albumabfrage. Es gibt keinen Cache und keine persistierte Snapshot-Tabelle.

## Snapshot-Vertrag

| Feld | Quelle/Formel | Bedeutung |
| --- | --- | --- |
| `sticker_code` | vorhandener Katalog-/Inventory-/Lifecycle-Code | fachliche Stickeridentität |
| `physical` | bestehendes `stickers.quantity` | aktuell physisch beim Nutzer |
| `assigned` | bestehende S08/S11-Projektion `min(physical, 1)` | dem heutigen Einzelalbum zugeordnet |
| `reserved` | Summe aktiver `trade_reservations` | verbindlich gebundene physische Überschussmenge |
| `incoming_transit` | offene versendete Positionen an den Nutzer | unterwegs, noch nicht physisch gebucht |
| `outgoing_transit` | dieselben offenen Positionen aus Sicht des Absenders | versendet und nicht mehr physisch beim Absender |
| `available` | `max(physical - assigned - reserved, 0)` | heutiger freier Tauschbestand |
| `missing` | `physical == 0` | physisch weiterhin fehlend, Transit ändert dies nicht |
| `duplicates` | `max(physical - assigned, 0)` | physischer Überschuss einschließlich gegebenenfalls reservierter Kopien |
| `effective_available` | in S19 exakt `available` | gemeinsame match- und vorschlagsfähige Menge |

`effective_available` führt keine neue Regel ein. Ausgehender Transit wurde beim Versand bereits aus `physical` entfernt, eingehender Transit ist noch nicht physisch, und aktive Reservierungen sind bereits in `available` abgezogen. Eine weitere Subtraktion wäre Doppelzählung.

## Transitprojektion

Ein gemeinsamer parametrisierter Lesepfad berechnet beide Perspektiven aus denselben vorhandenen Tabellen:

```text
offener Transit = trade_position.quantity
                - initial_received_quantity
                - resolution_received_quantity
```

Die Position zählt nur, wenn ihre Absenderseite versendet hat und die Empfängerseite noch nicht vollständig bestätigt ist. Ein Problembericht lässt ausschließlich die offene Restmenge im Transit. Nach vollständigem Empfang oder Problemauflösung verschwinden eingehende und ausgehende Projektion gemeinsam.

Es gilt weiterhin:

```text
outgoing_transit(Sender, Position)
= incoming_transit(Empfänger, Position)
```

## Konsolidierte Leser

Auf `availability_snapshot_for(...)` umgestellt wurden ausschließlich aktive read-only Verwendungen:

- Stickerwall und Stickerdetail für `incoming_transit`,
- Albumfortschritt,
- tauschbare Lücken und Albumvorschau,
- Album- und globale Tradeübersichten,
- Dealzusammenstellung und Request-Validierung,
- bilaterales Availability-Matching.

Der frühere `availability(...)`-Adapter bleibt ausschließlich zur Rückwärtskompatibilität und liefert das bereits im Snapshot enthaltene `AvailabilityDTO`; er berechnet nicht erneut. `trade_candidates(...)` bleibt als inaktiver Golden-Master-Vergleich für Resultate ohne Bindungen erhalten. Gespeicherte `duplicates`-Werte für Bestands-, Trophy- oder Legacy-Ausgaben sind keine zweite Availability-Berechnung und wurden nicht verändert.

## Konsistenz und Invarianten

- Gleiche persistierte Eingabe erzeugt dieselben Mengen und Statusfelder.
- `physical = assigned + reserved + available` bleibt erhalten.
- `effective_available` ist nie negativ und nie größer als `physical`.
- `incoming_transit` und `outgoing_transit` verändern weder Fortschritt noch Inventory.
- Snapshot-Aufrufe führen kein `INSERT`, `UPDATE`, `DELETE`, `COMMIT` oder `ROLLBACK` aus.
- Alle bestehenden Tradeergebnisse bleiben ohne Bindungen Golden-Master-identisch.

## Migration

S19 benötigt keine Migration und keine Schemaänderung. Sämtliche Felder werden aus dem vorhandenen V0005-Modell gelesen. Der lokale Stand wurde read-only als V0005 geprüft; es wurde kein Migration Runner mit einer Änderungsrichtung ausgeführt.

## Tests

Gezielt:

```bash
python3 -m unittest tests.test_s19_shared_availability_snapshot -v
```

Vollständiges Gate:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Die Tests verwenden ausschließlich temporäre Kopien der kanonischen S00-Fixture und migrieren nur diese Kopien bis V0005. Abgedeckt sind Vertrag und DTOs, Reservierungen, beide Transitrichtungen, fehlend/vorhanden/doppelt/effektiv verfügbar, Versand, Empfang, Problem, Auflösung, parallele Trades, Mutationsfreiheit, Stickerwall, Tradeansichten und Golden Master.

## Nicht enthalten und S20-Grenze

S20 „Markt- und persönliche Trade-Abdeckung“ darf auf dem Snapshot aufbauen. S19 berechnet jedoch keine Marktabdeckung, persönliche Abdeckung, Rankings oder Optimierungen. S21 wurde ebenfalls nicht begonnen.
