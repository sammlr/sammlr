# S14 – Annahme erzeugt verbindliche Reservierungen

Stand: 2026-08-02

## Zweck und Sprintgrenze

S14 bindet die ausgehenden Stickerpositionen beider Seiten erst bei der
Annahme einer bestehenden Tradeanfrage. Eine bloße Anfrage reserviert weiterhin
nichts. Annahme, Recheck, Lifecycle-Zuordnung, Positionen, Reservierungen,
Legacy-Status und die bestehende Annahme-Notification bilden eine atomare
Transaktion.

Nicht enthalten sind Versand, Empfang, Transit, Teilempfang, Problemprozess,
Tracking, Chat, Bewertung, dynamische Paketanpassung, Smart Trader 2.0 oder neue
Notificationtypen.

## Versionierte Migration V0002

S14 ergänzt ausschließlich über den S13-Migrationsmechanismus:

```text
0002_trade_reservations
```

Dateien:

- `App/Database/migrations/0002_trade_reservations.up.sql`
- `App/Database/migrations/0002_trade_reservations.down.sql`

Es gibt keine Startup-Migration und kein `ALTER TABLE` in `App/webapp.py`.
Produktivdatenbank und kanonische Fixture werden nicht automatisch migriert.
Die Anwendung verwendet die Reservierungslogik nur, wenn V0001 und V0002 auf
der bewusst gewählten Datenbank installiert sind. Eine noch nicht migrierte
Datenbank behält für die Bestandsregressionen den bisherigen Legacy-Annahmepfad.

## Reservierungsmodell

### `trade_reservations`

| Feld | Regel |
| --- | --- |
| `id` | technische Primär-ID |
| `trade_id` | Pflicht-FK auf `trades`; kaskadierendes Löschen |
| `trade_position_id` | Pflicht-FK auf `trade_positions`; eindeutig |
| `user_id` | Nutzer, der die Kopie abgibt |
| `album_id` | Album-/Albumtyp gemäß bestehendem Modell |
| `sticker_code` | bestehender Stickercode |
| `quantity` | positive reservierte Menge (`CHECK quantity > 0`) |
| `state` | ausschließlich `active` oder `released` |
| `created_at` | Erstellzeitpunkt |
| `released_at` | bei aktiver Reservierung zwingend leer, bei Freigabe gesetzt |
| `release_reason` | bei aktiver Reservierung zwingend leer, bei Freigabe gesetzt |

Eine Position besitzt höchstens eine Reservierungszeile. Die reservierte Menge
wird aggregiert gespeichert; doppelte Codes im bestehenden JSON-Paket ergeben
eine Position mit entsprechend höherer positiver Menge.

Indizes unterstützen aktive Bestandsabfragen nach Nutzer/Album/Code und die
Freigabe aller Reservierungen eines Lifecycle-Trades.

## Verbindung der Modelle

```text
trade_requests.id
    │
    └── trades.legacy_trade_request_id (UNIQUE)
            │
            ├── trade_positions.trade_id
            │       └── Richtung, Album, Code, Menge
            │
            └── trade_reservations.trade_id
                    └── trade_position_id (UNIQUE), Abgeber, Menge, Zustand
```

`trade_requests` bleibt für den heutigen sichtbaren Flow und die Historie
lesbar. Es erfolgt kein allgemeiner Backfill historischer Anfragen. Der
Lifecycle-Trade wird nur bei der ersten erfolgreichen S14-Annahme eindeutig
erzeugt oder bei konsistenter Zuordnung wiederverwendet.

## Positionsbildung

Für ein Legacy-Paket gelten unverändert:

- `give_codes`: Anfrageersteller → Empfänger,
- `get_codes`: Empfänger → Anfrageersteller.

Codes werden pro Richtung gezählt. Für jede Kombination aus Trade, Abgeber,
Empfänger, Album und Code entsteht genau eine `trade_positions`-Zeile. Für jede
dieser Zeilen entsteht genau eine aktive Reservierung.

Leere, strukturell ungültige oder nicht als String vorliegende Codes werden als
ungültiger Tradezustand behandelt. Das Paket wird nicht dynamisch angepasst.

## Transaktionsgrenze

`TradeReservationService.accept()` besitzt die vollständige Annahmetransaktion:

```text
BEGIN IMMEDIATE
  1. Trade laden
  2. Empfängerberechtigung und status=open prüfen
  3. Positionen aus dem unveränderten JSON-Paket bestimmen
  4. Lifecycle-Trade erzeugen oder konsistent wiederverwenden
  5. Availability aller Positionen neu lesen und vollständig prüfen
  6. alle Positionen speichern
  7. alle Reservierungen speichern
  8. Legacy-Status atomar auf accepted setzen
  9. bestehende Annahme-Notification erzeugen
COMMIT
```

Jeder fachliche Konflikt oder technische Fehler führt zu `ROLLBACK`. Damit
bleiben Lifecycle-Trade, Positionen, Reservierungen, Legacy-Status und
Notification gemeinsam unverändert. Bestandsmengen werden bei Annahme nie
geschrieben.

## Availability-Recheck

Der Recheck verwendet unmittelbar vor dem Schreiben den zentralen
`InventoryReadService` auf derselben Verbindung und innerhalb derselben
`BEGIN IMMEDIATE`-Transaktion.

Ab V0002 gilt für die Read-Projektion:

```text
physical = bestehende quantity
assigned = min(physical, 1)
reserved = SUM(aktive Reservierungen für Nutzer/Album/Code)
available = max(physical - assigned - reserved, 0)
reservable = available
```

Alle Positionen werden geprüft, bevor die erste Reservierung geschrieben wird.
Eine Teilreservierung ist daher ausgeschlossen. Physical, `stickers.quantity`,
`stickers.duplicates`, assigned sowie gesammelte Sticker und Fortschrittsprozent
bleiben bei Annahme unverändert.

Matching und bestehende Trade-Kandidaten lesen dieselbe Availability-Projektion
und bieten nur die verbleibende freie Menge an.

## Inventory Guard

Der `InventoryWriteService` verwendet auf migrierten Datenbanken aktive
Reservierungen als reale S14-Bindungsquelle für den S12-Guard. Solange eine
Reservierung aktiv ist, darf eine manuelle Mengenänderung den notwendigen
physischen Mindestbestand aus zugeordneter Basiskopie und reservierten
Überschusskopien nicht unterschreiten.

Ohne aktive Reservierung liefert die Quelle weiterhin Mindestmenge `0`; das
bisherige manuelle Verhalten bleibt dann unverändert.

## Idempotenz

Eine wiederholte Annahme derselben bereits angenommenen Legacy-Anfrage liefert
`ALREADY_ACCEPTED` und führt keine Mutation aus:

- kein zweiter Lifecycle-Trade,
- keine zweite Position,
- keine zweite Reservierung,
- keine zweite Annahme-Notification,
- keine Bestandsänderung.

Ein bereits vor S14 angenommener Legacy-Trade ohne Lifecycle-Zuordnung wird
nicht nachträglich migriert oder reserviert. Damit findet kein unkontrollierter
Backfill statt.

## Konkurrenzregel

`BEGIN IMMEDIATE` serialisiert konkurrierende Annahmen in SQLite vor dem
Availability-Recheck. Nach dem Commit der ersten Annahme sieht die zweite
Transaktion deren aktive Reservierung. Benötigen beide dieselbe letzte freie
Kopie, kann genau eine Annahme erfolgreich sein; die andere liefert
`INSUFFICIENT_AVAILABLE` und bleibt vollständig ohne Teilwirkung.

## Freigaberegel

S14 nutzt ausschließlich die bereits vorhandenen zulässigen Enden:

- `accepted → failed`: alle aktiven Reservierungen werden mit Grund `failed`
  genau einmal freigegeben; der bestehende Bestand bleibt unverändert.
- `accepted → completed`: alle aktiven Reservierungen werden mit Grund
  `completed` genau einmal freigegeben, bevor der bestehende einmalige
  Abschlussalgorithmus die Bestände bucht.

Die Freigabe aktualisiert nur Zeilen mit `state='active'`. Wiederholungen ändern
keine bereits freigegebene Zeile. Eine offene Ablehnung benötigt keine Freigabe,
weil eine Anfrage vor Annahme keine Reservierungen besitzt. Neue Abbruch-,
Problem-, Versand- oder Empfangszustände wurden nicht ergänzt.

## Stabile Ergebniszustände

| Code | Bedeutung |
| --- | --- |
| `ACCEPTED` | vollständig reserviert und angenommen |
| `ALREADY_ACCEPTED` | idempotente Wiederholung ohne Mutation |
| `INSUFFICIENT_AVAILABLE` | mindestens eine Position ist nicht mehr vollständig frei |
| `INVALID_TRADE_STATE` | unbekannter, nicht offener oder strukturell ungültiger Trade |
| `UNAUTHORIZED` | Akteur ist nicht der Empfänger |
| `TRANSACTION_ERROR` | technischer Fehler; vollständiger Rollback |

Die Codes sind UI-neutrale String-Enums in einem unveränderlichen DTO. Die
bestehende Route bildet sie lediglich auf schlichte Redirect-Meldungen ab.

## Migration und Backout

Vorwärts auf einer Testkopie:

```text
python3 -m App.Database.migration_runner up --database /absoluter/pfad/testkopie.db
```

Backout nur vor erster Nutzung von V0002:

```text
python3 -m App.Database.migration_runner down --database /absoluter/pfad/testkopie.db --target 1
```

Die Down-Migration ist fail-closed: Sobald irgendeine Reservierungszeile
existiert, bricht sie per Constraint ab und erhält Tabelle, Ledger und Daten.
Nach produktiver Nutzung ist deshalb vor einem Backout ein ausdrücklich
versionierter Export-/Recovery-Plan erforderlich. Leere V0002-Schemata können
verlustfrei auf V0001 zurückgeführt werden.

## Testvertrag

S14 prüft unter anderem:

- Anfrage ohne Reservierung,
- beidseitige vollständige Reservierung,
- Availability-/Matching-Projektion,
- unveränderte physische Mengen und Fortschrittswerte,
- vollständigen Konflikt-Rollback,
- Idempotenz und Nebenwirkungs-Deduplizierung,
- echte Konkurrenz zweier SQLite-Verbindungen,
- Objektberechtigung und ungültige Zustände,
- Guard gegen manuelle Unterschreitung,
- Freigabe bei `failed` und `completed`,
- bestehenden Abschluss mit genau einmaliger Bestandsbuchung,
- Migration, No-op, Backout und fail-closed Backout,
- Legacy-`completed`-Trade und JSON-Pakete,
- Schutz der kanonischen Datenbanken.

## Bewusst nicht umgesetzt: S15+

- Versandstatus oder Versandzeitpunkte,
- eingehender oder ausgehender Transit,
- Empfang und Teilempfang,
- Tracking, Labels oder Versicherung,
- Problemprozess und Konfliktentscheidung,
- Chat oder Bewertung,
- dynamische Paketänderung und erneute Zustimmung,
- neue Home-, Notification- oder Designoberflächen.
