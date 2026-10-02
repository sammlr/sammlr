# S09 – Inventory Read Service

Stand: 2026-07-31
Status: verbindlicher read-only Servicevertrag auf dem aktuellen Schema
Grundlage: Inventory Contract V1 aus Sprint S08

## 1. Zweck und Grenze

Der `InventoryReadService` ist die zentrale Lesequelle für heutige
Bestandsinformationen. Sammlung, Albumfortschritt und Matching erhalten damit
dieselben Mengen aus derselben Abfrage. Der Service liest ausschließlich die
bestehende Tabelle `stickers` und verändert weder Daten noch Schema.

S09 führt ausdrücklich nicht ein:

- Schreibbefehle oder Schreibvalidierung,
- Reservierungen oder Transitstände,
- eine reservation-aware Availability Engine,
- neue Tabellen, Spalten, APIs oder UI-Verhalten.

## 2. Öffentliche Service-API

Der Dienst liegt in `App/services/inventory.py`.

```python
inventory = InventoryReadService(connection)
album_inventory = inventory.album(user_id, album_id)
```

`connection` ist eine bestehende SQLite-Verbindung mit `sqlite3.Row` als
`row_factory`. Ihr Lebenszyklus bleibt beim aufrufenden Lesepfad; der Service
führt weder `commit`, `rollback` noch `close` aus.

`album(user_id, album_id)` führt genau eine parametrisierte `SELECT`-Abfrage
für die Betrachtungseinheit `(Nutzer, Albumtyp)` aus und liefert immer ein
`AlbumInventoryDTO`. Gibt es keine Zeilen, ist dessen Mapping leer. `None` und
unterschiedliche Rückgabeformate werden nicht verwendet.

## 3. DTOs

Alle DTOs sind unveränderliche `dataclass`-Objekte. Enthaltene Mappings sind
schreibgeschützte `MappingProxyType`-Sichten.

### `StickerInventoryDTO`

Das DTO repräsentiert eine vorhandene Zeile des heutigen `stickers`-Schemas:

| Feld/Eigenschaft | Quelle | Bedeutung in S09 |
| --- | --- | --- |
| `id` | `stickers.id` | technische ID der vorhandenen Zeile |
| `user_id` | `stickers.user_id` | Eigentümer im Ist-Modell |
| `album_id` | `stickers.album_id` | Albumtyp im Ist-Modell |
| `sticker_code` | `stickers.sticker_code` | Stickeridentität |
| `status` | `stickers.status` | unverändert gelesener Legacy-Wert |
| `quantity` | `stickers.quantity` | unverändert gelesene heutige Menge |
| `duplicates` | `stickers.duplicates` | unverändert gelesenes redundantes Legacy-Feld |
| `physical` | aus `quantity` | S08-Kompatibilitätsprojektion: `physical = quantity` |
| `duplicate_quantity` | aus `quantity` | heutige sichtbare Doppelte: `max(quantity - 1, 0)` |
| `available` | aus `quantity` | ausschließlich S08-Legacy-Projektion: `max(quantity - 1, 0)` |

`available` bildet in S09 nur das heutige Modell ohne Reservierungen ab. Es ist
keine neue Availability Engine und darf nicht als reservierungsbewusste
Verfügbarkeit interpretiert werden.

Für die schrittweise Migration kann vorhandener Sammlungscode die bisherigen
Zeilenzugriffe wie `item["quantity"]` weiterverwenden. Dieser eng begrenzte
Adapter ändert weder das DTO noch sein einheitliches Rückgabeformat.

### `AlbumInventoryDTO`

Das Album-DTO enthält:

- `user_id` und `album_id`,
- `items_by_code`: schreibgeschütztes Mapping von Sticker-Code auf
  `StickerInventoryDTO`,
- `quantity(code)`: Menge oder `0`, wenn keine Zeile existiert,
- `quantities`: schreibgeschütztes Mapping der heutigen Mengen für bestehende
  Matching-Funktionen,
- `progress(catalog_codes, total)`: zentrale Fortschrittsprojektion.

Wie im alten Lesepfad bedeutet eine fehlende Zeile Menge null. Der Service
erfindet dafür kein DTO und schreibt keine Nullzeile.

### `AlbumProgressDTO`

Die Fortschrittsprojektion liefert genau ein Format:

- `collected`: Anzahl der Katalogcodes mit `quantity > 0`,
- `duplicate_quantity`: Summe von `max(quantity - 1, 0)`,
- `total`: der vom bestehenden Albumlesepfad vorgegebene Gesamtwert,
- `percent`: unverändert `int((collected / total) * 100)`.

Der Katalog und dessen Gesamtwert bleiben außerhalb des Inventory-Service, weil
S09 weder Albumdefinitionen noch Produktlogik verändert.

## 4. In S09 umgestellte Lesepfade

Die Umstellung ist bewusst auf vorhandene reine Leseverwendungen begrenzt:

| Fachbereich | Lesepfad | Weiterhin unverändertes Ergebnis |
| --- | --- | --- |
| Stickerwall und Liste | `lade_album_for_user` | Zeilenwerte, Mengen, Filterzustände und Karten |
| Albumfortschritt | `lade_album_for_user` über `AlbumProgressDTO` | gesammelt, doppelt, Prozent und Gesamt |
| Sammlungs-Matching | `tauschbare_luecken_count`, `album_trade_preview_counts` | erhältliche Lücken und direkte Partner |
| Album-Tauschbörse | `album_trades` | fehlende/doppelte Codes und Partnerresultate |
| Dealzusammenstellung | `user_album_quantities` | Get-/Give-Kandidaten und Mengenlimits |
| globale Tradezentrale | `trades_overview` | Partner und Match-Zähler |

Direkte Einzelabfragen innerhalb vorhandener Schreibabläufe bleiben bewusst
unangetastet. Ihre Konsolidierung ist S10-Umfang und wird in S09 nicht
vorbereitet.

## 5. Golden-Master-Regeln

Der neue Dienst muss gegenüber dem vor S09 vorhandenen SQL-Lesepfad folgende
Gleichheit erfüllen:

```text
alte Zeile je Code = StickerInventoryDTO je Code
alte quantity-Map  = AlbumInventoryDTO.quantities
alte Fortschrittswerte = AlbumProgressDTO
alte Matching-Kandidaten = Matching mit AlbumInventoryDTO.quantities
```

Geprüft werden alle in der S00-Fixture vorhandenen Nutzer-/Album-Kombinationen,
fehlende Bestände sowie die Mengenrandfälle `0`, `1`, `2` und `5`. Die Tests
arbeiten ausschließlich auf temporären Kopien der S00-Fixture.

## 6. Sicherheits- und Kompatibilitätsregeln

- Der Service enthält ausschließlich `SELECT` und keine Schreibmethode.
- SQL-Parameter werden gebunden übergeben.
- DTOs und Mappings sind unveränderlich.
- Produktivdatenbank und kanonische S00-Fixture werden nie als Testziel
  verwendet.
- `quantity`, das gespeicherte Feld `duplicates`, Filtergrenzen,
  Fortschrittsformel und Matchinggrenzen bleiben unverändert.
- Inkonsistente oder ungültige Legacy-Daten werden beim Lesen nicht heimlich
  repariert. Validierung und konsolidierte Schreibregeln gehören nicht zu S09.

## 7. Testbefehl

Nur S09:

```sh
python3 -m unittest discover -s tests -p 'test_s09_*.py' -v
```

Vollständiges Gate S01–S09:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```
