# S28-Abschlussbericht – Qualifizierte Tradebewertungen und Vertrauen

Stand: 2026-08-08

## Ziel und Ergebnis

S28 ist vollständig umgesetzt. Ausschließlich terminal abgeschlossene
Lifecycle-Trades (`completed`, `closed_with_problem` und
`problem_resolved_after_close`) können auf ihrer bestehenden Dealansicht mit
1–5 Sternen bewertet werden. Beide Beteiligten bewerten unabhängig und je Trade genau
einmal. Die endgültige Bewertung ist weder änderbar noch löschbar.

Das eigene und das fremde Profil zeigen ausschließlich den Durchschnitt der
empfangenen Bewertungen mit einer Nachkommastelle und deren Anzahl. Ohne
Bewertung erscheint exakt „Noch keine Bewertungen“. Einzelbewertungen werden
nicht veröffentlicht. Die bestehende Kennzahl „Erfolgreiche Trades“ bleibt
fachlich und technisch unabhängig.

## Architektur

### Persistenz und Migration V0008

V0008 ergänzt die normalisierte Tabelle `trade_ratings` mit:

- kanonischer Lifecycle-Trade-ID,
- Rater-Nutzer-ID,
- bewerteter Nutzer-ID,
- ganzzahliger Sternezahl von 1 bis 5,
- Erstellungszeitpunkt.

`UNIQUE (trade_id, rater_user_id)` erzwingt die einmalige Bewertung je Nutzer
und Trade transaktional. Ein zweiter Constraint auf Trade und bewerteten Nutzer
schützt zusätzlich die zwei zulässigen Bewertungsrichtungen. Check Constraints
verhindern Werte außerhalb 1–5 und Selbstbewertungen. Der Foreign Key verweist
ausschließlich auf den Lifecycle-Trade; reine Legacy-Requests sind damit kein
Bewertungsziel.

Datenbank-Trigger verhindern zusätzlich jedes `UPDATE` und `DELETE` einer
gespeicherten Bewertung. Die Endgültigkeit ist damit auch unterhalb der
Service- und Routenschicht abgesichert.

Die Down-Migration arbeitet fail-closed: Sind Bewertungsdaten vorhanden, wird
die Tabelle nicht automatisch gelöscht. Ein datenloser Backout ist geprüft.

### Service und DTOs

Der neue `TradeRatingService` kapselt:

- Lifecycle- und Teilnehmerqualifikation,
- Auflösung der bestehenden Legacy-Deal-URL auf den kanonischen
  Lifecycle-Trade,
- das einmalige transaktionale Speichern,
- den Bewertungsstatus für die Dealansicht,
- die read-only Profilaggregation.

Immutable DTOs liefern stabile Ergebniszustände und Profilwerte. Die
Aggregation verwendet `Decimal` und kaufmännisches Runden (`ROUND_HALF_UP`) auf
eine Nachkommastelle.

Strukturierte Gründe sind ausschließlich technisch vorbereitet: Die stabile
Rating-ID bildet eine spätere referenzielle Erweiterungsnaht. S28 führt bewusst
keine Reason-Spalte, Speicherung, UI oder Fachlogik dafür ein.

## Datenfluss

```text
GET Dealansicht
→ bestehende Objektberechtigung
→ Lifecycle-Trade auflösen
→ completed + unbewertet: Bewertungsformular
→ completed + bewertet: finaler Hinweis
→ nicht completed: keine Bewertungsaktion

POST Bewertung
→ Sterne strikt validieren
→ Lifecycle und Teilnehmer in BEGIN IMMEDIATE erneut prüfen
→ Gegenseite serverseitig ableiten
→ einmaliges INSERT
→ bestehende Dealansicht erneut öffnen

GET eigenes/fremdes Profil
→ CollectorProfileService
→ TradeRatingService.summary_for_user
→ nur Durchschnitt und Anzahl rendern
```

Der POST erzeugt keine Notification, kein Lifecycle-Event und keine
Inventory-, Reservation-, Versand-, Empfangs- oder Problemmutation.

## Neue Dateien

- `App/Database/migrations/0008_trade_ratings.up.sql`
- `App/Database/migrations/0008_trade_ratings.down.sql`
- `App/services/trade_ratings.py`
- `tests/test_s28_trade_ratings.py`
- `Dokumentation/Product Bible/roadmap/s28-trade-ratings.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S28-report.md`

## Geänderte Dateien

- `App/webapp.py`: Bewertungsdarstellung auf der abgeschlossenen Dealansicht,
  genau eine Rating-POST-Route und reine Profilaggregation.
- `App/services/collector_profiles.py`: Rating-Durchschnitt und Anzahl im
  bestehenden Profil-DTO; erfolgreiche Trades unverändert.
- `App/static/style.css`: ausschließlich minimale Darstellung für Ratingform
  und Profilaggregation.
- `tests/test_s26_collector_profiles.py`: erwartete neueste Migration auf
  V0008 angehoben; S26-Zielversion bleibt V0006.
- `tests/test_s27_album_privacy_trade_pool.py`: erwartete neueste Migration auf
  V0008 angehoben; S27-Zielversion bleibt V0007.
- `Dokumentation/Product Bible/roadmap/README.md`: S28-Spezifikation und Report
  verlinkt; S29 lediglich als nächster offener Sprint bezeichnet.

## Unveränderte Komponenten

- Inventory Read/Write, Guard, Availability und Shared Snapshot,
- Coverage, TopMatch und Smart Requests,
- Trade Lifecycle, Reservierungen, Versand, Empfang und Problembehandlung,
- Notification-Typen, Historie, Deduplizierung und Badge,
- Operational Home,
- Albumprivacy und Tradepool,
- Tradearchiv und erfolgreiche-Trade-Zählung,
- lokale Entwicklungsdatenbank und kanonische S00-Fixture.

## Testmatrix

| Bereich | Abdeckung | Ergebnis |
|---|---|---|
| V0008 | Fixture-Up, bestehender completed Lifecycle-Trade, No-op, leerer Down/Up, fail-closed Backout | grün |
| Qualifikation | completed, offen, reine Legacy-Zeile, gelöster Problemfall | grün |
| Finalität | genau einmal je Richtung, Retry, keine Update-/Delete-Route, DB-Trigger gegen Update/Delete | grün |
| Sicherheit | Beteiligung, Fremdnutzer, serverseitige Gegenseite, Sterne 1–5, DB-Constraints | grün |
| Gegenseitigkeit | unabhängige Bewertungen beider Seiten | grün |
| Aggregation | Durchschnitt, 4,7-Rundung, Anzahl, sofortige Aktualisierung | grün |
| Profile | eigenes/fremdes Profil, Leerzustand, keine Einzelrating-Daten | grün |
| Seiteneffekte | keine Notification, Rating-Reads und Profile read-only | grün |
| Bestehende Kennzahl | erfolgreiche Trades unabhängig von Ratings | grün |
| Regression | vollständige S01–S28-Suite zweimal | grün |

## Testbefehle und Ergebnisse

S28-spezifisch:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s28_trade_ratings -v
```

Ergebnis: **9 Tests in 0,081 s, 0 Fehler**.

Der vorgegebene Mustername `tests.test_s28_*` wird von der Shell nicht als
Python-Modulname aufgelöst; deshalb wurde das konkrete S28-Modul ausgeführt.

Vollständiges Gate, Lauf 1:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

Ergebnis: **428 Tests in 4,526 s, 0 Fehler**.

Vollständiges Gate, Lauf 2 mit demselben Befehl:

Ergebnis: **428 Tests in 4,566 s, 0 Fehler**.

Syntaxprüfung mit isoliertem Bytecode-Cache: erfolgreich.

## Release Readiness

- Eine isolierte Kopie der kanonischen S00-Fixture wurde mit dem bestehenden
  Runner bis V0008 migriert: `(1, 2, 3, 4, 5, 6, 7, 8)`.
- Ein zweiter Up-Lauf bis V0008 war ein No-op: `()`.
- Temporäre Zielversion: V0008.
- Beide Unveränderlichkeitstrigger waren in V0008 vorhanden.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: keine Befunde.
- Die temporäre Release-Check-Datenbank wurde danach entfernt.
- Die lokale Entwicklungsdatenbank wurde nicht migriert und bleibt auf V0007.
- SHA-256 lokal: `091429b526592cd64f544f0d9a0ab6a751e293e5076c3b54263c19667948799f`.
- SHA-256 S00-Fixture: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Lokale Integritätsprüfung: `ok`; Foreign-Key-Check ohne Befund.
- `git diff --check`: erfolgreich.
- Es wurden ausschließlich temporäre Testdaten verwendet.

Die Anwendung benötigt vor einem manuellen S28-Smoke-Test eine separat
beauftragte, gesicherte lokale Migration auf V0008. Diese wurde im Sprint nicht
vorgezogen.

## Bekannte Grenzen und offene Punkte für S29

- Strukturierte Bewertungsgründe besitzen bewusst noch keine Speicherung,
  Darstellung oder Produktlogik.
- Es gibt bewusst keine Liste einzelner Bewertungen und keinen Freitext.
- Bewertungen beeinflussen weder Ranking noch Smart Matches.
- Die lokale Entwicklungsdatenbank steht weiterhin auf V0007; dies ist kein
  Migrationsfehler und wurde nicht eigenmächtig verändert.
- S29 wurde nicht analysiert, vorbereitet oder begonnen.

## S18.2-Integrationsnachtrag

Die spätere S18.2-Lifecycle-Härtung erweitert die Qualifikation kontrolliert um
`closed_with_problem` und `problem_resolved_after_close`. Eine vor der
nachträglichen Problemlösung gespeicherte Bewertung bleibt durch denselben
Unique-/Triggervertrag endgültig. Die eigene Bewertung wird zeitgestempelt in
der beteiligten Deal-Timeline sichtbar; Profile zeigen weiterhin ausschließlich
Aggregation und Anzahl. Es entstanden weder neue Ratingfelder noch
Notifications.

## Scope- und Abschlussbestätigung

- Ausschließlich S28 wurde umgesetzt.
- S29 wurde nicht begonnen.
- Keine fachliche Änderung an S17–S27, Inventory, Lifecycle, Snapshot,
  Coverage, TopMatch, Smart Requests, Versand, Empfang, Problemen oder
  Notifications.
- Keine neue Notification und kein neuer S23-Typ.
- Keine lokale Produktdatenbank und keine kanonische Fixture migriert.
- Kein Commit erstellt.
- Kein Push durchgeführt.
