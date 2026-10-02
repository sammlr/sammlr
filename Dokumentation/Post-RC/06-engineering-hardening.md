# Engineering Hardening

## Zweck

Dieses Dokument bündelt in Phase 7 Performance, Runtime, Datenbank, Browser-E2E und andere technische RC-Blocker.

## Abgrenzung

Engineering Hardening enthält keine Produkt-Auditentscheidungen, UX-Architektur, visuellen Designregeln oder allgemeinen UI-Aufgaben.

## Status

**Abgeschlossen und technisch abgenommen am 21. August 2026.** Der frühere
P0-Regressionsfix und alle CB-001–017-Verträge bleiben grün. Die übernommenen
S35-Performanceblocker sind geschlossen; Security-, Datenbank-, Runtime-,
Migration-/Restore- und Regressiongates sind bestanden. Externe Nutzer werden
daraus noch nicht freigegeben. Vollständiger Nachweis:
`04-implementation-reports/Phase-7-engineering-hardening-report.md`.

## Phase-7-Ergebnis

- Die verbindliche S35-Baseline mit einem Gunicorn-Worker, 20 Threads und 20
  parallelen Requests besteht auf allen zehn Pfaden mit `P95 < 500 ms` und
  `0` Fehlern.
- Markt-, Collection- und Community-Reads sind gebündelt; die beiden
  SQLite-intensiven Übersichtsprojektionen vermeiden im verbindlichen
  Ein-Worker-Betrieb konkurrierendes Read-Thrashing.
- Gespeicherte Profilwerte werden auch in HTML-Attributen escaped. Body-,
  Form-, Query- und persistierte Identitätseingaben besitzen serverseitige
  Obergrenzen.
- Runtime-Verbindungen aktivieren Foreign Keys. Responses besitzen die
  passenden Basissicherheitsheader. Der direkte Development-Start ist auf
  Loopback ohne Debugger beschränkt; requestbezogene Debug-Ausgaben sind
  entfernt.
- Zwei vollständige Regressionen bestehen mit jeweils `712/712`, `0` Fehlern
  und `0` Skips. Die echte Bestandsdatenbank bleibt auf V7 und besitzt weiterhin
  SHA-256 `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`.
- Nächster zulässiger Schritt ist Phase 8 – Realistic Simulation.

## CB-001 – verbindlicher Migrationsvertrag ab V0013

- V0013 ist die erwartete Runtime-Schemaversion und enthält ausschließlich den
  additiven historischen Sammlungs-Datenvertrag; es findet kein Backfill statt.
- Up- und Down-Migrationen laufen als atomare DDL-Einheit. Besitzt der Aufrufer
  bereits eine Transaktion, verwendet der Runner einen Savepoint und übernimmt
  keinen Commit der aufrufereigenen Transaktion; andernfalls `BEGIN IMMEDIATE`.
- Upgrade- und Recovery-Proben erfolgen nur auf SQLite-Backupkopien. Für die
  lokale realistische V7-Kopie wurden V8–V13, ein wirkungsloser Repeat-up,
  unveränderte Kernzeilenzahlen, `integrity_check=ok`, ein leerer
  `foreign_key_check` und ein `/healthz`-Status 200 nachgewiesen.
- Der Rollbackweg ist Backup-Restore gemäß S34; V0013 besitzt zusätzlich ein
  geprüftes strukturelles Down-Skript auf einer isolierten Testdatenbank. Ein
  Down-Lauf auf einer echten Datenbank ist nicht Teil des Betriebswegs.

## CB-002 – atomarer Cutoververtrag ab V0014

- V0014 ist die erwartete Runtime-Schemaversion. Die neue Tabelle
  `historical_inventory_mutations` ist ein technischer Mutationsbeleg mit
  eindeutigem Event-Key; sie enthält keinen Backfill und keine frei erweiterbare
  Payload.
- Browser-Writes erhalten eine beim Submit erzeugte stabile Mutations-ID. Bei
  einem verlorenen Response kann dasselbe Formular denselben fachlichen Request
  wiederholen. Lifecycle-Writes verwenden bestehende Trade-, Seiten- und
  Positionsidentitäten.
- Current-State-Mutation, Mutationsbeleg, positiver Zugang und gegebenenfalls
  Fortschrittspunkt werden unter `BEGIN IMMEDIATE` und Savepoint ausgeführt. Ein
  Fehler in einem History-Write rollt alle Teile zurück; ein identischer Retry
  verändert keinen Bestand erneut.
- Der Daten-Smoke auf einer isolierten V7-Backupkopie belegt V8–V14,
  wirkungslosen Repeat-up, unveränderte Kernzeilenzahlen durch die Migration,
  genau einen Zugang und Fortschrittspunkt für `0→1`, wirkungslosen Retry,
  `integrity_check=ok`, leeren `foreign_key_check` und `/healthz` HTTP 200.

## CB-005 – persistente Trophy-Wahrheit ab V0015

- V0015 ist die erwartete Runtime-Schemaversion. Die additive Tabelle
  `canonical_trophy_unlocks` besitzt stabile Definition-/Event-Identitäten,
  einen Composite-FK auf das konkrete Nutzeralbum und enthält keinen Backfill.
- Neue Unlocks entstehen ausschließlich in der bestehenden CB-002-/CB-003-
  Transaktionsgrenze. Ein Fehler rollt Current State, Historie, Completion und
  Trophy gemeinsam zurück; Unique-Constraints und `BEGIN IMMEDIATE` sichern
  Retry- und Konkurrenzfälle.
- Completion-Unlocks referenzieren ausschließlich den historischen CB-003-Fakt.
  Sonstige Unlocks referenzieren die auslösende Bestandsmutation; ein konkreter
  Triggersticker wird nur bei eindeutigem Einzeltrigger gespeichert.
- Produktive Trophy-GETs lesen ab V0015 nur gültige persistierte Unlocks.
  Legacydaten in `unlocked_trophies` bleiben unverändert und werden weder
  übernommen noch von parallelen Writer-Callbacks erweitert.

## CB-004 – kontrollierter Legacy-Backfill ab V0016

- V0016 ist die erwartete Runtime-Schemaversion. Sie erweitert ausschließlich
  den Constraint von `canonical_trophy_unlocks` um den strukturierten Source-Typ
  `legacy_trophy_backfill`; die Migration selbst liest, klassifiziert oder
  übernimmt keine Legacyzeile.
- Der Maintenance-Pfad benötigt immer einen expliziten Datenbankpfad. Default
  ist Dry-run; nur `--apply` schreibt. Import, App-Startup, Migration und GET
  lösen keinen Backfill aus.
- Apply re-auditiert unter `BEGIN IMMEDIATE`/Savepoint und schreibt Trophy und
  gegebenenfalls Completion atomar. Stabile Keys referenzieren die konkrete
  `unlocked_trophies.id`; Triggersticker bleiben `NULL`. Bestehende kanonische
  Fakten werden weder überschrieben noch umetikettiert.
- Betrieblicher Rollback nach einem ausgeführten Apply ist Restore der zuvor
  geprüften Backupkopie. Das V0016-Down-Skript ist nur strukturell nutzbar,
  solange keine `legacy_trophy_backfill`-Zeile existiert, und scheitert danach
  absichtlich fail-closed am V0015-Constraint.
- Der realistische Copy-Smoke belegt 61 geprüfte Zeilen, 21 Trophy-Writes,
  0 Completion-Writes, Repeat 0/0, unveränderte geschützte Tabellen,
  `integrity_check=ok`, leeren `foreign_key_check` und `/healthz` HTTP 200.

## P0-Regressionsfix aus dem Product Audit

- **Befund:** Auf Mobile überlagerten Bottom Navigation und Trade-Dock unteren
  Content; Inline-Änderungen des Stickerbestands endeten mit einem rohen 403.
- **Ursache:** Die beiden fixierten Bottom-Komponenten hatten keinen gemeinsamen
  Belegungsvertrag. Zusätzlich renderte das CSRF-Meta-Element den Token mit einem
  fehlerhaften abschließenden Anführungszeichen.
- **Fix:** Bottom-Navigation und Trade-Dock verwenden eine gemeinsame, dynamisch
  gemessene Bottom-Zone. Der CSRF-Token wird korrekt gequotet, Quantity-Mutationen
  verlangen eine `user_albums`-Zuordnung, und 403-Antworten besitzen kontrollierte
  HTML- beziehungsweise JSON-Verträge.
- **Regressionstest:** Plus/Minus, echter gerenderter Fetch-Token, fehlender und
  falscher Token, unveränderte Daten bei 403, Albumzuordnung, Fremdbestand,
  gemeinsamer Scrollraum sowie HTML-/JSON-403 sind gezielt abgedeckt.
- **Manueller Smoke:** Stickerwall mit Reload, Stickerliste bis zum unteren Ende,
  laufende und lange Dealansicht sowie verbotener Mutation-Request werden bei
  390 px und 430 px geprüft; Desktop und Landscape werden ergänzend kontrolliert.
- **Status:** Implementiert. Der gezielte Lauf ist mit 6/6 und das S01-S38-Gate
  zweimal mit jeweils 529/529 Tests bei 0 Skips grün. Der echte HTTP-Smoke für
  Plus, Minus und kontrollierten 403 ist grün; die visuelle Abnahme auf den
  Ziel-Viewports bleibt beim Product Owner.
