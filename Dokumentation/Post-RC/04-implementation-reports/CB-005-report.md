# CB-005 – Implementierungsreport

**Stand:** 2026-08-16
**Branch:** `feature/wm-special-trophies`
**Empfehlung:** CB-005 ABGENOMMEN

1. **Ziel:** Eine einzige persistente Wahrheit für individuell kuratierte
   Album-Trophäen herstellen. Unlocks entstehen nur am realen
   Bestandsmutationsmoment, bleiben dauerhaft erhalten und erzeugen weder Feed
   noch Notification. Vergangenheit wird nicht interpretiert oder migriert.

2. **Ausgangszustand / Inventar:** WM26 und VfL besaßen liebevoll definierte
   Code-/Kapitel-Trophäen, daneben aber generische Albumziele und globale
   Sticker-, Doppelten- und Trade-Trophäen. `unlocked_trophies` identifizierte
   nur über User, Albumscope und sichtbaren Namen. Verteilte Callback-Writer
   schrieben sichtbare und `silent_reached`-Ergebnisse nachträglich; globale
   Checks liefen beim Popup-Queueing. Albumseite, Preview, Schrank, Statistik
   und Profil verwendeten unterschiedliche Current-State-/Legacy-Projektionen.
   Der URL-Parameter `trophy` konnte eine Popupdarstellung auslösen; `trigger`
   war nur Darstellungsinput. CB-003 lieferte dagegen bereits einen stabilen
   exactly-once-Abschluss pro `user_album`.

3. **Geänderte Dateien:** Fachcode: `App/trophy_definitions.py`,
   `App/services/trophy_unlocks.py`, `App/services/history_cutover.py` und
   `App/webapp.py`. Schema: V0015 Up/Down unter
   `App/Database/migrations/`. Runtime-/Deploymentstand: Runtime Operations,
   Performance-Baseline, S34-Operationsdokumente und betroffene Latest-Schema-
   Tests. Neu ist `tests/test_cb005_canonical_trophy_truth.py`. Dokumentiert
   wurden Build-Plan, Engineering Hardening und dieser Report. Keine
   Profil-/Statistik-/Home-, Feed-, Notification- oder Designlogik wurde
   umgebaut.

4. **Migration:** JA. V0015 erstellt additiv
   `canonical_trophy_unlocks`; das Down-Skript entfernt nur diese neue Tabelle
   und ihre Indizes. Weder `unlocked_trophies` noch bestehende Bestands- oder
   Historienzeilen werden verändert. Die Runtime erwartet nach kontrolliertem
   Predeploy V0015. Die echte lokale V7-Datenbank wurde nicht migriert.

5. **Kanonische Trophy-Identität:** Jede Zeile besitzt eine explizite stabile
   `trophy_definition_id`, die konkrete `user_album_id` und zusätzlich
   `user_id`/`album_id`. Ein Composite-FK prüft diesen Kontext. Der stabile
   Event-Key lautet `trophy-unlock:<user_album_id>:<definition_id>`;
   `UNIQUE(user_album_id, trophy_definition_id)` erzwingt genau einen Unlock
   je Albumexemplar und Definition. Sichtbarer Name ist nur Snapshot, nicht
   Identität.

6. **Kuratierter Katalog:** Kanonisch sind 20 bestehende individuelle WM26-
   Definitionen und 16 bestehende individuelle VfL-Definitionen. Enthalten
   sind die konkrete Completion, Kapitel-/Serien- und Spezialtrophäen. Nicht
   enthalten sind `Erster Sticker`, `Halbzeit`, `Endspurt`, sämtliche globalen
   Definitionen und generische Fallbacks. EM24 erhält keinen Katalog, weil kein
   bereits freigegebener expliziter Katalog nachweisbar war. Es wurde keine
   neue Trophy erfunden.

7. **Persistente Unlock-Wahrheit:** `CanonicalTrophyUnlockService` liest
   ausschließlich gültige persistierte V0015-Zeilen. Ein späterer Rückgang
   löscht oder sperrt nichts; erneutes Erreichen verändert Timestamp, Source
   und Trigger nicht. Navigation, Rendern und Startup schreiben keine Unlocks.

8. **Unlock-Orchestrierung:** Vor einer potentiell positiven Mutation wird im
   zentralen `HistoricalInventoryWriteService` der Katalogzustand aufgenommen.
   Nach erfolgreichem Current-State-/CB-002-Write und CB-003-Evaluation wird
   ausschließlich bei einem realen `previous_quantity == 0` und
   `quantity > 0` der Nachzustand verglichen. Nur neu erreichte, kuratierte
   Definitionen werden gespeichert.

9. **Completion-Trophy-Anbindung:** `vfl.completion.v1` beziehungsweise
   `wm26.completion.v1` kann nur entstehen, wenn CB-003 in
   `historical_album_records` einen Abschluss besitzt. Unlockzeitpunkt und
   Source-Key werden direkt aus diesem Fakt übernommen. Aktuelle 100 Prozent,
   eine alte Trophyzeile oder ein späterer beliebiger Write sind kein Beweis.

10. **Triggersticker-Vertrag:** Bei der instrumentierten Einzelmutation wird
    der konkrete Sticker nur gespeichert, wenn er gültiger Katalogcode und Teil
    der gerade erreichten Code-Definition ist. Für die gleichzeitig erzeugte
    Completion ist derselbe letzte Sticker eindeutig. Direkte/mehrdeutige
    Orchestrierung ohne sicheren Trigger speichert `NULL`. URL-Parameter werden
    nie als historische Evidence verwendet.

11. **Legacy-Writer:** Ab V0015 schreibt `record_trophy_unlocks` weder sichtbare
    noch `silent_reached`-Namen; er ist nur noch ein read-only Popup-Adapter für
    bereits kanonisch persistierte Titel. `check_global_trophy_unlocks` liefert
    leer. Alte Callback-Aufrufstellen dürfen so regressionsarm bestehen bleiben,
    erzeugen aber keine parallelen Legacy- oder kanonischen Fakten. Legacydaten
    werden nicht gelöscht.

12. **Read-Vertrag:** Album-Trophyseite, Albumpreview, `erreichte_trophaeen*`
    und Trophy-Schrank verwenden ab V0015 die persistierte, kataloggefilterte
    Projektion. Die Detailseite rendert nur freigeschaltete Trophäen; gesperrte
    Namen/Beschreibungen bleiben verborgen. Globale Sektionen und dynamische
    Next-Ziele werden im kanonischen Schrank nicht ausgegeben. Ein gefälschtes
    `?trophy=` erzeugt ab V0015 kein Popup. Die Albumportalkarte zeigt weiterhin
    normalen Albumfortschritt, nicht eine Trophy-Behauptung.

13. **Transaktion / Atomarität:** Inventory, CB-002-Mutationsbeleg,
    Lifetime-/Progressfakten, CB-003-Completion und V0015-Unlock liegen im
    bestehenden `cb002_inventory_history`-Savepoint unter `BEGIN IMMEDIATE`.
    Ein injizierter Trophyfehler rollt sämtliche Teile zurück.

14. **Idempotenz:** Derselbe Mutation-Key wird vor einer zweiten Bestandsbuchung
    als Replay erkannt. Zusätzlich schützen stabiler Unlock-Event-Key und der
    Unique-Constraint je Nutzeralbum/Definition. Zwei serialisierte
    konkurrierende Kandidaten erzeugen zusammen exakt eine neue Zeile.

15. **Pre-Cutover-Verhalten:** Migration, GET, Startup und spätere
    Doppeltenerhöhung erzeugen keinen Unlock. Ein schon vollständiges Album ohne
    CB-003-Abschluss bleibt ohne Completion-Trophy. Ein nach Cutover real neu
    erfüllter Katalogsatz darf ab seinem echten letzten `0→>0`-Trigger einen
    neuen Unlock erhalten.

16. **Bewusst nicht migrierte Alt-Trophäen:** Sämtliche Zeilen in
    `unlocked_trophies`, einschließlich möglicher globaler, generischer,
    `silent_reached`- oder EM24-Zeilen, bleiben zweifelhaft und Legacy read-only.
    Sie werden nicht in V0015 übernommen und nicht als Abschlussbeweis benutzt.
    Ihre Validierung bleibt ausschließlich CB-004.

17. **Gezielte Tests:** 14/14 in 0,158 s, `OK`. Abgedeckt sind Katalog/IDs,
    Up/Repeat/Down, Trigger/NULL, normaler Unlock, Persistenz, Rückgang,
    Wiedererreichen, Retry/Konkurrenz, Completionquelle, Pre-Cutover, GETs,
    URL-Fälschung, Legacy-/globale/generische Sperre, Ownership/FK, Atomarität
    sowie keine Feed-/Notification-Writes.

18. **Kombinierte Tests:** CB-001/002/003/005 plus HTTP-Integrität,
    Deployment/Recovery und RC-Migrationsgate: 77/77 in 1,594 s, `OK`.

19. **Regression Lauf 1:** 580 Tests in 6,997 s, `OK`, 0 Fehler, 0 Skips.

20. **Regression Lauf 2:** 580 Tests in 6,896 s, `OK`, 0 Fehler, 0 Skips.

21. **Migration / Integrity / FK:** Isoliert V14→V15 ergab `(15,)`, Repeat-up
    `()`, unveränderte Kernzeilenzahlen, `integrity_check=ok` und 0 FK-Treffer;
    Down ergab `(15,)` und Version 14. Auf einer realistischen lokalen V7-Kopie
    liefen V8–V15; auch dort blieben die Kernzeilenzahlen durch Migration
    unverändert, Integrity war `ok` und der FK-Check leer.

22. **Startup-Smoke:** Frischer App-Import gegen die isolierte V15-Kopie mit
    explizitem Testing-Secret erfolgreich. `/healthz` lieferte 200 und
    `{"status":"ok"}`, `/login` 200 und die authentifizierte VfL-Trophyseite
    200.

23. **Realistischer Daten-Smoke:** Auf der isolierten V7-Kopie wurde das
    vorhandene VfL-Nutzeralbum auf 249/250 vorbereitet. Sticker 250 erzeugte um
    `2026-08-16T18:00:00.000000Z` genau die neue `Fanshop`- und Completion-
    Trophy mit Trigger `250`; Completion referenzierte
    `album-completion:2`. Identischer Retry, Rückgang und Wiedererreichen ließen
    beide ersten Unlocks unverändert. Danach: 250 Positionen, Legacycount
    unverändert, Feed-/Notificationcounts unverändert, beide Trophäen im echten
    HTTP-Read sichtbar.

24. **Bekannte Grenzen:** Nur WM26 und VfL besitzen einen freigegebenen
    Closed-Beta-Katalog. Neue Albumtypen benötigen eine bewusste Kuratierung und
    stabile IDs. Das bestehende Single-Exemplar-Modell bleibt unverändert.
    Ressource-Warnungen zu bereits bekannten offenen SQLite-/Dateihandles sind
    weiterhin sichtbar, aber kein Fehler oder Skip.

25. **Technische Restpunkte:** Profil- und Statistikprojektionen sowie der
    bestehende Datenexport zählen/zeigen weiterhin Legacy-
    `unlocked_trophies`; sie wurden wegen des ausdrücklichen Verbots eines
    Profil-/Statistik-/Home-Umbaus nicht verändert und müssen in ihren späteren
    Projektionspaketen auf die kanonische Wahrheit umgestellt werden. CB-004
    entscheidet ausschließlich validierte Altdaten. CB-007 kann auf dem stabilen
    Unlock-Event-Key aufbauen. Innerhalb der CB-005-Schreibmaschine bleibt kein
    offener Parallelwriter.

26. **Abweichungen vom Bauplan:** Die ältere Kurzfassung nannte eine Erweiterung
    von `unlocked_trophies` als Möglichkeit. Statt Legacyzeilen durch neue IDs
    implizit zu legitimieren, verwendet V0015 eine additive getrennte Tabelle.
    Das ist eine technische Präzisierung des No-Backfill-Vertrags, keine
    fachliche Abweichung. Keine Arbeit aus CB-004/006/007 oder später wurde
    vorgezogen.

27. **Product-Contract-Verletzungen:** NEIN.

28. **Empfehlung:** **CB-005 ABGENOMMEN.** Die produktive Unlock-Grenze ist
    persistent, atomar, idempotent, kataloggebunden und frei von dynamischer
    Rücknahme oder Legacy-Nachtrag.

29. **Kann CB-004 begonnen werden?** **JA.** Der gültige WM26-/VfL-Katalog und
    die stabile Zielidentität stehen fest; EM24 bleibt korrekt ohne kanonischen
    Katalog. CB-004 kann nun ausschließlich explizit validierte Legacy-Evidenz
    mit Dry-run/Auditliste behandeln, ohne dass CB-005 selbst Vergangenheit
    erfunden hat.

## Klassifikation der Bestandslogik

- **A – kanonisch weiterverwendbar:** individuelle WM26-/VfL-Codebedingungen,
  Trophy-Render-/Iconhelfer, stabile `user_albums.id`, CB-002-Mutationsevidence
  und CB-003-Completion.
- **B – technisch transformiert:** Albumseite, Preview, Schrank und
  `erreichte_trophaeen*`; verteilte Callback-Writer wurden zu read-only
  Adaptern hinter der zentralen Orchestrierung.
- **C – Legacy / später entfernbar:** `unlocked_trophies`, globale und
  generische Definitionen/Renderer, dynamische Profil-/Statistik-/Exportreads
  sowie die nun wirkungslosen Callback-Gerüste.
- **D – zuvor fachlich gefährlich:** `silent_reached`, globale Popup-Writes,
  Current-State als Unlock-Wahrheit, Completion aus aktuellen 100 Prozent und
  Popup-Truth aus `trophy`/`trigger`-URL-Parametern. Diese Pfade erzeugen ab
  V0015 keine kanonischen Fakten.

## Recovery und Datenbestand

Die Recoverystrategie bleibt der validierte S34-Backup-Restore; das strukturelle
V0015-Down dient nur dem isolierten Nachweis. Die lokale Datenbank blieb auf V7.
Ihr abschließend gemessener SHA-256 ist
`89254d1fe02980a0ccbf85437611273ea094568a064c75ed281f9ca6a23978a0`, der
unveränderte Referenzfixture-Hash
`21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
