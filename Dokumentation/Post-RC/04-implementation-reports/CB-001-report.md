# CB-001 – Implementierungsreport

**Stand:** 2026-08-16
**Branch:** `feature/wm-special-trophies`
**Empfehlung:** CB-001 ABGENOMMEN

1. **Ziel:** Persistenter, lesbarer und idempotenter Datenvertrag für künftigen
   Albumstart, Erstabschluss, positive Lifetime-Zugänge, sparsame
   Fortschrittspunkte, Feed-Ereignisse und optionalen Trophy-Trigger – ohne
   Cutover-Writes oder sichtbare Produktänderung.

2. **Ausgangszustand:** Die bestehende `user_albums.id` ist eine stabile
   nutzerspezifische Albumzuordnung. Historische Sammlungsfakten waren nicht
   separat vom Current State modelliert. Der Working Tree war bereits umfangreich
   verändert/untracked; diese fremden Änderungen und die lokale Datenbank wurden
   weder bereinigt, gestaged noch überschrieben.

3. **Geänderte Dateien:** Neu: `App/Database/migrations/0013_historical_collection_contract.up.sql`,
   `.down.sql`, `App/services/historical_collection.py`,
   `tests/test_cb001_historical_collection_contract.py`. Angepasst:
   `App/Database/migration_runner.py`, `App/services/runtime_operations.py`,
   `Scripts/s35_performance_baseline.py`, die S26–S29-, S31–S38- und
   Post-RC-P0-Tests mit V13-Erwartungen, die drei S34-Operationsdokumente sowie
   `Dokumentation/Post-RC/03-closed-beta-build-plan.md` und
   `Dokumentation/Post-RC/06-engineering-hardening.md`. Keine UI-, Auth-,
   Inventory-, Trade-, Trophy- oder Notification-Produktlogik wurde geändert.

4. **Migration:** V0013 `historical_collection_contract`, additiv, ohne Inserts
   oder Backfill. Das Down-Skript entfernt ausschließlich die fünf neuen Tabellen
   und den neuen Kontextindex. Die Runtime erwartet nun Schema 13.

5. **Historische Entitäten:** `historical_album_records`,
   `historical_sticker_acquisitions`, `historical_album_progress_points`,
   `feed_events` und `trophy_unlock_history_context`. Strukturierte Constraints
   begrenzen Mengen, Counts, Event-/Source-/Target-Typen und Albumkontexte; freie
   JSON-Payloads wurden bewusst nicht eingeführt.

6. **Services:** `HistoricalCollectionService` bietet Write-/Read-Grenzen für
   Albumstart, positiven Zugang, Fortschrittspunkt und Feed-Ereignis sowie
   Schemaerkennung. Er ist absichtlich nicht in bestehende Mutationen integriert.
   Completion- und Trophy-Write-Orchestrierung wurden nicht vorgezogen.

7. **Idempotenz / Exactly-once:** Albumstart und Erstabschluss besitzen je einen
   eindeutigen Event-Key; ein Albumhistorien-Datensatz ist über `user_album_id`
   einmalig. Zugänge deduplizieren über Source-Typ, Source-Key, Zuordnung und
   Sticker; Fortschritt über Zuordnung plus Event-Key; Feed über Event-Key;
   Trophy-Kontext einmal je Unlock. Identische Retries liefern denselben Datensatz,
   abweichende Fakten unter demselben Schlüssel werden abgewiesen.

8. **Heutiger Albumbezug:** Alle albumbezogenen Fakten referenzieren
   `user_albums(id, user_id, album_id)` per Composite-FK. Damit sind Ownership und
   Albumtyp konsistent und nicht nur an den globalen Albumtyp gekoppelt.

9. **Spätere Albumexemplare:** Historie hängt an der stabilen
   `user_albums.id`-Identität. Eine spätere Erweiterung kann weitere
   nutzerspezifische Zuordnungen anlegen, ohne historische Tabellen neu an den
   Albumtyp koppeln zu müssen; Mehrfachexemplare selbst wurden nicht implementiert.

10. **Kein Backfill:** Keine bestehenden Trophy-Unlocks, 100-%-Bestände,
    Sticker, Mengen, Notifications oder Zeitstempel wurden als Vergangenheit
    interpretiert; insbesondere keine `em24`-Interpretation.

11. **Gezielte Tests:** 6/6 grün in 0,033 s. Abgedeckt sind Fresh/Upgrade/
    Repeat-up/Down, Constraints, positive/0/negative Mengen, Deduplizierung,
    Konflikte, FKs, optionales Trigger-NULL, persistenter Erstabschluss und alle
    freigegebenen Serviceoperationen.

12. **Regression Lauf 1:** 541 Tests in 6,290 s, `OK`, 0 Fehler, 0 Skips.

13. **Regression Lauf 2:** 541 Tests in 6,304 s, `OK`, 0 Fehler, 0 Skips.

14. **Isolierte Migration:** SQLite-Backupkopie der lokalen V7-Datenbank wurde
    ausschließlich im temporären Verzeichnis auf V13 gebracht. Angewandt:
    V8–V13; Repeat-up: keine Migration. Tabellen: 17 → 28.

15. **Integrity:** `PRAGMA integrity_check` ergab `ok`.

16. **Foreign Keys:** `PRAGMA foreign_key_check` ergab keine Zeile.

17. **Whitespace:** `git diff --check` ist ohne Befund durchgelaufen.

18. **App-Startup:** Frischer Prozessimport gegen isoliert migrierte V13-Kopie
    erfolgreich; `GET /healthz` lieferte HTTP 200.

19. **Bestandsdaten vorher/nachher:** Unverändert: Users 4, Albums 3,
    Albumzuordnungen 8, Inventory-/Stickerzeilen 1965, Trades 10,
    Tradepositionen 62, Trophy-Unlocks 61. Die echte lokale DB blieb auf V7 und
    wurde nicht migriert.

20. **Warnungen:** Keine Warnung in den gezielten CB-001-Tests. Beide
    Gesamtläufe zeigen den bereits vor CB-001 vorhandenen `ResourceWarning`-Typ
    für nicht geschlossene SQLite-Verbindungen beziehungsweise einen statischen
    Dateistream in älteren Tests; kein neuer CB-001-Fehler und kein Skip.

21. **Bekannte Grenzen:** Zeitfelder sind persistierte, explizit als kanonische
    UTC-ISO-8601-Texte (`...Z`) zu liefernde Werte; die Servicegrenze normalisiert
    noch keine Zeitformate. Feed-Privacy/Retention, Cutover-Erfassung,
    Abschlussorchestrierung und Trophy-Cutover fehlen absichtlich.

22. **Offene technische Restpunkte:** CB-002 muss alle autorisierten positiven
    Mutationspfade transaktional an diese Grenze anbinden und die konkrete
    UTC-Serialisierung zentral festlegen. CB-003/CB-005 ergänzen ihre jeweils
    eigene Orchestrierung; keine Restarbeit innerhalb CB-001.

23. **Abweichungen vom Bauplan:** Keine fachliche Abweichung. Zusätzlich wurde
    der Migration Runner gehärtet, weil der isolierte Down-Fehlerpfad eine nicht
    vollständig atomare DDL-Ausführung sichtbar machte; Savepoints schützen nun
    aufrufereigene Transaktionen.

24. **Product-Contract-Verletzungen:** NEIN.

25. **Empfehlung:** **CB-001 ABGENOMMEN.** Schema-, Service-, Migrations- und
    Regressionsnachweise sind vollständig grün.

26. **Kann CB-002 begonnen werden?** **JA.** Die historische Schreibgrenze ist
    stabil vorhanden; CB-002 darf separat freigegeben ausschließlich die
    Cutover-Integration implementieren.

## Recovery

Produktiver Rückweg ist das validierte S34-Backup-Restore auf die vor dem Deploy
erzeugte Datenbankkopie. Das V0013-Down-Skript ist für kontrollierte isolierte
Tests vorhanden und auf V13→V12 geprüft; es darf nicht ungeprüft auf der echten
Datenbank ausgeführt werden.
