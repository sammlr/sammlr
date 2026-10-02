# S27-Abschlussbericht – Album-Privacy und getrennter Tradepool

Stand: 2026-08-08

## Ziel und Ergebnis

S27 ist vollständig umgesetzt. Album-Sichtbarkeit und Tradepool-Teilnahme
werden pro Nutzer-Album-Zuordnung gespeichert, serverseitig geprüft und
fachlich unabhängig voneinander behandelt. Berechtigte Fremde können ein Album
read-only bis zur vollständigen Wall und exakten Stickermenge ansehen.
Nichtberechtigte erhalten ein einheitliches HTTP 404, bevor Inventardaten
gelesen oder gerendert werden.

Die bestehenden S20-Coverage-, S21-Top-Match- und S22-Smart-Request-Pfade
verwenden die zentrale Tradepool-Entscheidung. Ein privates Album kann damit
weiter matchbar sein; ein öffentlich sichtbares Album mit deaktiviertem Pool
erscheint in keiner neuen Match- oder Anfragestrecke. Bereits bestehende Trades
bleiben sichtbar und abwickelbar.

## Architektur

Neu ist der zentrale `AlbumPrivacyService` mit immutablem `AlbumAccessDTO` und
eindeutigen Update-Codes. Er kapselt:

- `public`, `friends` und `private`,
- Eigentümer- und Friend-Testdouble-Prüfung,
- sichtbare Alben eines Profilinhabers,
- das unabhängige `trade_pool_enabled`,
- poolberechtigte Nutzer eines Albums,
- validierte Eigentümerupdates.

Der produktive Friend-Resolver liefert mangels bestehender Freundschaftsdomäne
immer negativ. Nur Tests beziehungsweise eine explizit injizierte App-Funktion
können einen Friend-Zugriff positiv beantworten. Es wurde keine Freundschaft
gespeichert und keine S28-Funktion vorgezogen.

## Datenfluss

### Sichtbarkeit

```text
Fremdprofil oder Fremdalbum-URL
→ AlbumPrivacyService.can_view / visible_album_ids
→ unzulässig: HTTP 404 bzw. Album aus Profilprojektion entfernen
→ zulässig: bestehender InventoryReadService
→ read-only Profil-, Wall- oder Stickerdetail-DTO
```

### Tradepool

```text
user_albums.trade_pool_enabled
→ AlbumPrivacyService
→ globale und albumbezogene Tauschbörse
→ TradeCoverageService (S20)
→ TopMatchOptimizationService (S21)
→ SmartTradeRequestService Berechnung/Erzeugung/Recheck (S22)
```

Auf diesem Pfad wird `visibility` nicht als Matchingkriterium verwendet. Ein
konkreter Match zeigt nur die bereits fachlich benötigten Positionen und
Mengen, keine allgemeine private Wall.

## Neue Komponenten und Dateien

- `App/Database/migrations/0007_album_privacy_trade_pool.up.sql`
- `App/Database/migrations/0007_album_privacy_trade_pool.down.sql`
- `App/services/album_privacy.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `Dokumentation/Product Bible/roadmap/s27-album-privacy-trade-pool.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S27-report.md`

## Geänderte Komponenten und Dateien

- `App/webapp.py`: Eigentümerkontrollen, sichere Fremdalbum-/Detailrouten und
  Poolfilter an den vorhandenen Börsen- und Smart-Einstiegen.
- `App/services/collector_profiles.py`: albumbezogene Profilaggregate werden
  vor dem Inventory-Read nach Sichtbarkeit gefiltert.
- `App/services/trade_coverage.py`: S20 verwendet die zentrale Poolregel; die
  Coverage-Formeln bleiben unverändert.
- `App/services/smart_trade_requests.py`: Erstellung und Recheck lehnen
  poolfremde Pakete ab, ohne sie anzupassen.
- `App/static/style.css`: ausschließlich kompakte Darstellung der neuen
  Eigentümerkontrolle.
- `tests/test_s26_collector_profiles.py`: nur die durch V0007 überholte
  Latest-Migration-Erwartung angepasst; der isolierte S26-Teststand bleibt
  weiterhin V0006.
- `Dokumentation/Product Bible/roadmap/README.md`: S27-Verweise und S28 als
  nächster offener Sprint.

## Migration V0007

V0007 ergänzt `user_albums` um:

- `visibility TEXT NOT NULL DEFAULT 'private'` mit Check-Constraint,
- `trade_pool_enabled INTEGER NOT NULL DEFAULT 1` mit booleschem
  Check-Constraint,
- zwei rein leseseitige Indizes.

Bestehende und neue Albumzuordnungen erhalten damit `private` und einen aktiven
Tradepool. Die Down-Migration rekonstruiert die V0006-Tabellenform unter Erhalt
von ID, Nutzer und Album. Up, No-op-Wiederholung, Down und erneutes Up wurden
ausschließlich auf temporären Fixture-Kopien geprüft.

Die lokale Entwicklungsdatenbank wurde nicht migriert und bleibt auf V0006.
Die kanonische S00-Fixture wurde nicht verändert.

## Unveränderte Komponenten

- Inventory Read/Write, Availability, Guard und Shared Snapshot,
- Trade Lifecycle, Reservierung, Versand, Empfang und Problemfälle,
- S20-Berechnungsformeln und S21-Score-/Tie-Break-Regeln,
- gespeicherte S22-Pakete und die bestehende TradeRequest-Struktur,
- Notifications, Operational Home und bestehende Tradeabwicklung,
- Freundschaften, Bewertungen, Blockierung und Aktivstatus.

## Testmatrix

| Bereich | Nachweis |
| --- | --- |
| V0007 | Up, Defaults/Backfill, Constraints, wiederholtes Up, Down, erneutes Up |
| Privacy | Eigentümer, public, friends mit Testdouble, friends ohne Beziehung, private |
| HTTP-Schutz | 404 für verborgenes und unbekanntes Fremdalbum sowie Stickerdetail |
| Profil | Albumzahl/Doppelte nur aus sichtbaren Alben; Trophy-Zahl unabhängig |
| Fremdalbum | vollständige read-only Wall, Filter, exakte Quantity und Doppelte |
| Update | Eigentümer-POST, unabhängiges Poolflag, ungültige Sichtbarkeit 400 |
| Trennung | privat + Pool aktiv matchbar; öffentlich + Pool aus sichtbar, nicht matchbar |
| Börsen | globale Börse, Albumbörse, direkter Tradeeinstieg und Request-POST |
| S20–S22 | Coverage, TopMatch, Smart-Erzeugung und Recheck teilen die Poolregel |
| Bestandsschutz | Fremd-GETs und abgelehnte Smart-Erzeugung ohne Mutation |
| Bestandstrades | laufender Trade bleibt nach Pool-Ausstieg lesbar |

## Testergebnisse

S27-spezifisch:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s27_album_privacy_trade_pool -v
Ran 9 tests
OK
```

Vollständiges Gate, Lauf 1:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
Ran 419 tests in 4.448s
OK
```

Vollständiges Gate, Lauf 2:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
Ran 419 tests in 4.456s
OK
```

## Release Readiness

- `PRAGMA integrity_check` auf der unveränderten lokalen Datenbank: `ok`.
- `PRAGMA foreign_key_check`: keine Befunde.
- Lokaler Migrationsstand: V0006; V0007 wurde nur auf temporären Testkopien
  ausgeführt.
- SHA-256 lokale Datenbank:
  `7db5218022c0beb35eead61222b6b65678f0f4484ed1ce8aaabdf341e6fea97e`.
- SHA-256 S00-Fixture:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- `git diff --check`: erfolgreich, keine Whitespace-Fehler.
- Ausschließlich temporäre Testdatenbanken wurden auf V0007 migriert.

## Bekannte Grenzen und offene Punkte für S28

- `friends` besitzt bewusst nur eine injizierbare Prüfnaht; ein produktives
  Freundschaftsmodell ist nicht Teil von S27.
- Es gibt keine öffentliche Suche, Feed-Erweiterung, Blockierung, Bewertung
  oder Aktivstatusanzeige.
- V0007 muss vor manueller Nutzung der S27-Einstellungen kontrolliert auf die
  jeweilige Entwicklungsumgebung angewendet werden; dies erfolgte in diesem
  Sprint ausdrücklich nicht auf der lokalen Datenbank.
- S28 wurde nicht analysiert, vorbereitet oder begonnen.

## Scope-Bestätigung

Es wurde ausschließlich S27 umgesetzt. S28 wurde nicht begonnen. Es gab keine
Änderung an Inventory-Buchungen, Trade Lifecycle, Shipping, Receipt, Problems,
Notification-Typen oder Operational Home. Es wurde kein Commit erstellt und
kein Push durchgeführt.
