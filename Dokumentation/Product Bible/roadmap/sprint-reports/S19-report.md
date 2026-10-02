# Sprint-Report S19 – Shared Availability Snapshot

Stand: 2026-08-05

## Ziel und Ergebnis

S19 ist umgesetzt. Ein zentraler versionierter Availability Snapshot liefert pro Nutzer, Album und Stickercode konsistent physischen Bestand, Reservierungen, beide Transitrichtungen, Verfügbarkeit, Fehlstatus, Doppelte und effektive Verfügbarkeit. Der Snapshot ist read-only und verändert kein sichtbares Produktverhalten.

## Architektur und Snapshot-Vertrag

Der bestehende `InventoryReadService` wurde zur einzigen Snapshot-Quelle erweitert:

- `StickerAvailabilitySnapshotDTO`: unveränderlicher Zustand eines Stickercodes,
- `AlbumAvailabilitySnapshotDTO`: Version `S19-v1`, gemeinsamer Zeitpunkt und schreibgeschütztes Code-Mapping,
- `InventoryReadService.snapshot(...)`: öffentliche read-only Album-Snapshot-API,
- `AlbumInventoryDTO.availability_snapshot_for(...)`: gemeinsamer Zugriff aktiver Bestands- und Trade-Leser.

Verwendete Felder:

- `sticker_code`
- `physical`
- `assigned`
- `reserved`
- `incoming_transit`
- `outgoing_transit`
- `available`
- `missing`
- `duplicates`
- `effective_available`

`effective_available` ist im heutigen Modell exakt die bereits reservierungsbereinigte Menge `available`. Es wurde keine zusätzliche Geschäftsregel eingeführt.

## Betroffene Komponenten

Geändert:

- `App/services/inventory.py`
  - Snapshot-DTOs und Version ergänzt,
  - eingehenden und ausgehenden Transit über einen gemeinsamen Lesepfad konsolidiert,
  - bestehende Album-/Availability-Adapter auf den einmal erzeugten Snapshot gelegt.
- `App/webapp.py`
  - ausschließlich bestehende read-only Availability-Aufrufe auf `availability_snapshot_for(...)` umgestellt,
  - Stickerwall, Fortschritt, Vorschauen, Tradeübersichten und aktives bilaterales Matching lesen dieselbe Quelle.
- `tests/test_s19_shared_availability_snapshot.py`
  - 18 isolierte S19-Contract- und Regressionstests ergänzt.
- `Dokumentation/Product Bible/roadmap/s19-shared-availability-snapshot.md`
  - Snapshot-Vertrag dokumentiert.
- `Dokumentation/Product Bible/roadmap/README.md`
  - S19-Artefakte verlinkt und S20 als nächsten regulären Sprint ausgewiesen.
- `Dokumentation/Product Bible/roadmap/sprint-reports/S19-report.md`
  - dieser Bericht.

Nicht geändert wurden Inventory-Schreibservice, Reservations-, Shipping-, Receipt- und Problem-Services, Migrationen, Datenbankschema, CSS und Templates. Die vorhandenen historischen Testdateien mit `test_s19_...` und `test_s20_...` blieben unverändert.

## Ersetzte Doppelberechnungen

- Reservierung, physische Availability und eingehender Transit werden nicht mehr je Verbraucher zusammengesetzt, sondern einmal im Album-Snapshot.
- Eingehender und ausgehender Transit verwenden dieselbe Abfrageprojektion mit lediglich fest vorgegebener Perspektive.
- Aktive Ansichten greifen nicht mehr separat auf `AvailabilityDTO` zu, sondern auf dasselbe Snapshotobjekt.
- Der Kompatibilitätsadapter `availability(...)` liefert das bereits erzeugte DTO und rechnet nicht erneut.

Der historische reine Mengenmatcher `trade_candidates(...)` bleibt ausschließlich als Golden-Master-Vergleich erhalten und ist kein aktiver zweiter Produktlesepfad.

## Testergebnisse

S19 gezielt:

```bash
python3 -m unittest tests.test_s19_shared_availability_snapshot -v
```

Ergebnis: **18 Tests, OK**.

Vollständiges Gate, zweimal ausgeführt:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Lauf 1: **307 Tests, OK**
- Lauf 2: **307 Tests, OK**

Abgedeckt sind Snapshot-/Inventory-Gleichheit, Reservierungen, `incoming_transit`, `outgoing_transit`, fehlend, vorhanden, doppelt, effektiv verfügbar, Versand, Empfang, Problemfall, Problemauflösung, mehrere gleichzeitige Trades, Mutationsfreiheit, unverändertes Inventory, Stickerwall, Tradeansichten und Golden-Master-Matching.

Alle S19-Tests arbeiten ausschließlich auf temporären Kopien der S00-Fixture. Lokale Entwicklungsdatenbank und kanonische Fixture waren niemals Testziel.

## Release Readiness

- bestehender lokaler Migrationsstand read-only geprüft: **V0005**
- erforderliche neue Migration: **keine**
- ausgeführte Migration: **keine**
- `PRAGMA integrity_check`: **ok**
- `PRAGMA foreign_key_check`: **keine Befunde**
- lokale Datenbankprüfsumme unverändert: `b72d7f8f0aa1bd3b70566ea3d79009be0feab6ff368105c470b66d25b563e1cc`
- kanonische S00-Fixture unverändert: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`
- beide vollständigen Gates reproduzierbar grün
- Syntaxprüfung erfolgreich
- `git diff --check`: **ohne Befund**

## Offene Punkte für S20

- S20 kann Markt- und persönliche Trade-Abdeckung aus `effective_available`, `missing` und den erklärbaren Snapshotfeldern ableiten.
- Keine Marktabdeckung, kein Ranking, keine Top-Match-Optimierung und kein Caching wurden in S19 vorgezogen.
- S21 wurde nicht begonnen.

## Scope-Bestätigung

- ausschließlich S19 „Shared Availability Snapshot“ umgesetzt
- keine neue Produktfunktion außerhalb des Snapshotumfangs
- keine Trade-, Versand-, Empfangs- oder Problemlogik geändert
- keine Bestandsmutation oder Reservierung ergänzt
- keine Migration und keine Schemaänderung
- keine UI-Politur, keine neuen Filter oder Buttons
- S20 und S21 nicht begonnen
- kein Commit
- kein Push
