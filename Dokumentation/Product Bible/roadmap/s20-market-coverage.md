# S20 – Markt- und persönliche Trade-Abdeckung

Stand: 2026-08-05
Status: umgesetzt

## Ziel und Grenze

S20 stellt zwei fachlich getrennte, erklärbare Kennzahlen auf Basis des S19 Shared Availability Snapshot bereit:

1. Community Market Coverage: Welcher Anteil der physisch fehlenden Stickercodes eines Nutzers ist bei mindestens einem betrachteten Community-Nutzer effektiv verfügbar?
2. Persönliche Trade-Abdeckung: Welche physisch fehlenden Stickercodes besitzt ein einzelner Gegenüber, und welche davon sind dort effektiv verfügbar?

Die Ergebnisse sind reine Fakten. Sie erzeugen keinen Trade, keine Empfehlung, keine Partnerbewertung, kein Ranking und keine optimierte Kombination. Eine finale UI ist nicht Bestandteil von S20.

## Service-API

Der read-only Service liegt in `App/services/trade_coverage.py`:

```python
coverage = TradeCoverageService(InventoryReadService(connection))

market = coverage.community_market_coverage(
    user_id,
    album_id,
    catalog_codes,
    community_user_ids,
)

personal = coverage.personal_trade_coverage(
    user_id,
    counterpart_user_id,
    album_id,
    catalog_codes,
)
```

Der Service verwendet ausschließlich `InventoryReadService.snapshot(...)`. Er enthält kein SQL und keinen Zugriff auf `stickers`, Reservations- oder Lifecycle-Tabellen. Auswahl und Berechtigung der betrachteten Community-Nutzer bleiben Aufgabe des aufrufenden Kontexts; S20 entdeckt, filtert oder sortiert keine Partner.

## Gemeinsame Zählregeln

- Betrachtungseinheit ist ein unterschiedlicher Stickercode im übergebenen Albumkatalog.
- Doppelte Katalogeinträge werden einmal gezählt; Mengen erhöhen keinen Coverage-Zähler mehrfach.
- `missing` und `effective_available` werden unverändert aus S19 übernommen.
- Prozentwerte verwenden die bestehende ganzzahlige Sammlr-Konvention `int(Anteil * 100)`; die exakten Zähler und Codelisten bleiben die primäre Wahrheit.
- Wenn keine Stickercodes fehlen, existiert kein Nenner. `coverage_percent` ist dann `None` und `has_missing` ist `False`. Daraus wird weder 0 % noch 100 % Albumfortschritt erfunden.

Beide DTOs tragen:

```text
scope = distinct_codes/current_album/current_snapshot
confidence = exact_for_supplied_users_and_snapshot_state
```

Damit ist sichtbar: Das Ergebnis ist für die übergebenen Nutzer und den gelesenen Snapshot exakt, aber keine Aussage über unbekannte Nutzer, künftige Bestände oder tatsächlich zustande kommende Trades.

## Community Market Coverage

Für Zielnutzer `u`, Albumkatalog `C` und betrachtete Community-Nutzer `N` gilt:

```text
M = {c ∈ C | snapshot(u, c).missing}

A = {c ∈ M |
     es existiert n ∈ N, n != u,
     mit snapshot(n, c).effective_available > 0}

U = M − A
```

Ausgabe:

```text
missing_count                 = |M|
available_in_community_count = |A|
unavailable_count            = |U|
coverage_percent             = int(|A| / |M| * 100), falls |M| > 0
```

Mehrere Nutzer mit demselben verfügbaren Code erhöhen die Abdeckung nicht mehrfach. Der Zielnutzer wird auch dann ausgeschlossen, wenn seine ID versehentlich in `community_user_ids` enthalten ist. Wiederholte Community-IDs werden dedupliziert, ohne eine Qualitäts- oder Prioritätsreihenfolge zu erzeugen.

## Persönliche Trade-Abdeckung

Für Zielnutzer `u`, Gegenüber `p` und Albumkatalog `C` gilt:

```text
M = {c ∈ C | snapshot(u, c).missing}

P = {c ∈ M | snapshot(p, c).physical > 0}

E = {c ∈ M | snapshot(p, c).effective_available > 0}
```

Ausgabe:

```text
missing_count                  = |M|
present_at_counterpart_count  = |P|
effectively_available_count   = |E|
coverage_percent              = int(|E| / |M| * 100), falls |M| > 0
```

`P` und `E` sind bewusst getrennt: Die einzige physische Kopie des Gegenübers ist vorhanden, aber dem Album zugeordnet und deshalb nicht effektiv verfügbar. `E` ist immer eine Teilmenge von `P`.

Die Kennzahl prüft nicht, ob der Zielnutzer seinerseits genügend Tauschmaterial besitzt. Sie simuliert keine Pakete und löst keine Konflikte zwischen mehreren Partnern. Diese Aussagegrenze verhindert, dass S20 als Empfehlung oder Abschlussprognose missverstanden wird.

## Reservierung, Transit und Probleme

S20 interpretiert diese Zustände nicht neu:

- aktive Reservierungen reduzieren `effective_available` bereits im S19-Snapshot,
- `incoming_transit` macht einen physisch fehlenden Sticker nicht vorhanden,
- `outgoing_transit` ist beim Absender bereits aus `physical` entfernt und nicht verfügbar,
- ein offener Problemrest bleibt Transit und deckt keinen fehlenden Code,
- nach Problemauflösung oder Empfang liefert ein späterer Snapshot den neuen physischen Zustand.

Snapshot und Coverage-Service mutieren diese Zustände niemals.

## DTOs

`CommunityMarketCoverageDTO` enthält:

- Nutzer und Album,
- fehlende, community-verfügbare und nicht verfügbare Anzahl,
- Prozentwert beziehungsweise `None`,
- die drei erklärenden Codelisten,
- Anzahl der tatsächlich betrachteten Community-Nutzer,
- Scope und Confidence.

`PersonalTradeCoverageDTO` enthält:

- Zielnutzer, Gegenüber und Album,
- fehlende, beim Gegenüber physisch vorhandene und effektiv verfügbare Anzahl,
- Prozentwert beziehungsweise `None`,
- die drei erklärenden Codelisten,
- Scope und Confidence.

Beide DTOs sind eingefrorene Dataclasses.

## Migration und UI

S20 benötigt keine Migration und keine Schemaänderung. Die API liest das bestehende V0005-Modell ausschließlich über S19. Es wurden keine UI, keine Buttons, keine Filter und keine Sortierung ergänzt.

## Tests

Gezielt:

```bash
python3 -m unittest tests.test_s20_market_coverage -v
```

Vollständiges Gate:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Die Tests verwenden ausschließlich temporäre V0005-Kopien der kanonischen S00-Fixture. Abgedeckt sind 0 %, 100 %, Teilabdeckung, persönliche und asymmetrische Abdeckung, Reservierungen, beide Transitrichtungen, Snapshot-/Inventory-Unveränderlichkeit, mehrere Nutzer und Alben, Problem und Auflösung sowie der reine Snapshotvertrag.

## S21-Grenze

S21 darf aus den S19-/S20-Erklärdaten konfliktfreie Pakete und Top Matches berechnen. S20 enthält keine Auswahl des besten Partners, keine gemeinsam verbrauchten Ressourcen, kein Ranking, keine Optimierung und keine Empfehlung.
