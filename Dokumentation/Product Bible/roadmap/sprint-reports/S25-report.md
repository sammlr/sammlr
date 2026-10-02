# S25-Abschlussbericht – Operatives Home V1

Stand: 2026-08-08

## Ziel und Ergebnis

S25 ist vollständig umgesetzt. Home zeigt als read-only operative Projektion
maximal fünf Aufgaben und maximal drei kompakte laufende Lifecycle-Trades. Die
verbindliche Priorisierung, Texte, Eigentümerregeln und stabilen Tie-Breaks
werden zentral durch einen eigenen Read-Service erzeugt. Bei fehlenden Aufgaben
erscheint exakt „Alles erledigt.“; passive laufende Trades dürfen darunter
weiterhin sichtbar bleiben.

S26 wurde nicht begonnen.

## Architektur und Datenfluss

Der neue `OperationalHomeService` liest den aktuellen Fachzustand aus den
bestehenden Request-, Lifecycle-, Shipping-, Receipt-, Problem- und
Notification-Tabellen. Für Smart-Pakete verwendet er den vorhandenen read-only
S22-Recheck. Er erzeugt immutable `HomeTaskDTO`, `HomeTradeSummaryDTO` und
`OperationalHomeDTO` und besitzt keine Schreiboperation.

```text
GET /
→ bestehende deduplizierte S23-Fristprojektion auslösen
→ OperationalHomeService für den Sessionnutzer lesen
→ Fachaufgaben deterministisch sortieren und auf 5 begrenzen
→ laufende Lifecycle-Trades nach letzter Fachänderung sortieren
  und auf 3 begrenzen
→ bestehende interne Detail- und Neuberechnungsziele rendern
```

Der einzige bestehende Seiteneffekt bei `GET /` ist die schon in S23
definierte lazy und deduplizierte Erzeugung fälliger Fristnotifications. Home
markiert keine Notification gelesen und mutiert weder Trade, Smart Request noch
Inventory.

## Aufgabenvertrag

| Priorität | Aufgabe | Eigentümer und Offen-Wahrheit |
| ---: | --- | --- |
| 1 | Versand überfällig | Nutzer mit weiterhin offenem eigenem Versand und bestehender S23-Fristprojektion |
| 2 | Empfang überfällig | Nutzer mit weiterhin offenem eigenem Empfang und bestehender S23-Fristprojektion |
| 3 | Problemfall offen | ausschließlich Empfänger mit realer bestehender Auflösungsaktion |
| 4 | eingehende manuelle Anfrage | Empfänger der offenen manuellen Anfrage |
| 5 | eingehende Smart-Anfrage | Empfänger der offenen Smart-Anfrage |
| 6 | verändertes Smart-Paket | ursprünglicher Absender; bestehender Neuberechnungspfad |
| 7 | obsoletes Smart-Paket | ursprünglicher Absender; bestehender Neuberechnungspfad |
| 8 | eigener offener Versand | betroffene versendende Seite |
| 9 | offener Empfang | betroffene empfangende Seite nach Versand der Gegenseite |

Gleiche Prioritäten werden nach dem ältesten Handlungsbedarf und danach nach
der kleineren stabilen Objekt-ID sortiert. Es gibt keine weitere Gewichtung.
Eine Fristaufgabe ersetzt die entsprechende normale Versand- oder
Empfangsaufgabe.

Alle Titel, Texte und Aktionsnamen entsprechen wörtlich der
Product-Owner-Klärung. Freunde und News verwenden exakt „Freunde kommen später.“
und „Noch keine Sammlr News.“.

## Kompakte laufende Trades

- maximal drei Einträge,
- ausschließlich noch laufende Lifecycle-Trades,
- keine offenen Anfragen sowie keine abgeschlossenen oder fehlgeschlagenen
  Trades,
- offene Problemfälle bleiben sichtbar, solange der Trade läuft,
- neueste fachliche Änderung zuerst,
- bei Zeitgleichheit kleinere Lifecycle-Trade-ID zuerst.

Die Karten enthalten nur Partner, Album, einen aus der bestehenden
Statusdarstellung gewonnenen kompakten Status und den sicheren Detail-Link.
Timeline, Positionen und mutierende Aktionen bleiben in der Tradezentrale.

## Neue Dateien

- `App/services/operational_home.py`
- `tests/test_s25_operational_home.py`
- `Dokumentation/Product Bible/roadmap/s25-operational-home-v1.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S25-report.md`

## Geänderte Dateien

- `App/webapp.py`: Home-Route auf das neue operative Readmodel umgestellt.
- `App/static/style.css`: ausschließlich notwendige responsive Darstellung
  der neuen Home-Karten.
- `tests/test_s04_home_collection_routes.py`: die durch S25 abgelöste alte
  Home-Platzhaltererwartung aktualisiert; die S04-Routentrennung bleibt
  unverändert abgesichert.
- `Dokumentation/Product Bible/roadmap/README.md`: S25-Artefakte verlinkt und
  S26 als nächsten offenen Sprint markiert.

## Unveränderte Komponenten

- Inventory, Shared Availability Snapshot, Coverage und TopMatch,
- Trade-, Reservation-, Shipping-, Receipt- und Problem-Schreiblogik,
- Smart-Request-Erzeugung, Ablauf und Annahme,
- S23-Notification-Typen, Deduplizierung und Fristregeln,
- S24-Historie, Badge und Read-State,
- Datenbankschema und Migrationsdateien,
- Sammlung, Tradezentrale und bestehende S07-/S24-Origin-Sicherheit.

## Testmatrix

Die 14 neuen S25-Tests prüfen:

- leeres Home, „Alles erledigt.“ und ehrliche Platzhalter,
- manuelle Anfrage unabhängig vom Notification-Read-State und ihr fachliches
  Verschwinden,
- normalen und erledigten eigenen Versand,
- normalen und überfälligen Empfang,
- überfälligen Versand ohne doppelte Normalaufgabe,
- Problemaufgabe nur für den Empfänger mit realer Auflösungsaktion,
- eingehende Smart-Anfrage sowie geändertes und obsoletes Smart-Paket nur für
  den jeweils festgelegten Nutzer,
- Priorität, ältesten Handlungsbedarf, stabile Objekt-ID und Fünferlimit,
- maximal drei laufende Trades, Sortierung und Ausschluss offener Anfragen und
  abgeschlossener Trades,
- „Alles erledigt.“ bei weiterhin sichtbarem passivem Trade,
- unveränderten Notification-, Trade-, Lifecycle- und Inventory-Zustand nach
  Home-Aufruf,
- Fremdzielschutz sowie fortbestehende S24-Historie und S07-Home-Rückweg,
- immutable DTOs und unveränderten Migrationsumfang.

## Testbefehle und Ergebnisse

Gezielter Lauf:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s25_operational_home -v
```

Ergebnis: **14 Tests, alle erfolgreich**.

Vollständiges Gate, erster finaler Lauf:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_s*.py' -q
```

Ergebnis: **399 Tests, alle erfolgreich**.

Zweiter finaler Lauf mit demselben Befehl: **399 Tests, alle erfolgreich**.

## HTTP-Smoke-Test

Der Server wurde ohne Code- oder Produktdatenänderung gegen eine isolierte
temporäre Kopie der S00-Fixture gestartet, die ausschließlich für den Test auf
V0006 migriert wurde. Login lieferte HTTP 302 auf Home, `GET /` danach HTTP 200.
Geprüft wurden:

- „Das braucht dich“,
- „Alles erledigt.“,
- „Laufende Trades / Sendungen“,
- „Freunde kommen später.“,
- „Noch keine Sammlr News.“.

Die lokale Entwicklungsdatenbank wurde für den isolierten Smoke-Test nicht
verwendet oder migriert. Anschließend wurde die bereits laufende lokale
Entwicklungsinstanz kontrolliert neu gestartet. Sie verwendet ohne
`DATABASE_PATH`-Override weiterhin den Standardpfad
`/Users/valy/Desktop/sammlr./App/Database/sammlr.db`; ein read-only Abruf von
`/login` lieferte nach dem Neustart HTTP 200.

Der bereits vor S25 vorhandene `init_db()`-Startup pflegt bei jedem App-Start
den bestehenden `wm26`-Albumwert per idempotentem `UPDATE`. Dadurch änderte
sich beim ausdrücklich geforderten Neustart die physische DB-Prüfsumme von
`071e50a6db4d2dc3891c660581d2e828209358feb4a5b543a42e8f9f892a110d`
auf den unten dokumentierten Endwert. Es wurde keine Migration ausgeführt;
Migrationsstand, Schema und fachlicher Wert blieben unverändert. Dieser
vorhandene Startup-Schreibpfad wurde im engen S25-Scope nicht refaktoriert.

## Release Readiness

- Migration: S25 benötigt keine neue Migration. Die lokale Entwicklungs-DB
  steht unverändert auf V0005; nur die temporäre Smoke-/Testkopie lief auf
  V0006.
- Integrität lokale Entwicklungs-DB: `PRAGMA integrity_check` = `ok`.
- Lokale Entwicklungs-DB SHA-256 nach dem geforderten Serverneustart:
  `f2ece9fd5b10cb2d1d52834325aeb2d781eaf1615396361a9bf01035ea17e0b3`.
- Kanonische S00-Fixture SHA-256:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Produktdaten und kanonische Fixture wurden durch die S25-Tests nicht
  verändert; die Tests sichern beide Prüfsummen ab. Der anschließende lokale
  App-Neustart führte ausschließlich den oben transparent dokumentierten,
  bereits vorhandenen `init_db()`-Startup-Pfad aus.
- Vollständiges Gate: beide finalen Läufe jeweils 399/399 grün.
- `git diff --check`: erfolgreich, keine Whitespace-Fehler.
- `PRAGMA foreign_key_check`: keine Befunde.
- Es wurden ausschließlich temporäre Testdaten verwendet.

## Bekannte Grenzen und offene Punkte für S26

- Freunde und Sammlr News bleiben bewusst ehrliche Platzhalter.
- Home besitzt keine Notification-Historie und keine vollständige
  Tradeverwaltung.
- Es gibt keine mutierenden Home-Aktionen, keinen zusätzlichen Feed und keine
  Albumfortschrittswand.
- Weitere Inhalte oder Produktentscheidungen gehören ausschließlich in den
  noch offenen S26 oder spätere Roadmap-Sprints.

## Scope-Bestätigung

- Ausschließlich S25 wurde umgesetzt.
- S26 wurde nicht begonnen.
- Keine Migration wurde hinzugefügt oder auf der lokalen Entwicklungsdatenbank
  ausgeführt.
- Keine Inventory-, Trade-, Versand-, Empfangs-, Problem-, Snapshot-, Coverage-
  oder Notification-Fachlogik wurde verändert.
- Kein Commit wurde erstellt.
- Kein Push wurde durchgeführt.
