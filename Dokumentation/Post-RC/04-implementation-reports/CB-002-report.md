# CB-002 – Implementierungsreport

**Stand:** 2026-08-16
**Branch:** `feature/wm-special-trophies`
**Empfehlung:** CB-002 ABGENOMMEN

1. **Ziel:** Ab Cutover neue Albumstarts, reale positive Stickerzugänge und
   sparsame Fortschrittspunkte vollständig, atomar und idempotent erfassen, ohne
   Vergangenheit, Completion, Trophy, Feed oder sichtbare Projektionen
   vorwegzunehmen.

2. **Ausgangszustand:** CB-001 stellte V0013 und den
   `HistoricalCollectionService` bereit, war aber bewusst an keinen produktiven
   Mutationspfad angebunden. Die echte lokale DB stand und steht auf V7. Der
   bereits umfangreich geänderte/untracked Working Tree wurde nicht bereinigt,
   gestaged oder überschrieben.

3. **Geänderte Dateien:** Neu sind V0014 Up/Down,
   `App/services/history_cutover.py`, `tests/test_cb002_history_cutover.py` und
   dieser Report. Angepasst wurden `App/webapp.py`, `trade_shipping.py`,
   `trade_receipt.py`, `trade_problems.py`, Runtime-/Performance-Schemaversion,
   die V14-Erwartungen der betroffenen S26–S38-/P0-Tests, drei
   Operationsdokumente, Build-Plan und Engineering Hardening. Der bestehende
   `InventoryWriteService` und seine Mengen-/Guard-Semantik blieben unverändert.

4. **Migration:** JA – V0014 `collection_history_cutover`. Sie ergänzt nur
   `historical_inventory_mutations` samt Index als strukturierten technischen
   Cutover-/Idempotenzbeleg. Keine Altzeile wird eingefügt oder interpretiert;
   Runtimeziel ist V14. Down entfernt nur diese V0014-Struktur.

5. **Instrumentierte Mutationspfade:** Album hinzufügen; Einzel-Add/Remove;
   Detail-Set; Inline-Quantity; Bulk Add/Remove; Undo; Albumwand-Papiertausch;
   Stickerlisten-/Offline-Transfer; Legacy-Completion-Fallback; Lifecycle-
   Versand, normaler Empfang, vollständiger Problemformular-Empfang,
   Teil-Empfang und spätere Problemauflösung.

6. **Albumstart-Cutover:** Nur ein tatsächlich neu angelegtes `user_albums`-
   Objekt erzeugt atomar `started_at` und `album-start:<user_album_id>`. Ein
   Retry oder eine bereits vor Cutover vorhandene Zuordnung erzeugt keinen
   Start. Zeitpunkte werden nicht aus Bestand, Account oder IDs geschätzt.

7. **Lifetime-Zugang-Cutover:** Gespeichert wird ausschließlich
   `result_quantity - previous_quantity > 0`. `1→2` ergibt `+1`, `1→3` ergibt
   `+2`; Reduktionen erzeugen keinen negativen Lifetime-Eintrag. Quellen bleiben
   auf `inventory`, `paper_trade` und `trade_receipt` begrenzt.

8. **Progress-Cutover:** Ein Punkt entsteht nur beim Übergang `0↔>0`, also wenn
   sich die Anzahl unterschiedlicher vorhandener Sticker ändert. Doppelte und
   reine Mengenänderungen erzeugen keinen Punkt. `owned_count` wird nach dem
   Write gezählt, `total_count` stammt aus `albums.total`.

9. **Feed-Writes:** Nicht umgesetzt. Der Bauplan weist Producer und
   privacy-sichere Feedprojektion CB-007 zu; normale Bestandsänderungen sind
   ausdrücklich nicht feedwürdig. CB-002 erzeugt auch keine Completion-,
   Trophy- oder News-Events.

10. **UTC-Zeitvertrag:** `canonical_utc_timestamp()` serialisiert zentral als
    `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Naive Datetimes und nichtkanonische Strings
    werden an der Cutover-Servicegrenze abgewiesen. Alle Fakten derselben
    Mutation verwenden denselben Zeitpunkt.

11. **Transaktion / Atomarität:** Current-State-Write, V0014-Mutationsbeleg,
    positiver Zugang und optionaler Fortschrittspunkt laufen unter derselben
    SQLite-Transaktion mit Savepoint. Ohne bestehende Transaktion wird
    `BEGIN IMMEDIATE` eröffnet und der Commit weiterhin dem Fachworkflow
    überlassen. Ein History-Fehler rollt den vollständigen Write zurück.

12. **Idempotenz je Pfad:** Browserformulare und Inline-Fetch liefern eine
    stabile Mutations-ID; Scope, Nutzer und Stickerposition bilden Event-Keys.
    Batch/Offline verwenden stabile Positionsindizes. Versand/Empfang verwenden
    Lifecycle-Trade, Seite und `trade_position.id`; Problemwege zusätzlich
    Report-/Phasenidentitäten. Gleicher Key plus gleiche Absicht liest den
    ursprünglichen Beleg und mutiert nicht erneut; widersprüchliche Wiederverwendung
    wird abgewiesen.

13. **Nicht historisierte Altbestände:** Keine vorhandenen Albumzuordnungen,
    Sticker/Mengen, Trophäen, 100-%-Zustände, Notifications, Trades oder
    Fortschritte wurden übernommen. `em24` blieb unangetastet.

14. **Gezielte Tests:** 8/8 grün in 0,110 s; zusätzlich 119/119 kombinierte
    History-/Inventory-/Shipping-/Receipt-/Problem-/Completiontests grün. Belegt
    sind Migration, Albumstart, Delta/Set/Batch/Offline, Lifecycle-Empfang,
    sparsamer Progress, UTC, Retry, Atomarität und bewusster Feed-/Completion-/
    Trophy-Nicht-Cutover.

15. **Regression Lauf 1:** 549 Tests in 6,856 s, `OK`, 0 Fehler, 0 Skips.

16. **Regression Lauf 2:** 549 Tests in 6,842 s, `OK`, 0 Fehler, 0 Skips.

17. **Migration / Integrity / FK:** Isolierte SQLite-Backupkopie V7→V14;
    angewandt V8–V14, Repeat-up leer, Tabellen 17→29. Kernzeilenzahlen durch die
    Migration unverändert. `integrity_check=ok`, `foreign_key_check` leer.

18. **App-Startup:** Frischer Prozess gegen isolierte V14-Kopie erfolgreich;
    `GET /healthz` lieferte HTTP 200.

19. **Daten-Smoke:** Auf der isolierten Kopie wurde ein fehlender realer
    VfL-Code `0→1` gebucht: Current State `1`, ein Mutationsbeleg, ein Zugang und
    ein Fortschrittspunkt. Wiederholung mit demselben Event-Key ließ alle vier
    Werte unverändert; Feed-Ereignisse blieben `0`.

20. **Bekannte Grenzen:** Idempotenz benötigt bei HTTP-Integrationen den
    mitgelieferten Mutations-Key; der reale Browserpfad erzeugt ihn technisch im
    Formular beziehungsweise Inline-Fetch. Vor-Cutover-Historie bleibt bewusst
    unbekannt. Fortschritt ist eine sparsame Zustandskurve, keine vollständige
    Mengenereignisfolge.

21. **Technische Restpunkte:** CB-003 muss den ersten Vollständigkeitsübergang
    separat aus denselben atomaren Mutationsmomenten orchestrieren. CB-005 und
    CB-007 bleiben für Trophy- beziehungsweise Feed-Cutover zuständig. Keine
    offene Restarbeit innerhalb CB-002.

22. **Product-Contract-Verletzungen:** NEIN.

23. **Empfehlung:** **CB-002 ABGENOMMEN.** Alle produktiven positiven
    Bestandszugänge ab Cutover besitzen eine atomare, idempotente
    Historisierungsgrenze; keine spätere Produktprojektion wurde vorgezogen.

24. **Kann CB-003 begonnen werden?** **JA.** Die benötigten Cutover-Fakten und
    Transaktions-/Retry-Grenzen sind vorhanden; CB-003 darf nach separater
    Freigabe ausschließlich den Exactly-once-Erstabschluss ergänzen.

## Warnungen und Recovery

Die Gesamtläufe zeigen weiterhin die vorbestehenden `ResourceWarning`-Meldungen
für nicht geschlossene SQLite-Verbindungen/statische Streams sowie zwei
vorbestehende `SyntaxWarning`-Meldungen zu `\d` in einem großen HTML-String.
V0014 selbst erzeugt keine neue Warnung. Produktiver Rückweg bleibt der
validierte S34-Backup-Restore; V14→V13 wurde ausschließlich isoliert geprüft.
