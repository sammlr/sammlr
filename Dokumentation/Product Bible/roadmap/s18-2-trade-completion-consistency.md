# S18.2 – Trade-Abschluss konsolidieren

Stand: 2026-08-05

## Ziel

S18.2 macht den bereits in S13–S18 sowie S18.1 implementierten Abschluss eines Lifecycle-Trades in allen bestehenden Ansichten eindeutig und read-only. Die Nacharbeit erzeugt keinen neuen Abschlussweg und verändert weder Versand, Empfang, Problemauflösung noch Bestandsbuchung.

## Verbindliche Abschlussbedingung

Für einen Lifecycle-Trade gilt der erfolgreiche Abschluss nur konsistent, wenn:

1. `trade_requests.status = 'completed'` ist,
2. `trades.lifecycle_state = 'completed'` ist,
3. beide Empfangsseiten bestätigt sind, sofern das Empfangsschema für den Trade vorhanden ist,
4. kein Problembericht `state = 'open'` besitzt,
5. keine historische Problemposition eine offene Restmenge besitzt.

Der Abschlusszeitpunkt stammt ausschließlich aus `trades.completed_at`. Bestehende abgeschlossene Legacy-Trades ohne Lifecycle-Projektion bleiben über ihren unveränderten Legacy-Status lesbar; ein nicht verfügbarer historischer Abschlusszeitpunkt wird nicht erfunden.

Die read-only Projektion `trade_is_successfully_completed(...)` validiert diese bereits bestehenden Zustände für Darstellung, Timeline und Profilarchiv. Sie schreibt keine Daten und ersetzt weder `TradeReceiptService` noch `TradeProblemService`.

## Bestehende Abschlusswege

### Normaler Empfang

- Die erste Empfangsseite bucht ausschließlich ihre eingehenden Positionen.
- Der Trade bleibt `accepted` / `partially_received`.
- Die zweite vollständig empfangene Seite setzt Legacy und Lifecycle gemeinsam auf `completed`.

### Problembehafteter Empfang

- Eine offene Restmenge und ein offener Bericht verhindern den Abschluss.
- Eine bestätigte physische Nachlieferung löst die Restmenge über den bestehenden Problemweg auf.
- Erst wenn beide Empfangsseiten vollständig und alle Probleme gelöst sind, entsteht derselbe Endzustand wie beim normalen Empfang.
- Problembericht, Positionen und Problemereignisse bleiben historisch erhalten.

## Read-only Endzustand

Ein konsistent abgeschlossener Trade zeigt:

- Statuschip `Abgeschlossen`,
- `Trade abgeschlossen`,
- den bestehenden Abschlusszeitpunkt,
- erhaltene und abgegebene Vertragsposten,
- vollständige Timeline,
- erhaltene Problemhistorie.

Die Abschlussleiste enthält keine Buttons oder Formulare mehr. Insbesondere werden keine Aktionen für Versand, Empfang, Problembericht, Problemauflösung, generische Bestätigung oder pauschales Scheitern gerendert.

Direkte POST-Retries bleiben durch die bestehenden Services und Statusbedingungen kontrolliert idempotent oder werden ohne Mutation abgewiesen. Der alte generische Abschlussweg akzeptiert keinen bereits abgeschlossenen Lifecycle-Trade und kann ihn nicht erneut buchen.

## Übersichten und Archiv

- Globale Tauschbörse: abgeschlossene Trades sind nicht mehr Teil der laufenden Absprachen oder Anfragen.
- Albumbezogene Tauschbörse: abgeschlossene Trades sind nicht mehr Teil der laufenden Absprachen oder Anfragen.
- Profil-Tradearchiv: verwendet dieselbe konsistente Abschlussprojektion, zeigt den Abschlusszeitpunkt und verlinkt zur read-only Dealansicht.
- Direkte Deal-URLs und die S07-Rückwegverträge bleiben unverändert.

## Timeline

Bei konsistent abgeschlossenen Lifecycle-Trades:

- sind keine verpflichtenden Timeline-Schritte mehr `pending`,
- endet die Timeline immer mit `Trade abgeschlossen`,
- verwendet der letzte Schritt `trades.completed_at`,
- bleiben gelöste Problemereignisse sichtbar,
- werden vollständig zeitgestempelte historische Schritte stabil chronologisch dargestellt.

Legacy-Timelines ohne vollständige historische Zeitstempel behalten ihre bestehende Reihenfolge und erhalten keine erfundenen Zeitpunkte.

## Idempotenz und Side Effects

Wiederholtes Rendering oder erneute Aufrufe bereits verarbeiteter Wege dürfen nicht erzeugen:

- zusätzliche Inventory-Buchungen,
- zusätzliche Trophy-Einträge,
- zusätzliche Abschlussnotifications,
- zusätzliche Completed-Events,
- einen neuen Abschlusszeitpunkt.

Die S18.2-Tests vergleichen deshalb Inventory, Abschlusszeit, Event-, Notification- und Trophy-Zähler vor und nach Retries sowie read-only Renderings.

## Datenbank und Migration

S18.2 benötigt keine Migration und keine Schemaänderung. Der erforderliche lokale Stand bleibt V0005.

## Tests

S18.2-spezifisch (historischer technischer Modulname bleibt unverändert):

```bash
python3 -m unittest tests.test_s20_trade_completion_consistency -v
```

Vollständiges Gate:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Alle Tests verwenden ausschließlich isolierte Kopien der kanonischen S00-Fixture und migrieren nur diese temporären Testdatenbanken bis V0005.

## Nicht enthalten

Keine neuen Lifecycle-Zustände, Problemtypen, Fristen, Erinnerungen, Bewertungen, Chats, Tracking-, Support-, Share-, Statistik- oder Home-Funktionen. Keine Bestands-, Versand-, Empfangs- oder Problemlogik wurde fachlich geändert.
