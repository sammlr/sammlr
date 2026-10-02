# S11 – Zentrale Availability-Projektion

Stand: 2026-08-01
Status: verbindliche read-only Kompatibilitätsprojektion auf dem Ist-Schema
Grundlagen: S08 Inventory Contract V1, S09 Read Service, S10 Write Service

## 1. Zweck und Grenze

S11 stellt eine zentrale, erklärbare Availability-Berechnung bereit. Sie
projiziert ausschließlich die heutige aggregierte `quantity` auf das in S08
definierte Zielvokabular. Es werden keine Reservierungen erzeugt, gespeichert
oder durchgesetzt.

Die Komponente ist:

- read-only und ohne Datenbankzugriff,
- deterministisch für eine gegebene `quantity`,
- frei von UI-, Trade-, Notification- und Schreiblogik,
- ohne Tabellen, Spalten oder Migrationen.

## 2. Heutiges Availability-Modell

Für das aktuelle Einzelalbum-Modell gilt:

```text
physical         = max(quantity, 0)
assigned         = min(physical, 1)
reserved         = 0
available        = max(physical - assigned - reserved, 0)
incoming_transit = 0
reservable       = available
```

Für alle gültigen heutigen Daten mit `quantity >= 0` entspricht dies exakt dem
S08-Vertrag:

```text
physical = quantity
assigned = min(quantity, 1)
available = max(quantity - 1, 0)
reserved = incoming_transit = 0
```

`max(quantity, 0)` ist ausschließlich eine defensive read-only Projektion für
vertragswidrige negative Eingangswerte. Sie korrigiert keine Daten und ist kein
Inventory Guard. Die kanonische S00-Fixture enthält keine negativen Mengen.

## 3. Availability-Komponente

Die zentrale Komponente liegt in:

```text
App/services/inventory_availability.py
```

Aufruf:

```python
availability = LegacyAvailabilityCalculator.from_quantity(quantity)
```

Der Name `LegacyAvailabilityCalculator` macht deutlich, dass diese Berechnung
nur das heutige Schema abbildet. Eine spätere Reservierungsquelle darf nicht
stillschweigend angenommen werden.

## 4. `AvailabilityDTO`

Das unveränderliche DTO enthält:

| Feld/Eigenschaft | Bedeutung in S11 |
| --- | --- |
| `physical` | heutige physische Menge aus `quantity` |
| `assigned` | implizit höchstens eine Kopie für das heutige Einzelalbum |
| `reserved` | immer `0`, da keine Reservierungsquelle existiert |
| `available` | freie physische Überschusskopien |
| `incoming_transit` | immer `0`, da kein Transitmodell existiert |
| `reservable` | Alias für `available`; erzeugt keine Reservierung |
| `is_available` | wahr genau dann, wenn `available > 0` |
| `balance_is_valid` | prüft Nichtnegativität und `P = A + R + V` |
| `reason_code` | stabiler technischer Begründungscode |
| `explanation` | menschenlesbare Erklärung der Projektion |

### Begründungscodes

| `reason_code` | Bedingung | Erklärung |
| --- | --- | --- |
| `not_physical` | `physical == 0` | keine physische Kopie vorhanden |
| `assigned_only` | `physical == 1` | einzige Kopie dem heutigen Einzelalbum zugeordnet |
| `legacy_surplus_available` | `physical >= 2` | Überschusskopien frei, da S11 keine Reservierungen kennt |

Die Texte sind Erklärdaten für Architektur und spätere Adapter. S11 zeigt sie
nicht in der UI.

## 5. Beispiele

| `quantity` | `physical` | `assigned` | `reserved` | `available` | `incoming_transit` | Ergebnis |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 0 | 0 | 0 | 0 | fehlt, nicht verfügbar |
| 1 | 1 | 1 | 0 | 0 | 0 | nur Albumkopie, nicht verfügbar |
| 2 | 2 | 1 | 0 | 1 | 0 | eine freie Überschusskopie |
| 5 | 5 | 1 | 0 | 4 | 0 | vier freie Überschusskopien |

In jedem Beispiel gilt:

```text
0 <= available <= physical
physical = assigned + reserved + available
```

## 6. Integration in die Inventory-Architektur

`StickerInventoryDTO.availability` liefert die zentrale Projektion für eine
vorhandene Zeile. `AlbumInventoryDTO.availability(code)` liefert dasselbe DTO
und für einen fehlenden Code nachvollziehbar den Zustand mit Menge null.

Zusätzlich bietet `AlbumInventoryDTO.availabilities` ein schreibgeschütztes
Mapping der vorhandenen Codes. Die bestehenden `quantity`- und
`quantities`-Kompatibilitätszugriffe bleiben erhalten.

`AlbumInventoryDTO.progress` summiert Doppelte jetzt über
`availability.available`. Das Ergebnis bleibt identisch zur bisherigen Formel
`max(quantity - 1, 0)`.

## 7. Verhaltensgleich umgestellte Lesepfade

| Fachbereich | Verwendung der Availability | Identisches Altverhalten |
| --- | --- | --- |
| Albumfortschritt | Summe `available` | bisher `max(quantity - 1, 0)` |
| Papierliste | fehlend über `physical == 0`, Doppelte über `available` | bisher `quantity == 0` und `quantity - 1` |
| Papiertransfer-Prüfung | maximal abgebbar über `available` | bisher `max(quantity - 1, 0)` |
| Sammlungs-Matching | fehlend/tauschbar über `physical` und `is_available` | bisher `quantity == 0` / `quantity >= 2` |
| Album-Tauschbörse | Partner und Codes über Availability | identische Code-Mengen |
| Dealzusammenstellung | `availability_trade_candidates` | identische Get-/Give-Counts |
| Tradeanfrage-Prüfung | erlaubte Mengen aus Availability-Kandidaten | identische Grenzen |
| globale Tradezentrale | Partnerzählung über Availability | identische Resultate |

Die alte Funktion `trade_candidates` und die `quantities`-Projektion bleiben
als Golden-Master- und Kompatibilitätsweg bestehen. Aktive Matching-Workflows
verwenden `availability_trade_candidates`.

## 8. Bewusst nicht umgestellte Lesedaten

Globale Statistik- und Trophy-Pfade lesen teilweise das redundant gespeicherte
Feld `stickers.duplicates`. Der S10-Golden-Master dokumentiert, dass dieses Feld
bei einer Legacy-Mehrfachanlage zeitweise von `max(quantity - 1, 0)` abweichen
kann. Eine Umstellung dieser Pfade auf abgeleitete Availability wäre deshalb
nicht für alle Legacy-Daten garantiert verhaltensgleich und wurde in S11 nicht
vorgenommen.

## 9. Keine Reservierungslogik

`reserved` und `incoming_transit` sind im DTO sichtbar, aber in S11 immer null.
Es existieren ausdrücklich nicht:

- eine Reservierungsquelle,
- ein Reservation Command,
- eine Bindung bei Tradeanfrage oder Annahme,
- ein Guard im `InventoryWriteService`,
- eine Schema- oder Persistenzänderung.

`reservable` benennt lediglich die Menge, die im heutigen Modell theoretisch
frei ist. Die Eigenschaft führt keine Aktion aus.

## 10. Tests

Nur S11:

```sh
python3 -m unittest discover -s tests -p 'test_s11_*.py' -v
```

Vollständiges Gate S01–S11:

```sh
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Geprüft werden insbesondere `0/1/n`, Nichtnegativität, Obergrenze durch
`physical`, exakte S08-Bilanz, Begründungscodes, Fixture-Kompatibilität,
Sammlung/Papierliste, Alt-/Neu-Matching, read-only Verhalten und unverändertes
Schema.
