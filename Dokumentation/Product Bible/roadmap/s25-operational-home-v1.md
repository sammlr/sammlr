# S25 – Operatives Home V1

Stand: 2026-08-08

## Ziel

Home beantwortet ausschließlich zwei Fragen:

- „Was braucht mich?“ durch maximal fünf fachlich offene Aufgaben.
- „Was ist passiert?“ durch maximal drei kompakte laufende Lifecycle-Trades.

Home ist eine read-only Projektion. Trade Lifecycle, Notifications, Inventory
und Smart Requests bleiben fachliche Besitzer. Es entstehen keine zweite
State-Machine, keine zweite Fristberechnung und keine mutierenden Home-Aktionen.

## Verbindliche Invarianten

- Notification gelesen bedeutet nicht, dass eine Fachaufgabe erledigt ist.
- Aufgaben werden ausschließlich aus aktuellem Fachzustand abgeleitet.
- Eine Aufgabe verschwindet genau dann, wenn die zugrunde liegende eigene
  Handlung nicht mehr offen ist.
- Home markiert keine Notification gelesen und verändert weder Trade noch
  Inventory.
- S23-Fristwahrheit wird über die vorhandene lazy Projektion und deren
  typisierte Fristnotifications wiederverwendet; Home berechnet keine Frist.
- Jede Aufgabe verweist ausschließlich auf ein bestehendes, autorisiertes
  Fachobjekt oder einen bestehenden Smart-Neuberechnungspfad.
- Home enthält keine mutierende Tradeaktion.
- Fremde Objekte und Ziele werden nie in das Readmodel aufgenommen.
- Es gibt keine Notification-Historie, vollständige Tradezentrale oder
  Albumfortschrittswand auf Home.

## Architektur

### `OperationalHomeService`

Ein neuer isolierter Read-Service erzeugt zwei immutable Projektionen:

1. operative Aufgaben für den aktuellen Nutzer,
2. kompakte laufende Lifecycle-Trades des aktuellen Nutzers.

Der Service erhält eine bestehende Datenbankverbindung, liest ausschließlich
bestehende Tabellen und ruft für Smart-Konflikte nur eine bestehende oder
minimal freigelegte read-only S22-Projektion auf. Er besitzt keine Commit-,
Insert-, Update- oder Delete-Operation.

### DTOs

- `HomeTaskDTO`
  - Typ,
  - Priorität,
  - verbindlicher Titel, Text und Aktionsname,
  - kanonischer interner Zielpfad,
  - fachlicher Offen-Grund,
  - Zeitpunkt des Handlungsbedarfs,
  - stabile Objekt-ID.
- `HomeTradeSummaryDTO`
  - Lifecycle- und Legacy-Request-ID,
  - Partner,
  - Album,
  - vorhandener Lifecycle-Zustand,
  - Zeitpunkt der letzten fachlichen Änderung,
  - kanonischer Detailpfad.
- `OperationalHomeDTO`
  - höchstens fünf Aufgaben,
  - höchstens drei laufende Trades.

Alle DTOs sind immutable.

## Datenfluss

```text
GET /
→ vorhandene S23-lazy Fristprojektion einmal aufrufen
→ OperationalHomeService für Sessionnutzer lesen
→ Aufgaben aus Fachzuständen ableiten
→ laufende Lifecycle-Trades kompakt projizieren
→ bestehende Statusdarstellung für kompakte Labels wiederverwenden
→ read-only Home rendern
```

Der erlaubte S23-Aufruf kann ausschließlich idempotente, deduplizierte
Fristnotifications erzeugen. Er markiert nichts gelesen und verändert keinen
Fachzustand. Das Home-Readmodel selbst bleibt ohne Schreibpfad.

## Aufgabenmatrix

| Priorität | Typ | Fachliche Offen-Wahrheit | Nutzer | Ziel |
| ---: | --- | --- | --- | --- |
| 1 | Versand überfällig | bestehende S23-Notification `trade_shipping_overdue` plus weiterhin eigener Versand offen | betroffene versendende Seite | Trade mit `origin=home` |
| 2 | Empfang überfällig | bestehende S23-Notification `trade_receipt_overdue` plus weiterhin eigener Empfang offen | betroffene empfangende Seite | Trade mit `origin=home` |
| 3 | Problemfall offen | offener Report und bestehende eigene Auflösungsaktion | ausschließlich berechtigter Empfänger | Trade mit `origin=home` |
| 4 | manuelle Anfrage | eingehender Request `open`, nicht Smart | Empfänger | Request mit `origin=home` |
| 5 | Smart-Anfrage | eingehender Smart-Request mit eigener Reaktionsmöglichkeit | Empfänger | Request mit `origin=home` |
| 6 | Smart-Paket geändert | bestehende read-only S22-Recheck-Wahrheit `package_changed` | ursprünglicher Absender | bestehende albumbezogene Smart-Neuberechnung |
| 7 | Smart-Paket obsolet | vorhandener Zustand `obsolete` | ursprünglicher Absender | bestehende albumbezogene Smart-Neuberechnung |
| 8 | Versand steht aus | laufender Lifecycle-Trade, eigener Versand offen, nicht bereits als überfällig projiziert | betroffene versendende Seite | Trade mit `origin=home` |
| 9 | Sendung unterwegs | Gegenseite versendet, eigener Empfang offen, kein eigener aktiver Problemfall und nicht bereits überfällig | betroffene empfangende Seite | Trade mit `origin=home` |

Eine fachliche Situation erzeugt für denselben Nutzer und dieselbe Handlung
nur die höchstpriorisierte passende Aufgabe. Insbesondere ersetzt
„überfällig“ die normale offene Versand- beziehungsweise Empfangsaufgabe.

## Priorisierung

1. feste Product-Owner-Priorität aufsteigend von 1 bis 9,
2. innerhalb derselben Priorität ältester Handlungsbedarf zuerst,
3. danach kleinere stabile Objekt-ID.

Nach dieser deterministischen Sortierung werden genau die ersten fünf Aufgaben
angezeigt. Es gibt keine weitere Gewichtung.

## Verbindliche Texte

| Typ | Titel | Text | Aktion |
| --- | --- | --- | --- |
| Versand überfällig | Versand überfällig | Bitte bestätige den Versand deiner Sticker. | Zum Trade |
| Empfang überfällig | Empfang bestätigen | Die Sendung der Gegenseite ist seit längerem unterwegs. | Zum Trade |
| Problemfall | Problemfall offen | Bei diesem Trade ist noch eine Lieferung offen. | Problem ansehen |
| manuelle Anfrage | Neue Tauschanfrage | Jemand möchte mit dir tauschen. | Anfrage ansehen |
| Smart-Anfrage | Neue Smart-Anfrage | Du hast eine neue Smart-Trade-Anfrage. | Smart-Anfrage ansehen |
| Smart geändert | Smart-Paket hat sich geändert | Das vorgeschlagene Paket ist nicht mehr vollständig verfügbar. | Neu berechnen |
| Smart obsolet | Smart-Paket nicht mehr verfügbar | Dieses Smart-Paket kann nicht mehr ausgeführt werden. | Neu berechnen |
| Versand offen | Versand steht aus | Deine Sticker wurden noch nicht als versendet bestätigt. | Versand bestätigen |
| Empfang offen | Sendung unterwegs | Du kannst den Empfang bestätigen, sobald die Sticker angekommen sind. | Zum Trade |

## Kompakte laufende Trades und Sendungen

Die Projektion enthält ausschließlich Lifecycle-Trades, deren Fachvorgang noch
läuft. Ausgeschlossen sind:

- offene, noch nicht angenommene Anfragen,
- abgeschlossene oder gescheiterte Trades,
- reine Legacy-Anfragen ohne Lifecycle-Trade.

Problemfälle bleiben enthalten, solange der Trade läuft. Sichtbar sind nur
Partner, Album, kompakter vorhandener Status und der sichere Detail-Link.
Timeline, Stickerpositionen und mutierende Aktionen bleiben in der
Tradezentrale.

Sortierung:

1. letzte vorhandene fachliche Änderung absteigend,
2. bei Gleichstand kleinere Lifecycle-Trade-ID.

Danach werden maximal drei Einträge angezeigt.

## Deep-Link-Regeln

- Trade- und Request-Aufgaben verwenden ausschließlich
  `/trades/<legacy-request-id>?origin=home`.
- Der bestehende S07-Rückweg `home → Trade → Home` bleibt unverändert.
- Smart-Neuberechnung verwendet ausschließlich den vorhandenen
  albumbezogenen Smart-Pfad.
- Kein Ziel wird aus einem frei übergebenen Request-Parameter übernommen.
- Keine externe URL und kein allgemeiner Navigation-Stack.

## Trennung von Aufgabe und Notification

S23-/S24-Notifications können gelesen oder ungelesen sein. Dieser Zustand
beeinflusst keine Home-Aufgabe. Fristnotifications dienen lediglich als bereits
zentral projizierte Fristwahrheit; der aktuelle Lifecycle-Zustand wird vor der
Aufnahme erneut geprüft. Eine historische Fristnotification erzeugt daher nach
Versand oder Empfang keine erledigte Aufgabe erneut.

## Home-Darstellung

1. **Das braucht dich** – maximal fünf Aufgaben oder exakt „Alles erledigt.“
2. **Laufende Trades und Sendungen** – maximal drei kompakte Vorgänge.
3. **Freunde** – exakt „Freunde kommen später.“
4. **Sammlr News** – exakt „Noch keine Sammlr News.“

Passive laufende Trades dürfen unter „Alles erledigt.“ sichtbar bleiben.

## Read-/Write-Pfade und Seiteneffekte

Read-only:

- aktuelle Requests, Lifecycle-, Versand-, Empfangs- und Problemzustände,
- S22-Smart-Recheck als reine Projektion,
- vorhandene S23-Fristnotification,
- Partner-, Album- und Zeitinformationen.

Bestehender erlaubter Seiteneffekt:

- S23 `ensure_overdue(...)` erzeugt deduplizierte Fristnotifications.

Nicht erlaubt:

- Notification-Read-State ändern,
- Trade, Smart Request, Lifecycle oder Inventory ändern,
- Fristen neu berechnen,
- Home-Aktionen ausführen,
- neue Typen, Zustände, Tabellen oder Migrationen.

## Betroffene Komponenten

- neuer Operational-Home-Read-Service,
- bestehende Home-Route `/`,
- bestehende kompakte Statusprojektionen,
- S22 read-only Smart-Recheck, falls für Home minimal als reine Abfrage
  freizulegen,
- S25-Tests und Dokumentation.

## Unveränderte Komponenten

- S23-/S24-Notification-Historie, Badge, Typen und Deduplizierung,
- S07-/S24-Origin-Kontexte und Sicherheitsfallbacks,
- Inventory, Snapshot, Coverage und TopMatch,
- Smart-Erzeugung, Ablauf und Annahme,
- Reservation, Shipping, Receipt und Problems,
- alle Trade-Schreibpfade,
- Sammlung unter `/sammlung`,
- Freunde-, Community- und Newslogik.

## Risiken und Gegenmaßnahmen

- **Notification mit Aufgabe verwechselt:** Aufgaben prüfen ausschließlich
  Fachzustände; `is_read` wird nie gelesen.
- **Frist doppelt berechnet:** ausschließlich bestehende S23-Projektion und
  Fristtypen verwenden.
- **Smart-Recheck mutiert:** nur reine S22-Leseprojektion zulassen.
- **Fremdziel:** alle Queries auf Beteiligung beziehungsweise Empfänger
  begrenzen.
- **Home wird zweite Tradezentrale:** maximal drei kompakte Einträge ohne
  Timeline, Positionen oder Aktionen.
- **instabile Reihenfolge:** feste Priorität, ältester Bedarf, stabile ID.

## Testvertrag

Getestet werden Alles-erledigt, manuelle und Smart-Anfragen, gelesene
Notification bei offener Aufgabe, Erledigung, Versand/Empfang offen und
überfällig, eigener Problemfall, Smart geändert/obsolet, maximale Anzahl und
deterministische Sortierung, drei kompakte Trades, keine Home-Mutation,
Fremdzielschutz, ehrliche Platzhalter, Sammlung/Tradezentrale,
Notification-Historie und bestehende Origin-Kontexte sowie die vollständige
S01–S25-Regression.

## Nicht enthalten

- S26,
- Friend Feed, Freundesaktivitäten oder Community,
- echte Sammlr-News oder Redaktion,
- neue Notification-Typen,
- Albumfortschrittsdashboard,
- vollständige Tradeverwaltung oder Timeline,
- Push, Bewertung, Animationen oder allgemeiner Design-Patch.
