# Sprintbericht S14 – Annahme erzeugt verbindliche Reservierungen

Stand: 2026-08-02

## Ergebnis

Sprint S14 wurde ausschließlich im vorgesehenen Umfang umgesetzt. Auf einer
explizit bis V0002 migrierten Datenbankkopie erzeugt die Annahme einer offenen
Legacy-Tradeanfrage atomar:

- genau einen Lifecycle-Trade,
- aggregierte gerichtete Tradepositionen für beide Seiten,
- genau eine aktive Reservierung je Position,
- den bestehenden Legacy-Status `accepted`,
- die bestehende Annahme-Notification genau einmal.

Unmittelbar vor dem Schreiben werden sämtliche Positionen innerhalb derselben
`BEGIN IMMEDIATE`-Transaktion erneut über den zentralen Inventory Read Service
geprüft. Scheitert eine Position oder Nebenwirkung, wird die gesamte Annahme
einschließlich Lifecycle-Daten, Status und Notification zurückgerollt.

Anfragen reservieren weiterhin nichts. Es wurden keine Versand-, Empfangs-,
Transit-, Problem- oder dynamischen Paketzustände umgesetzt.

## Neue Dateien

- `App/Database/migrations/0002_trade_reservations.up.sql`
  - versioniertes Reservierungsschema mit Constraints und Indizes
- `App/Database/migrations/0002_trade_reservations.down.sql`
  - fail-closed Backout auf V0001
- `App/services/trade_reservations.py`
  - atomarer Acceptance-/Reservation-Service
  - stabile Ergebnis-DTOs und Fehlercodes
  - aktive Bindungsquelle für den Inventory Guard
  - idempotente Freigabe
- `tests/test_s14_trade_reservations.py`
  - S14-Migrations-, Service-, Route-, Konkurrenz- und Regressionstests
- `Dokumentation/Product Bible/roadmap/s14-trade-reservations.md`
  - verbindlicher Reservierungs-, Transaktions- und Backout-Vertrag
- `Dokumentation/Product Bible/roadmap/sprint-reports/S14-report.md`
  - dieser Sprintbericht

## Geänderte Dateien

- `App/services/inventory_availability.py`
  - zentrale Projektion um tatsächliche aktive Reservierungsmenge ergänzt
- `App/services/inventory.py`
  - Read Service aggregiert aktive Reservierungen, sofern V0002 installiert ist
- `App/services/inventory_write.py`
  - reale aktive S14-Bindungen an den bestehenden S12-Guard angeschlossen
- `App/services/inventory_guard.py`
  - Erklärung von „simuliert gebunden“ auf den nun allgemeinen Begriff
    „gebunden“ präzisiert; Codes und Entscheidungslogik unverändert
- `App/webapp.py`
  - migrierte Annahmen an den atomaren Service delegiert
  - bestehende Annahme-Notification innerhalb der Transaktion erhalten
  - Freigabe vor bestehendem Abschluss beziehungsweise bei bestehendem
    `failed`-Ende angebunden
  - Legacy-Annahmepfad für noch nicht migrierte Datenbanken erhalten
- `tests/test_s13_trade_lifecycle_schema.py`
  - S13-Vertrag explizit auf Zielversion V0001 fixiert, damit spätere
    Migrationen den abgeschlossenen S13-Testumfang nicht stillschweigend ändern
- `Dokumentation/Product Bible/roadmap/README.md`
  - ausschließlich Verweise auf S14-Spezifikation und Bericht ergänzt

Weitere bereits vorhandene Änderungen im Arbeitsverzeichnis wurden weder S14
zugerechnet noch zurückgesetzt. Insbesondere ist die vorhandene Änderung an
`App/static/style.css` keine S14-Änderung.

## Reservierungsmodell und Constraints

V0002 ergänzt `trade_reservations` mit:

- FK zum Lifecycle-Trade,
- eindeutigem FK zur Tradeposition,
- abgebendem Nutzer,
- Album und Stickercode,
- positiver Menge (`quantity > 0`),
- Zustand ausschließlich `active` oder `released`,
- Erstellungszeitpunkt,
- gekoppelten Freigabefeldern `released_at` und `release_reason`.

Eine aktive Reservierung darf keine Freigabeangaben besitzen; eine freigegebene
Reservierung muss beide Angaben besitzen. Die eindeutige Position verhindert
duplizierte Reservierungen für denselben Paketbestand.

## Modellverbindung

```text
Legacy trade_requests
  └── Lifecycle trades (legacy_trade_request_id UNIQUE)
        ├── trade_positions (Richtung, Album, Code, positive Menge)
        └── trade_reservations (Position UNIQUE, Abgeber, Menge, Zustand)
```

Bestehende `trade_requests`-Zeilen und JSON-Pakete bleiben unverändert lesbar.
Es wurde kein historischer Backfill durchgeführt. Ein Lifecycle-Trade entsteht
ausschließlich bei einer neuen, erfolgreichen S14-Annahme.

## Transaktionsgrenze und Recheck

Die gemeinsame Transaktion umfasst:

1. Berechtigung und aktuellen Legacy-Status prüfen.
2. Paket unverändert zu Positionen aggregieren.
3. Lifecycle-Trade bestimmen.
4. aktuelle Availability aller Positionen lesen.
5. alle Positionen speichern.
6. alle Reservierungen speichern.
7. Legacy-Status auf `accepted` setzen.
8. bestehende Annahme-Notification erzeugen.
9. gemeinsam committen.

Der Recheck vertraut weder Anfragezeitpunkt noch Matching-Snapshot. Er liest
`physical`, `assigned`, aktive `reserved` und daraus `available` unmittelbar
innerhalb derselben schreibsperrenden SQLite-Transaktion.

## Availability und Matching

Auf V0002 gilt zentral:

```text
available = max(physical - assigned - reserved, 0)
reservable = available
```

Aktive Reservierungen reduzieren nur `available`/`reservable`. Physical,
`stickers.quantity`, `stickers.duplicates`, assigned, gesammelte Sticker und
Albumfortschrittsprozent werden bei Annahme nicht geändert. Matching verwendet
den zentralen Read Service und bietet reservierte Kopien nicht erneut an.

Der Inventory Guard verhindert auf migrierten Datenbanken, dass eine manuelle
Mengenänderung die für aktive Reservierungen notwendige physische Menge
unterschreitet. Ohne aktive Reservierung bleibt das bisherige Verhalten erhalten.

## Idempotenz und Konkurrenz

Eine wiederholte Annahme liefert `ALREADY_ACCEPTED` und erzeugt weder Lifecycle-
Trade, Position, Reservierung noch Notification erneut.

`BEGIN IMMEDIATE` serialisiert konkurrierende Annahmen vor dem Recheck. Der
automatisierte Zwei-Verbindungs-Test belegt: Benötigen zwei offene Trades
dieselbe letzte freie Kopie, wird genau einer angenommen. Der andere liefert
`INSUFFICIENT_AVAILABLE`, bleibt `open` und besitzt keinerlei Teilreservierung.

## Freigaberegel

Nur bestehende zulässige Enden wurden angebunden:

- `accepted → failed`: aktive Reservierungen werden einmalig mit `failed`
  freigegeben; kein Bestand wird gebucht.
- `accepted → completed`: aktive Reservierungen werden einmalig mit `completed`
  freigegeben; anschließend bucht der bestehende Abschlussalgorithmus den
  Bestand weiterhin genau einmal.

Die Freigabe aktualisiert ausschließlich `state='active'`. Wiederholungen sind
No-ops. Eine Ablehnung aus `open` benötigt keine Freigabe, weil vor Annahme
keine Reservierung existiert.

## Stabile Ergebniszustände

- `ACCEPTED`
- `ALREADY_ACCEPTED`
- `INSUFFICIENT_AVAILABLE`
- `INVALID_TRADE_STATE`
- `UNAUTHORIZED`
- `TRANSACTION_ERROR`

Alle Zustände sind UI-neutrale String-Enums in einem unveränderlichen DTO. Die
bestehende Route verwendet nur schlichte Redirect-Meldungen und enthält keine
neue Oberfläche.

## Migration und Backout

Vorwärtsmigration wurde auf einer leeren temporären Datenbank und auf jeder
temporären Fixture-Kopie geprüft. Ein wiederholter Lauf ist ein No-op.

Der Down-Pfad auf V0001 ist fail-closed:

- ohne Reservierungszeilen wird V0002 verlustfrei entfernt,
- sobald Reservierungshistorie existiert, verhindert ein Constraint den
  Backout und erhält Tabelle, Ledger und Daten vollständig.

Nach echter Nutzung ist daher ein eigener versionierter Export-/Recovery-Schritt
erforderlich; S14 löscht keine Reservierungshistorie beiläufig.

## Testübersicht

S14-spezifischer Testbefehl:

```text
python3 -m unittest tests.test_s14_trade_reservations -v
```

Ergebnis: 21 von 21 Tests erfolgreich.

Geprüft wurden:

1. Anfrage allein reserviert nichts.
2. Gültige Annahme reserviert beide ausgehenden Seiten vollständig.
3. Available und reservable werden korrekt reduziert.
4. Physical, assigned und Albumfortschritt bleiben unverändert.
5. Matching bietet reservierte Kopien nicht erneut an.
6. Fehlender Bestand verhindert die gesamte Annahme.
7. Positionskonflikt erzeugt keine Teilreservierung.
8. Wiederholte Annahme ist idempotent.
9. Konkurrierende Annahmen können dieselbe Kopie nicht beide reservieren.
10. Unberechtigter Zugriff erzeugt keine Reservierung.
11. Ungültiger Zustand erzeugt keine Reservierung.
12. `failed` gibt Reservierungen genau einmal frei.
13. Bestehender `completed`-Flow gibt frei und bucht Bestand genau einmal.
14. Inventory Guard schützt aktiv gebundene Überschusskopien.
15. Technischer Nebenwirkungsfehler rollt alles zurück.
16. Alle stabilen Codes sind vollständig und UI-neutral.
17. Migration auf leerer DB, Wiederholung und leerer Backout funktionieren.
18. Fixture-Backout erhält den Legacy-`completed`-Trade und JSON-Pakete.
19. Backout mit Historie scheitert sicher und verlustfrei.
20. Annahme-Notification erfolgt einmal; Trophäen bleiben unverändert.
21. Produktivdatenbank und kanonische Fixture bleiben unverändert.

Vollständiges Gate, zweimal ausgeführt:

```text
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Abschlusslauf 1: 175 von 175 Tests erfolgreich (`OK`).
- Abschlusslauf 2: 175 von 175 Tests erfolgreich (`OK`).

## Schutz der kanonischen Datenbanken

Vor und nach den Abschlussläufen waren die Prüfsummen identisch:

- `App/Database/sammlr.db`:
  `a6751d5324fe7a598f8f461efcc7ea8d8c3035dce9b8f6261b6b84fad3cc0abd`
- `App/Database/sammlr_reference_s00.db`:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`

Migration und Backout liefen ausschließlich gegen temporäre leere Datenbanken
oder temporäre Kopien. Die bereits im Arbeitsverzeichnis vorhandene
benutzerverwaltete Änderung an `sammlr.db` wurde weder migriert noch
zurückgesetzt.

`git diff --check` war ohne Befund.

## Bewusst offene Punkte für S15+

Nicht begonnen oder vorbereitet wurden:

- Versandstatus und getrennte Versandzeitpunkte,
- ausgehender oder eingehender Transit,
- Empfang und Teilempfang,
- Tracking oder Versandprodukte,
- Problemfälle und Konfliktentscheidung,
- dynamische Paketänderung und erneute Zustimmung,
- Chat, Bewertung oder Smart Trader 2.0,
- neue Home- oder Notification-UI,
- Design Patch.

## Scope-Bestätigung

- Ausschließlich Sprint S14 wurde umgesetzt.
- Sprint S15 wurde nicht begonnen.
- Es wurden keine Versand- oder Empfangszustände umgesetzt.
- Es wurde keine dynamische Paketanpassung umgesetzt.
- Es wurden keine neuen Notificationtypen ergänzt.
- Es wurden keine UI- oder CSS-Änderungen für S14 vorgenommen.
- Bestehende Tradehistorie, JSON-Pakete, Papierlisten- und Abschlussflows blieben
  kompatibel.
- Produktivdatenbank und kanonische Fixture wurden nicht migriert oder verändert.
- Es wurde kein Commit erstellt und kein Push durchgeführt.
