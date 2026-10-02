# S17 – Problemfälle und Teilempfang

Stand: 2026-08-03

## Zweck und Grenze

S17 erweitert den vollständigen Empfang aus S16 um eine dokumentierte
physische Bestandswahrheit. Nur korrekt erhaltene erwartete Positionen werden
gebucht. Fehlende, falsche, beschädigte oder verlorene Mengen bleiben
ungebucht, im Transit offen und historisch sichtbar. Ein offener Problemfall
verhindert den erfolgreichen Abschluss.

Der direkte S16-Standardweg „Alles vollständig erhalten“ bleibt bestehen. S17
entscheidet weder Schuld noch Ersatz, Rücksendung, Erstattung oder Sanktion.
Chat, Bilder, Bewertung, Fristen, Überfälligkeit, Supportautomation,
Versicherung, Tracking und Versanddienstleister sind nicht enthalten.

## Problemfallmatrix

| Physische Lage | Korrekt erhalten | Problemtyp | Bestandsbuchung | Trade |
| --- | ---: | --- | --- | --- |
| vollständig korrekt | erwartet | keiner | gesamte erwartete Menge | normaler S16-Empfang |
| teilweise korrekt | 1 bis erwartet − 1 | `missing` | nur korrekte Teilmenge | `problem_open` |
| erwartete Position falsch erfüllt | 0 bis erwartet − 1 | `wrong_sticker` | nur korrekte erwartete Teilmenge | `problem_open` |
| erwartete Position beschädigt | 0 bis erwartet − 1 | `damaged` | nur korrekte erwartete Teilmenge | `problem_open` |
| ganze Sendung verloren | 0 für alle Positionen | `shipment_lost` | keine | `problem_open` |

Es sind ausschließlich `missing`, `wrong_sticker`, `damaged` und
`shipment_lost` zulässig. Ein falscher mitgesendeter Sticker erhält keinen frei
eingebbaren Ersatzcode und wird nicht automatisch eingebucht. Ein beschädigter
Sticker gilt nicht als korrekt erhalten.

## Mengen- und Buchungsvertrag

Für jede an den angemeldeten Empfänger gerichtete Lifecycle-Position muss
genau eine Eingabe vorliegen:

```text
0 <= correct_received <= expected
open = expected - initial_received - resolution_received
```

- Bei `correct_received == expected` ist kein Problemtyp erlaubt.
- Bei `correct_received < expected` ist genau ein erlaubter Problemtyp nötig.
- `shipment_lost` gilt nur, wenn jede Position Menge `0` und diesen Typ trägt.
- Positionen anderer Seiten, fehlende Positionen, Duplikate, negative,
  nicht-ganzzahlige oder überhöhte Mengen werden vollständig abgewiesen.
- Buchungen laufen ausschließlich über `InventoryWriteService.add()`.
- Die bestehende Availability- und Guard-Architektur bleibt maßgeblich.

Problemaufnahme und Bestand laufen gemeinsam unter `BEGIN IMMEDIATE`:
Berechtigung, Versand, Zustand, vollständige Eingabe, Bestandsbuchung,
Problemzeilen, Event und Lifecycle werden gemeinsam committed oder vollständig
zurückgerollt. Trophy und Abschlussnotification werden bei einem offenen
Problem nicht ausgelöst.

## Transitauflösung

Die zentrale Inventory-Leseprojektion zieht pro Tradeposition bereits korrekt
gebuchte Mengen vom eingehenden Transit ab:

```text
incoming_transit = expected
                   - initial_received_quantity
                   - resolution_received_quantity
```

Bei 29 von 30 werden deshalb 29 physisch gebucht und genau 1 bleibt unterwegs.
Falsche, beschädigte, fehlende oder verlorene Restmengen werden nicht als
Physical gezählt. Nach vollständiger Auflösung ist der Resttransit 0.

## Versioniertes Modell V0005

`trade_receipt_reports` speichert je Trade und Empfänger genau einen Bericht:

- Lifecycle-Trade und Empfänger-ID,
- Empfängerseite `requester` oder `partner`,
- Zustand `open` oder `resolved`,
- Kennzeichen für vollständig verlorene Sendung,
- Erstellungs- und Auflösungszeitpunkt.

`trade_receipt_report_positions` speichert die unveränderliche Wahrheit je
erwarteter Position:

- Tradeposition,
- erwartete Menge,
- anfänglich korrekt erhaltene Menge,
- später korrekt erhaltene Auflösungsmenge,
- Problemtyp,
- Zustand `fulfilled`, `open` oder `resolved`,
- Erstellungs- und Auflösungszeitpunkt.

Constraints verhindern negative, überhöhte oder inkonsistente Mengen und
unzulässige Typ-/Zustandskombinationen. V0005 verändert keine Legacy-Zeilen.
Der Backout nach V0004 ist bei leerem S17-Modell möglich. Sobald ein Bericht
existiert, bricht die Down-Migration fail-closed ab, damit Historie und
Bestandsursprung nicht verloren gehen.

## Lifecycle und erlaubte Übergänge

```text
partially_shipped / shipped / partially_received
  ├─ alles korrekt → S16 receipt → partially_received oder completed
  └─ Teil-/Problemempfang → problem_open

problem_open
  ├─ andere Seite versendet/empfängt → problem_open bleibt erhalten
  └─ erwartete Restmenge trifft korrekt ein
       → Bericht resolved
       → Empfangsseite vollständig
       → partially_received oder completed
```

`completed` ist ausschließlich erlaubt, wenn beide S16-Empfangsseiten
bestätigt und kein Bericht mehr offen ist. Der Legacy-Trade bleibt während
eines Problems `accepted`.

## Minimale spätere Auflösung

Die Auflösung bucht ausschließlich
`expected - initial_received - resolution_received` der offenen erwarteten
Positionen. Sie verändert keine vorherige Buchung, keinen Problemtyp und
keinen ursprünglichen Zeitpunkt. Bericht und Positionen werden als aufgelöst
markiert und bleiben in der Historie. Ein Retry ist ein No-op. Es gibt keine
Verhandlung, Ersatzposition oder dynamische Paketänderung.

## Idempotenz und stabile Ergebniszustände

Eine identische Wiederholung erkennt denselben Bericht und liefert
`ALREADY_IDENTICAL`. Sie bucht nicht erneut, dupliziert keinen Bericht und
überschreibt keinen Zeitpunkt. Eine abweichende Wiederholung liefert
`CONFLICTING_REPORT` und bewahrt die gespeicherte Wahrheit.

Stabile UI-neutrale Codes:

- `FULLY_RECEIVED`
- `PARTIAL_RECEIPT_RECORDED`
- `ALREADY_IDENTICAL`
- `PROBLEM_RESOLVED`
- `INVALID_QUANTITY`
- `CONFLICTING_REPORT`
- `NOT_SHIPPED`
- `INVALID_TRADE_STATE`
- `UNAUTHORIZED`
- `TRANSACTION_ERROR`

## Berechtigungen

Der Empfänger wird aus Session-Nutzer und Lifecycle-Positionen bestimmt. Nur
er darf seinen Eingang melden oder seinen Bericht auflösen. Der Absender kann
nicht für ihn handeln; Unbeteiligte werden abgewiesen. Der Versand der
Gegenseite und ein empfangsfähiger Lifecycle bleiben zwingend. Es gibt keine
frei übergebene Empfänger-ID oder freie Tradeposition.

## Einfache Bedienoberfläche

Die Dealansicht zeigt für einen empfangsberechtigten Nutzer weiterhin:

- „Empfang bestätigen – Alles vollständig erhalten“
- „Problem melden / Lieferung unvollständig“

Das schlichte Problemformular zeigt je erwarteter Position „Erwartet“ und ein
begrenztes Zahlenfeld „Korrekt erhalten“, den erlaubten Problemtyp sowie die
Hinweise, dass nur korrekte Mengen gebucht werden und Sammlr keine Schuldfrage
entscheidet. Ein offener Bericht erscheint in Status und Historie und bietet
nur „Offene Restmenge als korrekt eingetroffen bestätigen“.

## Tests

S17-spezifisch:

```bash
python3 -m unittest tests.test_s17_trade_problems_partial_receipt -v
```

Vollständiges Gate:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Die Tests migrieren ausschließlich temporäre Datenbanken oder temporäre
Fixture-Kopien. Sie decken den vollständigen Standardempfang, 29/30,
Transitanteil, alle vier Problemtypen, Validierung, spätere Auflösung,
Abschlussinvariante, Idempotenz, Autorisierung, atomaren Rollback, Side Effects,
V0005/Backout und Legacy-Lesbarkeit ab.

## Offene Supportgrenzen und S18+

Bewusst nicht umgesetzt sind Schuldentscheidung, Beweisprüfung, Fotos,
Erstattung, Rücksendung, Ersatzlieferung, Sanktion, Schiedsgericht,
Supportautomation, Versicherung, Chat, Bewertung, Fristen, Überfälligkeit,
Tracking, Dienstleister, Home-Aufgaben, Notification-Historie und Design Patch.
Insbesondere wurde keine S18-Frist- oder Ereignisprotokoll-Erweiterung
begonnen; S17 schreibt nur seine zwingend notwendigen bestehenden
Lifecycle-Events.
