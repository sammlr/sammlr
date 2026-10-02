# S22 – Smart-Trade-Anfragen und transparente Paketänderungen

Stand: 2026-08-07

## Fachliches Ziel

Die konfliktfreien S21-Pakete werden als nicht editierbare Smart-Pakete
angezeigt und können über die bestehende TradeRequest-Architektur angefragt
werden. Smart-Anfragen bleiben von manuellen Anfragen fachlich unterscheidbar.
Vor jeder zustandsrelevanten Aktion wird das unveränderte Paket gegen die
zentrale Availability gelesen. Eine heimliche Anpassung findet niemals statt.

## Verbindliche Product-Owner-Regeln

- global höchstens drei gleichzeitig offene Smart-Anfragen eines Absenders;
  manuelle Anfragen zählen nicht,
- Ablauf exakt 48 Stunden nach `created_at`, Status danach `expired`, keine
  Löschung,
- Ablaufprüfung ausschließlich beim Öffnen, Annehmen und Ablehnen,
- Availability-Recheck beim Absenden, Öffnen und Annehmen,
- ein verändertes Paket wird weder verkleinert noch automatisch angepasst,
- ist noch ein bilateraler Teil ausführbar, bleibt die Anfrage offen, aber die
  Annahme ist gesperrt; angeboten werden Neuberechnung und Abbrechen,
- ist kein bilaterales Paket mehr ausführbar, wird die Smart-Anfrage
  `obsolete`,
- ein ausgeschlossener Partner gilt nur für die aktuelle Neuberechnung und
  wird nicht gespeichert,
- keine Migration und keine neue Datenbankstruktur.

## Architektur

### Neue Komponente

`SmartTradeRequestService` kapselt ausschließlich die S22-Regeln:

- Smart-Kennzeichnung,
- globales Offen-Limit,
- 48-Stunden-Ablauf,
- exakten Availability-Recheck,
- Erzeugung einer Smart-Anfrage im bestehenden `trade_requests`-Modell,
- Übergang nach `obsolete`, falls keine bilaterale Ausführung mehr möglich
  ist.

Der Service verwendet `InventoryReadService.snapshot(...)` und schreibt keine
Inventory-Daten. Er ruft weder Shipping-, Receipt- noch Problem-Services auf.

### Migrationsfreie Smart-Kennzeichnung

Solange eine Anfrage im Legacy-Request-Modell geführt wird, kennzeichnet der
exakte reservierte Wert `from_confirmed = -22` die Smart-Herkunft. Die Werte
`0` und `1` behalten ihre bisherige Bedeutung für manuelle beziehungsweise
Legacy-Anfragen. Die Erkennung prüft ausschließlich auf `-22`, nicht auf
allgemeine Wahrheit/Falschheit.

Der bestehende `TradeReservationService` setzt bei der Annahme die beiden
Legacy-Bestätigungsfelder wie bisher auf `0`. Die Smart-Herkunft wird danach
über ein rein informatives `smart_request_accepted`-Event im bereits
vorhandenen Lifecycle festgehalten. Reservierungen, Positionen und
Lifecycle-Zustände werden weiterhin ausschließlich durch den bestehenden
S14-Service erzeugt.

Diese Abbildung benötigt weder Spalte noch Tabelle noch Migration.

### Neue DTOs

Immutable DTOs beschreiben:

- Ergebniscode einer Smart-Aktion,
- gespeichertes Paket und Ablaufzeit,
- exakten Recheck mit fehlenden Mengen je Richtung,
- Erzeugungsergebnis mit optionaler TradeRequest-ID.

Lose, je Route unterschiedlich geformte Dictionaries werden für die neue
Fachlogik vermieden.

## Datenfluss

### Vorschlag und Absenden

1. Route liest Albumkatalog und zulässige Partner.
2. Optionaler Partnerausschluss wird nur im aktuellen Request angewendet.
3. Unveränderter `TopMatchOptimizationService` erzeugt S21-Pakete.
4. UI zeigt Paket, Profilverweis und Mengen ausschließlich read-only.
5. POST berechnet dasselbe Ergebnis erneut und vergleicht `result_id` und
   Partnerpaket.
6. `SmartTradeRequestService` prüft in einer Transaktion das globale Limit und
   die exakte Availability beider Richtungen.
7. Nur ein weiterhin vollständig verfügbares Paket wird als offene
   TradeRequest gespeichert.

### Öffnen

1. Bestehende Objektberechtigung prüft die Teilnahme am Trade.
2. Nur bei Smart-Anfragen wird Ablauf geprüft.
3. Nur bei weiterhin offenen Smart-Anfragen wird das unveränderte Paket
   erneut gelesen.
4. Voll verfügbar: normale Darstellung und vorhandene Aktionen.
5. Teilweise ausführbar: Status bleibt `open`, Annahme gesperrt, keine
   Paketänderung.
6. Nicht mehr bilateral ausführbar: Status `obsolete`.

### Annehmen

1. Nur der bisher berechtigte Empfänger darf annehmen.
2. Ablauf und exakter Availability-Recheck laufen vor dem bestehenden
   Annahmeservice.
3. Nur `READY` delegiert unverändert an `TradeReservationService.accept(...)`.
4. Reservierung und Lifecycle bleiben vollständig beim bestehenden Service.
5. Ein informatives Event erhält danach die Smart-Herkunft.

### Ablehnen

Beim Ablehnen wird ausschließlich der Ablauf geprüft. Eine noch offene,
nicht abgelaufene Smart-Anfrage nutzt den vorhandenen Ablehnungspfad. Ist sie
bereits abgelaufen, bleibt `expired` erhalten.

## Recheck-Regel

Für jede gespeicherte Position wird die angeforderte Menge mit
`effective_available` des jeweils abgebenden Nutzers verglichen:

- `give_codes`: Bestand des Absenders,
- `get_codes`: Bestand des Empfängers.

`full_available` gilt nur, wenn jede ursprüngliche Position in voller Menge
ausführbar ist. `any_executable` gilt nur, wenn in beiden Richtungen noch
mindestens eine Einheit verfügbar ist. Kein Recheck verändert die
gespeicherten Code-Listen.

## Status- und Regelmatrix

| Fall | Smart-Anfrage | Manuelle Anfrage |
| --- | --- | --- |
| Paket editierbar | nein | bestehendes Verhalten |
| Offen-Limit | global 3 | keines durch S22 |
| Ablauf | 48 h bei Öffnen/Annehmen/Ablehnen | unverändert |
| Recheck | Absenden/Öffnen/Annehmen | bestehendes Verhalten |
| Paket teilweise verändert | offen, Annahme gesperrt | unverändert |
| Paket nicht mehr ausführbar | `obsolete` | unverändert |
| Annahme | bestehender Reservierungsservice | bestehender Reservierungsservice |
| Regel `geben >= bekommen` | S21-Paket unverändert | unverändert geschützt |

## Seiteneffekte

Erlaubte S22-Schreibvorgänge sind ausschließlich:

- Erzeugen einer offenen Smart-TradeRequest,
- Statuswechsel einer Smart-Anfrage nach `expired` oder `obsolete`,
- bestehender Statuswechsel nach `accepted` beziehungsweise `declined`,
- bestehende Notification-Hooks bei Anfrage, Annahme und Ablehnung,
- informatives Lifecycle-Event nach erfolgreicher Smart-Annahme.

Keine Inventory-Buchung, Reservierung außerhalb des bestehenden
Annahmeservices, Migration, automatische Paketänderung oder Hintergrundarbeit
wird eingeführt.

## Unveränderte Komponenten

- `TopMatchOptimizationService` (S21),
- `TradeCoverageService` (S20),
- Shared Availability Snapshot (S19),
- `TradeReservationService` und Inventory-Services,
- Shipping-, Receipt- und Problem-Services,
- manueller Dealwizard und seine Validierung.

## Determinismus, Komplexität und Risiken

Die Vorschlagsberechnung übernimmt die deterministische S21-Reihenfolge. Der
Recheck ist linear in der Zahl der Paketpositionen; das globale Limit ist eine
einzelne Zählabfrage. Ein `BEGIN IMMEDIATE` schützt Limitprüfung und Erzeugung
vor parallelem Überschreiten.

Bekannte Risiken werden durch Tests abgesichert:

- Race beim dritten offenen Smart-Request,
- Grenzzeitpunkt exakt nach 48 Stunden,
- Verwechslung von Smart- und manuellen Requests,
- veraltete S21-Ergebnis-ID zwischen Anzeige und POST,
- Paketverlust in nur einer Richtung,
- unbeabsichtigte Inventory-Mutation beim Recheck,
- Verlust der Smart-Kennzeichnung nach Reservierung.

## Testanforderungen

Happy Path bis zur bestehenden Reservierung, Limit inklusive manueller
Anfragen, Ablauf auf allen drei erlaubten Triggern, unveränderte und veränderte
Pakete, `obsolete`, Ablehnung, flüchtiger Partnerausschluss, Objektberechtigung,
Nichteditierbarkeit, Retry/Parallelität sowie vollständige Regression S17–S21.

## Nicht enthalten

Keine Bewertungssortierung, Strategieauswahl, Cross-Album-Optimierung,
Hintergrundjobs, Migration, neue Notification-Typisierung, automatische
Paketverkleinerung oder Arbeit an S23.
