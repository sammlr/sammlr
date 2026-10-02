# S18 – Trade Lifecycle Timeline und Fälligkeiten

Stand: 2026-08-04

## Zweck und Scope

S18 macht den bereits vorhandenen technischen Lifecycle verständlich sichtbar.
Es ergänzt ausschließlich read-only UI-Projektionen: Timeline, lokalisierte
Zeitstempel, einheitliche Statuschips und gelbe Hinweise bei ausstehendem
Versand beziehungsweise lange ausstehendem Empfang.

S18 schreibt keine Events, Zustände oder Fristen. Inventory,
`TradeReservationService`, `TradeShippingService`, `TradeProblemService` und
`TradeReceiptService` bleiben unverändert. Es gibt keine neue Tabelle, keine
Migration, keine Erinnerung, Notification oder Eskalation.

## Datenquellen und Ereigniskatalog

| Sichtbares Ereignis | Vorhandene Quelle | Zeitstempel |
| --- | --- | --- |
| Anfrage gesendet | `trade_requests` | `created_at` |
| Anfrage angenommen | erste Reservierung des Lifecycle-Trades | `MIN(trade_reservations.created_at)` |
| Sticker reserviert | erste Reservierung des Lifecycle-Trades | `MIN(trade_reservations.created_at)` |
| Eigener/Gegenseiten-Versand | `trade_shipping_status` | seitenbezogenes `*_shipped_at` |
| Problem gemeldet | `trade_receipt_reports` | `created_at` |
| Problem gelöst | `trade_receipt_reports` | `resolved_at` |
| Eigener/Gegenseiten-Empfang | `trade_receipt_status` | seitenbezogenes `*_received_at` |
| Trade abgeschlossen | `trades` | `completed_at` |

Die Timeline wird immer aus Sicht des angemeldeten Nutzers projiziert. Deshalb
bedeuten „eigener Versand“, „Gegenseite versendet“, „eigener Empfang“ und
„Gegenseite bestätigt“ je Nutzer unterschiedliche Seiten desselben
Lifecycle-Datensatzes.

Es werden keine fehlenden historischen Ereignisse nachträglich erzeugt. Bei
Legacy-Trades bleibt der Zustand lesbar; für einen nicht vorhandenen
historischen Zeitpunkt erscheint ausdrücklich „Zeitpunkt nicht verfügbar“.

## Timeline-Zustände

Jede Zeile besitzt ausschließlich einen Darstellungszustand:

- `done`: fachlich erreicht, grüner Haken,
- `pending`: noch offen, leerer Kreis,
- `warning`: vorhandener Problemfall, gelber Marker,
- `muted`: beendeter Legacy-/Anfragepfad.

Beispiel aus Sicht eines Nutzers:

```text
✓ Anfrage gesendet                  31.07.2026  12:00
✓ Anfrage angenommen               31.07.2026  13:00
✓ Sticker reserviert               31.07.2026  13:00
✓ Eigener Versand bestätigt        03.08.2026  20:18
✓ Gegenseite versendet             03.08.2026  20:22
✓ Eigener Empfang bestätigt        04.08.2026  11:04
○ Gegenseite bestätigt
○ Trade abgeschlossen
```

Offene Probleme ergänzen `Problem … gemeldet` und `Problem offen`. Nach der
vorhandenen S17-Auflösung bleibt die Meldung sichtbar und wird um
`Problem gelöst` samt Auflösungszeit ergänzt. Die S17-Problemhistorie bleibt
parallel unverändert erhalten.

## Zeitformat und Zeitzone

SQLite-`CURRENT_TIMESTAMP` wird als UTC interpretiert und für die Darstellung
über `Europe/Berlin` lokalisiert. Datum und Uhrzeit erscheinen getrennt im
Sammlr-Format:

```text
03.08.2026
20:18
```

Sommer- und Winterzeit werden durch die IANA-Zeitzone berücksichtigt. Rohwerte
in der Datenbank werden nicht verändert.

## Statuschips

Die primären Tradeansichten verwenden dieselbe Chip-Komponente und dieselbe
Wortwahl:

- `Offen`
- `Reserviert`
- `Versand läuft`
- `Problem offen`
- `Teilweise erhalten`
- `Empfang vollständig`
- `Abgeschlossen`

Die Komponente wird in Dealansicht, globaler Tauschbörse und albumbezogener
Tauschbörse wiederverwendet. Farbe ist unterstützend; der Text trägt die
fachliche Aussage.

## Fälligkeiten und gelbe Hinweise

### Versand

Die bereits festgelegte Versandfrist beträgt fünf Werktage ab verbindlicher
Annahme. Weil kein separates Annahmefeld existiert, verwendet die read-only
Projektion den frühesten vorhandenen Reservierungszeitpunkt. Werktage sind in
dieser Darstellung Montag bis Freitag; ein Feiertagskalender wird nicht
eingeführt. Nach Fristablauf erscheint:

```text
Versand steht noch aus
Fällig seit …
```

### Empfang

Ist der Versand der Gegenseite seit mindestens 14 Kalendertagen bestätigt und
der eigene Empfang weiterhin offen, erscheint entsprechend der S18-Vorgabe:

```text
Empfang steht noch aus
Versendet vor 14 Tagen
```

Ein eigener offener S17-Problembericht ersetzt diesen allgemeinen Hinweis,
weil der konkrete Problemzustand bereits sichtbar ist.

Beide Regeln sind reine Darstellungsberechnungen. Sie speichern keinen
`overdue`-Status, verändern keine Frist, schließen keinen Trade und lösen keine
Notification oder Eskalation aus.

## Historie

Das vorhandene Profil-Tradearchiv verwendet für neue Lifecycle-Trades den
tatsächlichen `completed_at`-Zeitpunkt statt der Anfragezeit. Legacy-Trades
ohne Lifecycle-Abschlusszeit fallen weiterhin lesbar auf ihre vorhandene
Anfragezeit zurück. Sortierung und Anzeige erfolgen read-only.

## Screens / Ansichten

S18 definiert vier prüfbare Darstellungszustände:

1. **Offene Anfrage:** Chip `Offen`; Anfrage gesendet abgeschlossen, Annahme
   und Reservierung offen.
2. **Laufender Versand:** Chip `Reserviert` oder `Versand läuft`; Versand und
   Empfang je Seite mit lokalisierten Zeiten; gegebenenfalls gelber Hinweis.
3. **Problemfall:** Chip `Problem offen`; Problem gemeldet/offen in Timeline
   sowie die bestehende detaillierte S17-Historie.
4. **Abgeschlossen:** Chip `Abgeschlossen`; beide Empfänge und Abschluss mit
   `completed_at`; Profilarchiv verwendet das Abschlussdatum.

Es wurden keine künstlichen Bild-Mockups als Beleg erzeugt. Die Ansichten sind
deterministisch über die S18-UI-Tests und die Smoke-Test-Anleitung prüfbar.

## Tests

S18-spezifisch:

```bash
python3 -m unittest tests.test_s18_trade_lifecycle_timeline -v
```

Vollständiges Gate:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Die Tests verwenden ausschließlich temporäre, bis V0005 migrierte Kopien der
S00-Fixture. Abgedeckt sind Berlin-Zeit/Sommerzeit/Winterzeit,
Werktagsberechnung, Statuschips, offene/angenommene/versendete/teilweise
empfangene/abgeschlossene Trades, offene und gelöste Probleme,
14-Tage-Hinweis, Tradeboards, Abschlussdatum im Archiv und Legacy-Fallback.

## Nicht enthalten

- Änderungen an Inventory oder Trade-Services,
- neue oder geänderte Lifecycle-Schreiblogik,
- neue Events oder Tabellen,
- Migrationen,
- gespeicherte Fälligkeits- oder Überfälligkeitszustände,
- Feiertagskalender,
- automatische Erinnerungen oder Push-Nachrichten,
- Eskalation, Supportautomation, Chat oder Bewertung.
