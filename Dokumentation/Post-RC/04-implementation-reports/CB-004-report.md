# CB-004 – Validierter historischer Backfill

**Stand:** 18. August 2026
**Status:** technisch abgenommen

## 1. Ziel

Eindeutig belegte Legacy-Trophäen kontrolliert in die kanonische historische
Wahrheit übernehmen, ohne Vergangenheit aus Current State zu erfinden.

## 2. Ausgangszustand

CB-001 bis CB-003 und CB-005 waren abgenommen. Die lokale V7-Datenbank enthielt
61 Zeilen in `unlocked_trophies`, aber 0 kanonische Trophy-Unlocks und
0 historische Albumabschlüsse. CB-005 stellt nur Kataloge für WM26 (20) und VfL
(16), ausdrücklich keinen EM24-Katalog, bereit.

## 3. Geänderte Dateien

- `App/services/legacy_trophy_backfill.py`
- `Scripts/cb004_validated_trophy_backfill.py`
- `App/Database/migrations/0016_legacy_trophy_backfill_source.up.sql`
- `App/Database/migrations/0016_legacy_trophy_backfill_source.down.sql`
- `App/services/runtime_operations.py`
- `Scripts/s35_performance_baseline.py`
- `tests/test_cb004_validated_historical_backfill.py`
- Runtime-/Migrationsstand-Erwartungen in den vorhandenen S26–S38- und
  Post-RC-Tests
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`
- `Dokumentation/Post-RC/06-engineering-hardening.md`
- S34 Deployment-/Recovery-Dokumente
- dieser Report und `CB-004-backfill-audit.md`

Keine Produkt-UI, Definition, Feed-, Notification-, Profil-, Statistik- oder
Home-Projektion wurde verändert.

## 4. Migration JA/NEIN

**JA: V0016.** V0015 erlaubt als `canonical_trophy_unlocks.source_type` nur
Livequellen. Ein Legacy-Write durfte nicht fälschlich als
`inventory_transition` etikettiert werden. V0016 erweitert deshalb exakt diesen
Constraint um `legacy_trophy_backfill`, übernimmt alle V0015-Zeilen und führt
selbst keinen Backfill aus. Up, Repeat-up, struktureller Down-Test, Erhalt von
V0015-Zeilen, Integrität und FKs sind getestet. Nach realen Backfillzeilen ist
der betriebliche Rollback ein Backup-Restore; Down scheitert absichtlich am
engeren V0015-Constraint.

## 5. Backfill-Service/Script

`ValidatedLegacyTrophyBackfillService` kapselt Audit und atomaren Apply.
`Scripts/cb004_validated_trophy_backfill.py` verlangt `--database`, gibt
deterministisches UTF-8-JSON aus, ist standardmäßig Dry-run und schreibt nur mit
`--apply`. Fehler liefern Exit-Code 1 und strukturiertes Fehler-JSON. Es gibt
keine Webserverabhängigkeit und keine Import-Seiteneffekte.

## 6. Dry-run-Vertrag

Jede `unlocked_trophies`-Zeile erscheint genau einmal mit Legacy-ID, User,
Album, eindeutigem Nutzeralbum, Name, Roh-/normalisierter Zeit, Definition-ID,
Typ, Kategorie, Status, Grund und erlaubtem Backfill. Der Modus führt nur
SELECTs aus. Die Kopien wurden mit der SQLite Backup API erzeugt. Auf der
realistischen Kopie blieb der SHA-256 der migrierten Datei
vor und nach Dry-run identisch:
`44220e6f71b47fc2e026fbd6b85e146c5ceb1cf618eb6aba573c07284470fa6a`.

## 7. Mapping Legacy → canonical

Nur exakte, eindeutige Namensgleichheit innerhalb des bestehenden CB-005-
Katalogs des konkreten Albums ist erlaubt. Es gibt weder Alias-, Fuzzy- noch
Ähnlichkeitslogik. Globale und generische Namen sowie Alben ohne Katalog werden
vor einem Mapping ausgeschlossen. Der vollständige Kandidatensatz steht im
Backfill-Audit.

## 8. Validierungskriterien

Erforderlich sind gültige User-/Albumidentität, genau ein passendes
`user_albums`-Objekt, genau eine exakte Definition und ein belastbarer, nicht
zukünftiger Zeitpunkt. Bestehende oder untereinander widersprüchliche Fakten
blockieren den Write. Identische Mehrfachevidenz wird deterministisch über die
kleinste Legacy-ID repräsentiert.

## 9. Completion-Backfill-Vertrag

Nur die exakte, katalogvalidierte Definition `Album vollendet` darf zugleich
Completion-Evidenz sein. Nutzeralbum und UTC-Zeit müssen eindeutig sein; es darf
keinen abweichenden bestehenden Abschluss und keine widersprüchliche zweite
Evidenz geben. Zielsource ist `validated_trophy`, Source-Key ist
`legacy-trophy:<Legacy-ID>`. Heutige 100 Prozent werden nie ausgewertet.

## 10. Trophy-Backfill-Vertrag

Zielzeilen enthalten Definition-ID, Nutzeralbum-/User-/Albumkontext, Legacy-
Zeitpunkt in kanonischem UTC, stabilen Event-/Source-Key und
`source_type=legacy_trophy_backfill`. `trigger_sticker_code` ist immer `NULL`.

## 11. Konfliktbehandlung

Ein bestehender identischer kanonischer Fakt gewinnt und wird
`ALREADY_PRESENT`; fehlende unabhängige Zielanteile dürfen ergänzt werden.
Abweichende kanonische Zeiten/Identitäten oder widersprüchliche Legacy-Zeiten
werden `CONFLICT/NONE`. Nichts wird überschrieben, verschoben oder umetikettiert.

## 12. Timestamp-Vertrag

Die historische SQLite-Form `YYYY-MM-DD HH:MM:SS` wird aufgrund ihrer
`CURRENT_TIMESTAMP`-UTC-Semantik akzeptiert. ISO-8601 benötigt explizit `Z` oder
Offset. Ausgabe ist `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Fehlende, unparsebare, naive
ISO- oder zukünftige Werte werden verworfen; Zeitzonen werden nicht geraten.

## 13. Idempotenz

Event- und Source-Keys basieren stabil auf `unlocked_trophies.id`. Unique-
Constraints schützen zusätzlich Definition/Nutzeralbum und Event-Key. Apply
re-auditiert innerhalb `BEGIN IMMEDIATE` plus Savepoint. Repeat-Apply auf der
realistischen Kopie erzeugte 0 Trophy- und 0 Completion-Zeilen.

## 14. Echte lokale DB verändert JA/NEIN

**NEIN.** Sie wurde nur gelesen und kopiert. SHA-256 vor und nach allen Läufen:
`89254d1fe02980a0ccbf85437611273ea094568a064c75ed281f9ca6a23978a0`.
Kein Apply und keine Migration liefen gegen die echte Datei.

## 15. Dry-run-Ergebnis auf realistischer Kopie

61/61 geprüft: 21 `VALID_CANONICAL_TROPHY`, 25 `LEGACY_GLOBAL`,
6 `LEGACY_GENERIC`, 5 `NO_CANONICAL_CATALOG`, 4 `AMBIGUOUS`; alle übrigen
Kategorien 0. Ergebnis: 21 zulässige Trophy-, 0 Completion- und 40 verworfene
Kandidaten. Keine Datenänderung.

## 16. Apply-Ergebnis auf isolierter Kopie

Auf einer zweiten, separat von V7 nach V16 migrierten Kopie wurden exakt die
angekündigten 21 Trophy-Zeilen und 0 Completion-Zeilen erzeugt. Alle 21 Sources
sind `legacy_trophy_backfill`; alle Trigger sind `NULL`.

## 17. Repeat-Apply

Zweiter Apply: **0 Trophy / 0 Completion**. Alle 21 zuvor erzeugten Fakten sind
`ALREADY_PRESENT`; keine Tabelle wuchs erneut.

## 18. EM24-Ergebnis

Fünf EM24-Zeilen sind `NO_CANONICAL_CATALOG/NONE`. Insbesondere Row 597,
`Album vollendet` vom `2026-07-01 15:57:30`, wird weder Trophy noch Completion.
Ohne freigegebenen EM24-Katalog ist die Abschluss-Trophäe nicht eindeutig
validierbar; PO-07 verbietet die Annahme.

## 19. Bewusst nicht übernommene Legacy-Daten

25 globale, 6 generische, 4 nicht exakt mapbare und 5 kataloglose EM24-Zeilen.
Nichts wurde gelöscht. Current State, Notifications, Requests und Statistiken
wurden nicht als Evidenz verwendet.

## 20. Gezielte Tests

15/15 grün. Abgedeckt sind V0016 Up/Repeat/Down, WM26/VfL-Mapping, alle
Negativkategorien, EM24, Completion und Nicht-Inferenz aus 100 Prozent,
Timestampfehler, Ownership, Konflikte/identische Evidenz, bestehende Fakten,
Dry-run-Read-only, Apply/Repeat, NULL-Trigger, verbotene Side Effects,
Integrität, atomarer Forced-Failure-Rollback und CLI-Modi.

## 21. Kombinierte CB-001–CB-005-Tests

CB-001, CB-002, CB-003, CB-004 und CB-005 zusammen: **60/60 grün**.

## 22. Regression Lauf 1

**595/595 grün, 0 Fehler, 0 Skips** mit expliziter Testing-Umgebung.

## 23. Regression Lauf 2

**595/595 grün, 0 Fehler, 0 Skips** mit identischem Gate.

## 24. Integrity/FK

Realistische Apply-Kopie: `PRAGMA integrity_check = ok` und
`PRAGMA foreign_key_check` ohne Treffer. Die Migrations- und Fixturetests prüfen
dies zusätzlich.

## 25. App-Startup-Smoke

Test-App gegen die angewendete V0016-Kopie importiert ohne Backfill-
Seiteneffekt. `GET /healthz` liefert 200/`{"status":"ok"}`, `GET /login` 200.

## 26. Daten Vorher/Nachher

Nur `canonical_trophy_unlocks` wuchs von 0 auf 21;
`historical_album_records` blieb 0. Unverändert nach Count und Inhalts-SHA-256:
Users 4, Nutzeralben 8, Inventory 1968, Trade Requests 18, Trades 10,
Tradepositionen 62, Legacy-Trophäen 61, Notifications 87 und Feed 0.

## 27. Bekannte Grenzen

Kein EM24-Katalog bedeutet keinen EM24-Backfill. Nicht explizit katalogisierte
Legacy-Namen bleiben unübernommen. Der Backfill erfindet keine Triggersticker,
Startzeiten, Completion aus Current State oder Feedhistorie.

## 28. Technische Restpunkte

Vor einem späteren echten Apply sind S34-Backup, separate Dry-run-Abnahme und
explizite Product-Owner-Freigabe erforderlich. Nach Apply ist Restore der
betriebliche Rollbackweg. Für CB-004 selbst bleibt kein Implementierungsrest.

## 29. Abweichungen vom Bauplan

Der ältere Bauplan erwartete den EM24-Fall nach Katalogvalidierung als
übernehmbar. Die neuere verbindliche CB-005-Entscheidung stellt jedoch keinen
EM24-Katalog bereit; die detaillierte CB-004-Anweisung fordert dann ausdrücklich
keinen Backfill. Der Bauplan wurde auf diese strengere Wahrheit korrigiert.
Außerdem war V0016 zwingend, weil V0015 keinen ehrlichen Legacy-Source-Typ
zuließ; die Migration bleibt dateninterpretationsfrei.

## 30. Product-Contract-Verletzungen JA/NEIN

**NEIN.** Keine neue Definition, keine Schätzung, keine Projektion, keine
Legacy-Löschung, kein Feed, keine Notification, keine UI-Änderung und kein
Write auf die echte Datenbank.

## 31. Empfehlung

**CB-004 ABGENOMMEN.** Dry-run, Apply, Idempotenz, Integrität, Recovery-Grenze
und vollständiges Regressiongate sind nachgewiesen.

## 32. Kann CB-010 begonnen werden?

**JA.** CB-001 bis CB-005 sind damit technisch abgenommen; CB-010 kann auf den
kanonischen historischen Fundamenten beginnen. Es wurde in dieser Aufgabe nicht
begonnen.
