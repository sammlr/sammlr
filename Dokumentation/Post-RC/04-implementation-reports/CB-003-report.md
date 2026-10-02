# CB-003 – Implementierungsreport

**Stand:** 2026-08-16
**Branch:** `feature/wm-special-trophies`
**Empfehlung:** CB-003 ABGENOMMEN

1. **Ziel:** Den ersten fachlichen Übergang eines konkreten Nutzeralbums von
   unvollständig zu vollständig atomar, persistent und exactly once als
   historischen Abschluss erfassen. Keine sichtbare Projektion und kein
   Trophy-, Feed-, Notification- oder Backfill-Cutover.

2. **Ausgangszustand:** V0013 stellte `historical_album_records` mit stabiler
   `user_album_id`, eindeutigem Completion-Key, Timestamp und strukturierter
   Source bereit. V0014 verband bereits alle produktiven Bestandsmutationen mit
   demselben Transaktions-/Savepoint-Moment, erzeugte aber bewusst noch keine
   Completion. Die echte lokale DB blieb auf V7. Der umfangreich vorbestehend
   geänderte/untracked Working Tree wurde weder bereinigt noch gestaged.

3. **Geänderte Dateien:** Neu sind `App/services/album_completion.py`,
   `tests/test_cb003_exactly_once_album_completion.py` und dieser Report.
   Angepasst wurden `App/services/historical_collection.py`,
   `App/services/history_cutover.py` und
   `Dokumentation/Post-RC/03-closed-beta-build-plan.md`. Keine UI-, Trophy-,
   Feed-, Notification-, Auth-, Privacy-, Statistik- oder Produktlogikdatei
   wurde verändert.

4. **Migration:** NEIN. V0013 erzwingt bereits maximal einen Datensatz je
   `user_album_id`, einen eindeutigen `completion_event_key`, vollständige
   Completion-Feldgruppen und den Composite-FK auf das konkrete Nutzeralbum.
   Eine kosmetische V0015 wäre ohne zusätzlichen Integritätsgewinn gewesen.
   Es gibt keinen Backfill und die Runtime bleibt auf Schema V14.

5. **Kanonische Vollständigkeitsdefinition:** Verwendet wird dieselbe Wahrheit
   wie `lade_album_for_user`: `all_codes(album_id)` liefert ausschließlich die
   verbindlichen Katalogpositionen; `InventoryReadService.progress` zählt eine
   Position als gesammelt, wenn ihre physische Quantity mindestens 1 ist.
   EM24/WM26 verwenden die Länge ihres Datenkatalogs, andere unterstützte Alben
   den persistierten `albums.total`. Vollständig bedeutet `collected >= total`.
   Fremde Stickerzeilen und reine Mengen weiterer Exemplare erhöhen
   `collected` nicht.

6. **Übergangserkennung:** Innerhalb der Schreibtransaktion wird vor einer
   potentiell positiven Mutation der kanonische Zustand aufgenommen. Nach dem
   erfolgreichen Current-State- und History-Write wird nur bei einer echten
   Besitzstandsänderung `previous_quantity == 0` und `quantity > 0` erneut
   geprüft. Completion entsteht nur bei `before.complete == False` und
   `after.complete == True`. Eine bloße Nachzustandsprüfung findet nicht statt.

7. **Completion-Service:** `FirstAlbumCompletionService` löst die stabile
   Albumzuordnung auf, erzeugt Vor-/Nachzustände und orchestriert ausschließlich
   den ersten historischen Abschluss. `HistoricalCollectionService` kapselt
   den idempotenten V0013-Write. Beide Services schalten keine Trophy frei und
   schreiben weder Feed noch Notification.

8. **Exactly-once-Vertrag:** Fachlich wird ein vorhandener Erstabschluss vor
   jedem Write respektiert. Der stabile Event-Key lautet
   `album-completion:<user_album_id>`. V0013 besitzt einen Primärschlüssel auf
   `user_album_id` und einen Unique-Constraint auf dem Completion-Key. Gleicher
   Key mit abweichenden Fakten ist ein Konflikt; ein späterer anderer Kandidat
   ist ein No-op, weil der erste persistierte Fakt gewinnt. `BEGIN IMMEDIATE`
   serialisiert konkurrierende SQLite-Writer.

9. **Transaktion / Atomarität:** Membership-Auflösung, Vorzustand,
   Current-State-Mutation, V0014-Mutationsbeleg, Lifetime-Zugang,
   Fortschrittspunkt, Nachzustand und Completion liegen im bestehenden
   `cb002_inventory_history`-Savepoint. Ohne äußere Transaktion wird davor
   `BEGIN IMMEDIATE` eröffnet. Ein absichtlich injizierter Completion-Fehler
   rollt Inventory und sämtliche Historywrites vollständig zurück.

10. **Timestamp / Evidence:** `completed_at` ist exakt derselbe bereits von
    CB-002 validierte kanonische UTC-Zeitpunkt (`YYYY-MM-DDTHH:MM:SS.ffffffZ`)
    wie `occurred_at` der Mutation. `completion_source_type` ist
    `inventory_transition`; `completion_source_key` ist der stabile V0014-
    Mutationsevent-Key. Es gibt keine zweite `now()`-Ermittlung und keine freie
    Beschreibung.

11. **Instrumentierte Mutationspfade:** Durch die zentrale CB-002-Grenze sind
    Einzel-Add, Inline-Quantity, Detail-Set, Bulk Add, positiv wirkendes Undo,
    Albumwand-/Stickerlisten-Papiertausch, normaler Lifecycle-Empfang,
    vollständiger Problemformular-Empfang, Teilempfang und spätere
    Problemauflösung erfasst. Versand und Reduktionen können keinen positiven
    Vollständigkeitsübergang erzeugen.

12. **Pre-Cutover-Alben:** Ein bereits vollständiges Album ohne Completion
    bleibt auch bei `1→2` ohne historischen Abschluss. Ein bereits vorhandenes
    unvollständiges Album darf durch den ersten echten letzten Zugang nach
    Cutover abgeschlossen werden. Dabei bleibt `started_at` bewusst `NULL`; es
    wird kein Albumstart erfunden.

13. **Späterer Bestandsrückgang:** Eine Reduktion ändert oder löscht den
    historischen Datensatz nicht. Current State kann wieder unvollständig sein,
    während `completed_at`, Completion-Key und Evidence unverändert bleiben.

14. **Erneutes Erreichen von 100 Prozent:** Der neue positive Übergang wird als
    Bestandsmutation, Lifetime-Zugang und Progress erfasst, erzeugt aber keinen
    zweiten Abschluss und verschiebt den ersten Timestamp nicht.

15. **Legacy-Completion-/Trophy-Pfade:** Sammlung, Profil und Statistik lesen
    weiterhin dynamischen Current State und sind reine Legacy-Projektionen, die
    CB-013 bis CB-015 ersetzen. Die verteilten Route-/Lifecycle-Callbacks
    berechnen weiterhin Trophäen vor/nach Mutationen und persistieren Namen in
    `unlocked_trophies`. Besonders der `silent_reached`-Pfad kann eine bereits
    erfüllte Legacy-Trophy bei einer späteren Mutation nachtragen. Er ist ein
    später zu ersetzender, fachlich gefährlicher paralleler Write-Pfad, wurde
    aber gemäß ausdrücklicher CB-003-Abgrenzung weder gelöscht noch zum
    historischen Completion-Beweis erklärt. Er schreibt nie in
    `historical_album_records`.

16. **Nicht umgesetzt:** Keine CB-005-Trophy, kein Trophy-Triggerkontext, kein
    CB-007-Feed-Event, keine Notification, kein Backfill, keine Interpretation
    von `em24`, keine Profil-/Statistik-/Vitrinenprojektion, keine Animation und
    keine UI-Änderung.

17. **Gezielte Tests:** 17/17 grün in 0,232 s. Abgedeckt sind normaler
    Erstabschluss, Retry, Rückgang, erneute Vollständigkeit, Pre-Cutover voll
    und unvollständig, Einzel/Inline/Set/Batch/Undo/Offline, normaler Receipt,
    vollständiger Problemempfang, Teilempfang plus Auflösung, Atomarität,
    konkurrierende Kandidaten, GET-/Startup-Nichtwirkung sowie explizit keine
    Trophy-/Feed-/Notification-Writes der neuen Orchestrierung.

18. **Kombinierte History-/Trade-Tests:** 177/177 grün in 1,556 s. Enthalten
    sind CB-001 bis CB-003 sowie Inventory Write/Guard, Shipping, Receipt,
    Problem-, Receipt-UX- und Trade-Completion-Regressionen.

19. **Regression Lauf 1:** 566 Tests in 6,596 s, `OK`, 0 Fehler, 0 Skips.

20. **Regression Lauf 2:** 566 Tests in 6,634 s, `OK`, 0 Fehler, 0 Skips.
    Ein vorangegangener Aufruf mit `discover -s tests` war ungültig, weil er das
    Paket-Bootstrap `tests/__init__.py` umging und dadurch erwartungsgemäß vier
    Security-Environment-/Importfehler erzeugte; er ist kein Abnahmelauf.

21. **Migration / Integrity / FK:** Keine neue Migration. Eine isolierte Kopie
    der Referenzfixture wurde frisch bis V14 migriert. `integrity_check=ok` und
    `foreign_key_check` lieferte 0 Zeilen. Die echte lokale DB wurde nicht
    migriert oder beschrieben.

22. **App-Startup-Smoke:** Frischer Prozessimport mit explizitem Testing-Secret
    gegen die isolierte V14-Smoke-DB erfolgreich; `GET /healthz` lieferte 200
    und `{"status":"ok"}`.

23. **Realistischer Daten-Smoke:** Auf der isolierten V14-Kopie wurde Nutzer 1
    im VfL-Album auf 249/250 gesetzt. `0→1` des letzten Katalogstickers erzeugte
    Current State 250, Zugang, Progress und genau eine Completion um
    `2026-08-16T15:00:00.000000Z`. Nach Entfernung waren 249 Positionen
    vorhanden und dieselbe Completion blieb bestehen. Erneutes Hinzufügen
    stellte 250 her; Completion-Timestamp, Key `album-completion:1` und Evidence
    `smoke:first` blieben bytegleich. Ergebnis: 1 Completion, 2 positive
    Zugänge, 3 Progresspunkte, 0 Feed-Events.

24. **Bekannte Grenzen:** Das bestehende Single-Exemplar-/Katalogmodell bleibt
    unverändert. Mehrfachexemplare sind Future-Scope. Die Vollständigkeitslogik
    folgt bewusst dem heutigen Katalogvertrag; neue Albumtypen benötigen wie
    bisher eine korrekte `all_codes`-Definition. HTTP-Retries benötigen weiterhin
    den in CB-002 eingeführten stabilen Mutation-Key.

25. **Technische Restpunkte:** CB-005 muss die parallelen Legacy-Trophy-Writer
    durch eine persistente gültige Trophy-Wahrheit ersetzen und den Abschluss
    konsumieren. CB-007 muss genau ein Feed-Ereignis aus dem stabilen
    Completion-Key produzieren. CB-004 bleibt alleiniger validierter Backfill.
    Keine Restarbeit innerhalb CB-003.

26. **Abweichungen vom Bauplan:** Der ältere Kurztext des Bauplans erwartete
    eine neue Migration und gemeinsame Trophy-/Feed-Referenzen. Die detaillierte
    freigegebene CB-003-Aufgabe präzisiert ausdrücklich: vorhandenes V0013-Schema
    bevorzugen, keine Trophy und kein Feed. Deshalb ist V14 unverändert und der
    Completion-Datensatz mit stabilem Key die spätere Producerquelle. Keine
    fachliche Abweichung von der aktuellen Aufgabe.

27. **Product-Contract-Verletzungen:** NEIN.

28. **Empfehlung:** **CB-003 ABGENOMMEN.** Der erste echte
    `unvollständig→vollständig`-Mutationsübergang ist atomar und exactly once
    historisiert; alle geforderten Gates sind grün.

29. **Kann CB-005 begonnen werden?** **JA.** CB-003 liefert eine stabile,
    timestamp- und evidence-feste Completion-Quelle, ohne Trophy-Verantwortung
    vorwegzunehmen. CB-005 darf ausschließlich die persistente Trophy-Wahrheit
    und den gültigen Katalog integrieren.

## Warnungen und Recovery

Die Gesamtläufe zeigen die bereits vor CB-003 bekannten `ResourceWarning`-
Meldungen für nicht geschlossene SQLite-Verbindungen beziehungsweise einen
statischen Dateistream; kein neuer Fehler und kein Skip. `git diff --check`,
zusätzliche Trailing-Whitespace-Prüfung der neuen Dateien und `py_compile` sind
ohne Befund. Die SHA-256-Werte der echten lokalen DB
(`33b20999c3ee30b6a924df6225db73bca953697fc1b8375d992c62484f0aa1c3`)
und Referenzfixture
(`21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`)
sind gegenüber CB-002 unverändert. Da keine Migration entstand, bleibt der
Recoveryvertrag V14 unverändert: validierter Backup-Restore statt ungeprüfter
Manipulation der echten Datenbank.
