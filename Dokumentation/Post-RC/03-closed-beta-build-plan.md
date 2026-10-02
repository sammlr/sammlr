# Closed-Beta-Bauplan

**Stand:** 21. August 2026
**Status:** P1 abgeschlossen; CB-001 bis CB-017 sowie Phase 7 – Engineering Hardening und Phase 8 – Realistic Simulation technisch abgenommen. Phase 9 wurde am 21. August 2026 ausgeführt und bleibt NO-GO: Alle technischen Gates einschließlich des realen S34-Betreiber-Backup-/Restore-Drills sind grün; ausschließlich die juristische Endprüfung und finalen Betreiberangaben fehlen. Externe Closed-Beta-Nutzer bleiben gesperrt.
**Normative Grundlage:** [Product Contract Freeze](02-cross-audit/02-product-contract-freeze.md)

## 1. Zweck und Scope-Regel

Dieser Plan übersetzt den eingefrorenen Produktvertrag in fachlich und technisch geschnittene Arbeitspakete. Er ist keine Freigabe, in dieser Dokumentationsrunde Code, Datenbank oder Tests zu verändern.

Prioritäten bedeuten:

- **P0 – Release Blocker:** Security, Datenintegrität, kaputter Kernworkflow, falsche Bestandsbuchung, unerreichbare notwendige Aktion oder realer technischer Blocker.
- **P1 – Closed-Beta Product Contract:** notwendig, damit die Closed Beta dem eingefrorenen Modell entspricht.
- **P2 – Post-Beta:** sinnvoll oder bereits beschlossen, aber für den Closed-Beta-Start nicht notwendig.
- **P3 – Future:** größere Zukunftsthemen.

Es gilt **Fundament vor Projektion**. Gemeinsame Fachwahrheiten werden einmal hergestellt und danach von Home, Profil, Statistik, Sammlung und Glocke gelesen. Eine sichtbare Funktion kann P2 sein, während ihre heute noch unwiederbringlich verlorene Datenerfassung P1 ist.

## 2. Unverändert nutzbare Fundamente

Folgende Systeme werden nicht neu gebaut, sondern nur gezielt erweitert oder gegen den Freeze verifiziert:

- Auth-, Session-, CSRF-, Ownership- und Account-Guards,
- Inventory-Read/-Write-, Availability- und Guard-Services,
- Trade-Lifecycle-Schema mit `trades`, `trade_positions`, Reservierungen, Versand, Empfang und Problemen,
- getrennte Versand-/Empfangsbuchung und atomare Reservierung,
- Freundschaften und Blocks,
- Albumprivacy `public/friends/private` und separater Tradepool als innere Ebene,
- typisierte Notification-Grundstruktur mit Ziel, Empfängerprüfung und Dedupe-Key,
- Bewertungen und Tradearchiv als technische Grundlage,
- drei Hauptbereiche und sichere Deep-Link-/Back-Navigation,
- fokussierter Offline-Tradevertrag der Stickerliste; Offlinefähigkeit selbst bleibt P2.

## 3. Arbeitspakete

### P0 – Release Blocker: 0 Pakete

Aus den Product Audits entsteht kein neuer nachgewiesener P0. Ein während der Umsetzung reproduzierter Security-, Integritäts- oder Kernworkflowdefekt wird nach Freeze-Regel separat als P0 eingeschoben und darf nicht als Produktwunsch getarnt werden.

### P1 – Closed-Beta Product Contract: 17 Pakete

#### CB-001 – Historischer Sammlungs-Datenvertrag

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-16).**

- **Ziel:** kanonische, idempotente Identitäten und Zeitfelder für Albumstart, Erstabschluss, Bestandsereignisse und Feed-Ereignisse definieren, ohne Mehrfachexemplare bereits umzusetzen.
- **Product-Contract-Bezug:** Audits 09, 11–13; CA-017, CA-020, CA-034, CA-035; PO-02/05/07.
- **Betroffen:** neue Migration(en), `App/Database/migrations/`, Inventory-/Albumservices, `user_albums`, `unlocked_trophies`; neue schlanke History-/Completion-Services wahrscheinlich.
- **Abhängigkeiten:** keine; Startpaket.
- **Datenänderung erforderlich:** JA. **Migration:** JA.
- **Tests:** Schemakontrakt, Unique-/FK-/Idempotenztests, Up-/Down-Migrationscheck auf Kopie, kein Current-State-Backfill.
- **Risiko:** **groß / hoch** – falsche Identität oder Deduplizierung vervielfacht spätere Ereignisse.
- **Abnahme:** ein dokumentierter Schema-/Servicevertrag besitzt stabile Schlüssel, klare UTC-Zeitsemantik, Transaktionsgrenze und keine automatische historische Interpretation.
- **Nicht Teil:** Mehrfachexemplare, sichtbare Statistik, Feed-UI, Migration realer Abschlüsse.

**Umsetzungsnachweis:** Migration V0013 ergänzt getrennte Tabellen für Albumhistorie,
positive Stickerzugänge, sparsame Fortschrittspunkte, Feed-Ereignisse und optionalen
Trophy-Triggerkontext. Alle Albumfakten referenzieren die bestehende stabile
`user_albums.id` zusammen mit dem geprüften User-/Albumkontext. Eindeutige Event-
und Source-Keys bilden den Retry-/Exactly-once-Vertrag; Zeitwerte werden von den
späteren Schreibern als explizite UTC-Zeitpunkte geliefert. Der neue
`HistoricalCollectionService` kapselt die derzeit zulässigen Writes und Reads,
ist aber bewusst in keinen bestehenden Mutationspfad eingebunden. Es gibt keinen
Backfill und keine sichtbare Produktänderung. Frischmigration, Upgrade einer
realistischen Kopie, Repeat-up, Down-Test V13→V12, Integritäts-/FK-Prüfung,
Startup-Smoke, 6 gezielte Tests sowie zwei vollständige Läufe mit jeweils 541
Tests und 0 Skips sind grün. CB-002 darf auf dieser Grenze ausschließlich die
Cutover-Writes integrieren; Abschlussorchestrierung und Trophy-Cutover verbleiben
bei CB-003 beziehungsweise CB-005. Vollständiger Nachweis:
`04-implementation-reports/CB-001-report.md`.

#### CB-002 – Historische Erfassung ab Cutover

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-16).**

- **Ziel:** ab Aktivierung Albumstart, positive Lifetime-Stickerzugänge und sparsame Fortschrittspunkte verlustfrei erfassen; keine erfundene Vergangenheit.
- **Product-Contract-Bezug:** Audit 12; CA-017/034; Prinzip „heute verlorenes Ereignis“.
- **Betroffen:** `App/services/inventory_write.py`, alle Bestandsmutationspfade in `App/webapp.py`, Trade-Receipt und Papierlisten-/Bulk-Pfade; neue History-Services.
- **Abhängigkeiten:** CB-001.
- **Datenänderung erforderlich:** JA. **Migration:** JA, nur Struktur/Cutover-Marker.
- **Tests:** jeder Write-Pfad erzeugt genau einen fachlichen Zugang beziehungsweise Fortschrittspunkt; Retry/Rollback; Abgaben reduzieren Lifetime nicht.
- **Risiko:** **groß / hoch** – verteilte Mutationspfade und Doppelzählungsgefahr.
- **Abnahme:** alle produktiven Zugangswege sind instrumentiert, Cutover ist sichtbar und Werte werden nicht aus Current State rückgerechnet.
- **Nicht Teil:** fertige Verlaufskurve, historische Herkunftsdetailanalyse, künstlicher Backfill.

**Umsetzungsnachweis:** V0014 ergänzt ausschließlich einen strukturierten,
eindeutigen Mutationsbeleg als Cutover- und Retry-Grenze. Neue Albumzuordnungen
erzeugen atomar genau einen Albumstart; bereits vorhandene Zuordnungen bleiben
ohne geschätzten Start. Einzel-, Set-, Inline-, Batch-, Undo- und physische
Tauschpfade sowie Lifecycle-Versand, Empfang, Teil-/Problemempfang und
Problemauflösung laufen über denselben History-Writer. Nur reale positive Deltas
erzeugen Lifetime-Zugänge; eine Änderung zwischen `0` und `>0` erzeugt einen
sparsamen Fortschrittspunkt mit Albumumfang. Browserformulare und Inline-Fetches
liefern stabile Mutations-IDs, Lifecycle-Pfade verwenden Trade-/Positions-IDs.
Current State, Mutationsbeleg, Zugang und Fortschrittspunkt liegen in derselben
SQLite-Transaktion beziehungsweise demselben Savepoint. UTC wird zentral als
`YYYY-MM-DDTHH:MM:SS.ffffffZ` serialisiert. Feed-, Completion- und Trophy-Writes
bleiben CB-007, CB-003 und CB-005 vorbehalten; es gibt keinen Backfill. Der
vollständige Nachweis steht in `04-implementation-reports/CB-002-report.md`.

#### CB-003 – Exactly-once-Albumabschluss

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-16).**

- **Ziel:** erster Übergang zu vollständig erzeugt atomar genau einen stabilen historischen Abschluss; Trophy- und Feed-Producer bleiben gemäß Pakettrennung CB-005 beziehungsweise CB-007.
- **Product-Contract-Bezug:** Audit 13; CA-020/035; PO-05/06/07.
- **Betroffen:** neuer Completion-Service, Inventory-Write-/Trade-Receipt-/Bulk-Pfade, `App/webapp.py`, Historyschema.
- **Abhängigkeiten:** CB-001; Integration mit CB-002, CB-005 und CB-007.
- **Datenänderung erforderlich:** JA, ausschließlich neue Laufzeitfakten. **Migration:** NEIN; V0013 enthält den benötigten Vertrag bereits vollständig.
- **Tests:** letzter fehlender Sticker, Bulk, Tradeempfang, Retry, paralleler Write, Bestandssenkung und erneutes 100 Prozent; Abschlusszeit bleibt stabil.
- **Risiko:** **groß / hoch**.
- **Abnahme:** Completion ist an der stabilen `user_albums.id` genau einmal und im selben Transaktionsmoment wie Bestand und CB-002-Historie gespeichert; spätere Bestandsreduktion oder erneute Vollständigkeit verändert sie nicht.
- **Nicht Teil:** Abschlussanimation, Albumlöschung, Mehrfachexemplare.

**Umsetzungsnachweis:** Der neue `FirstAlbumCompletionService` verwendet exakt
die bestehende Katalog-/Inventory-Wahrheit aus `all_codes`,
`InventoryReadService.progress` und dem kanonischen Albumumfang. Der zentrale
CB-002-Writer erfasst den Vorzustand innerhalb der `BEGIN IMMEDIATE`-/Savepoint-
Grenze und evaluiert nur eine positive Besitzstandsänderung `0→>0`; gespeichert
wird ausschließlich ein echter Übergang `unvollständig→vollständig`. V0013
dedupliziert bereits pro `user_album_id` und Completion-Key, deshalb war keine
neue Migration nötig. `completed_at` entspricht dem kanonischen UTC-Zeitpunkt
der auslösenden Mutation, deren Event-Key als strukturierte Evidence erhalten
bleibt. Bereits vollständige Vor-Cutover-Alben, reine Doppeltenerhöhungen,
Reduktionen, GETs und Startup erzeugen nichts. Einzel-, Inline-, Set-, Batch-,
Undo-, Offline-Trade-, normaler Receipt-, vollständiger Problemempfang-,
Teilempfangs- und Auflösungspfad sind abgedeckt. Trophy-, Feed-, Notification-,
Backfill- und UI-Cutover wurden ausdrücklich nicht vorgezogen. 17 gezielte und
177 kombinierte Tests sowie zwei Gesamtläufe mit jeweils 566 Tests und 0 Skips
sind grün; isolierter Daten-Smoke, Integrity, FKs und Startup ebenfalls. Details:
`04-implementation-reports/CB-003-report.md`.

#### CB-004 – Validierter Abschluss-Backfill

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-18).**

- **Ziel:** ausschließlich eindeutig gültige Abschluss-Trophäen in historische Abschlüsse überführen; Dry-run, Auditliste und Rollback ermöglichen.
- **Product-Contract-Bezug:** PO-07; CA-020; Datenrisiko `em24`.
- **Betroffen:** versionierte Datenmigration oder kontrolliertes Migrationsskript, Trophy-Katalog, Completiontabellen.
- **Abhängigkeiten:** CB-001, fachliche Katalogvalidierung aus CB-005.
- **Datenänderung erforderlich:** JA, ausschließlich bei explizitem Apply auf
  eine gewählte Datenbank. **Migration:** JA, V0016 erweitert nur den zulässigen
  strukturierten Source-Typ; sie enthält selbst keinen Backfill.
- **Tests:** positive/negative Fixtures, Namens-/Albumvalidierung, Dubletten, Dry-run, `em24` mit `2026-07-01 15:57:30` und aktuellem `709/728`.
- **Risiko:** **mittel / hoch** – irreversible falsche Historie vermeiden.
- **Abnahme:** nur validierte Evidenz wird übernommen; ohne freigegebenen
  EM24-Katalog bleibt auch der bekannte EM24-Abschluss bewusst unübernommen.
- **Nicht Teil:** Backfill aus 100 Prozent, Notifications, Mengen oder Schätzungen.

**Umsetzungsnachweis:** Der kontrollierte Operationspfad verlangt einen
expliziten Datenbankpfad und läuft standardmäßig read-only als deterministischer
JSON-Dry-run. Exakt gleiche Namen aus den freigegebenen WM26-/VfL-Katalogen,
eindeutige `user_albums`-Identität und belastbare UTC-Zeitsemantik sind zwingend;
Fuzzy Matching, Current State, Triggersticker und Projektionen sind ausgeschlossen.
Bestehende kanonische Fakten gewinnen, widersprüchliche Evidenz wird als
`CONFLICT` ohne Write ausgewiesen. Apply läuft atomar und idempotent mit stabilen
Legacy-Row-basierten Event-/Source-Keys. V0016 erlaubt dafür ausschließlich
`legacy_trophy_backfill` als zusätzlichen Source-Typ in
`canonical_trophy_unlocks`; die Migration interpretiert keine Daten.

Der Dry-run einer migrierten realistischen V7-Kopie klassifizierte 61/61 Zeilen:
21 `VALID_CANONICAL_TROPHY`, 25 `LEGACY_GLOBAL`, 6 `LEGACY_GENERIC`,
5 `NO_CANONICAL_CATALOG` und 4 `AMBIGUOUS`. Zulässig waren 21 kanonische
WM26-/VfL-Trophäen und 0 historische Abschlüsse; 40 Zeilen wurden verworfen.
Der bekannte EM24-Fall, Row 597 (`Album vollendet`, 2026-07-01 15:57:30), ist
wegen des fehlenden freigegebenen EM24-Katalogs `NO_CANONICAL_CATALOG/NONE`.
Apply auf einer zweiten Kopie erzeugte exakt 21/0 Zeilen, Repeat-Apply 0/0;
geschützte Tabellen, Feed, Notifications und Legacy blieben byteinhaltlich
unverändert. Details: `04-implementation-reports/CB-004-report.md` und
`04-implementation-reports/CB-004-backfill-audit.md`.

#### CB-005 – Persistente Album-Trophäen und gültiger Katalog

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-16).**

- **Ziel:** Views lesen dauerhaft gespeicherte, gültige albumbezogene Unlocks; globale/generische und unerreichte Ziele werden aus Closed-Beta-Projektionen ausgeschlossen.
- **Product-Contract-Bezug:** Audit 11; CA-012–016.
- **Betroffen:** `App/trophy_definitions.py`, Trophy-Helfer/Routen in `App/webapp.py`, neue persistente Unlocktabelle; `unlocked_trophies` bleibt Legacy read-only.
- **Abhängigkeiten:** CB-001; Completionintegration CB-003.
- **Datenänderung erforderlich:** JA, ausschließlich für neue Unlocks ab Cutover. **Migration:** JA, V0015 additiv und ohne Backfill; Legacyzeilen bleiben read-only.
- **Tests:** persistierter Unlock überlebt Mengenrückgang; Albumscope; verborgene unerreichte Ziele; keine globalen Zeilen in Zahlen; Completion-Dedupe.
- **Risiko:** **groß / hoch**.
- **Abnahme:** alle Closed-Beta-Reads verwenden dieselbe gültige Unlock-Projektion; keine dynamische Rücknahme.
- **Nicht Teil:** vollständige Kuratierung jedes Zukunftsalbums, XP, globale Achievements, finale Trophy-Optik.

**Umsetzungsnachweis:** V0015 ergänzt `canonical_trophy_unlocks` mit stabiler
Definition-ID, Nutzeralbum-/User-/Albumkontext, eindeutigem Event-Key,
Source-Referenz, kanonischem UTC-Zeitpunkt und optionalem Triggersticker. Die
Migration übernimmt keine Legacyzeile. Der explizite Closed-Beta-Katalog enthält
20 individuell definierte WM26- und 16 VfL-Trophäen; generische Fortschritts-,
globale und mangels freigegebener Kuratierung auch EM24-Trophäen sind nicht
kanonisch. Der zentrale CB-002-Writer ermittelt den Vorzustand innerhalb seines
Savepoints und persistiert neue Unlocks nur beim realen `0→>0`-Trigger. Die
Completion-Trophy konsumiert ausschließlich den exactly-once-Abschluss aus
CB-003. Retry, Rückgang und erneutes Erreichen verändern den ersten Unlock nicht;
ein Trophyfehler rollt Bestand, Historie und Completion gemeinsam zurück.
Albumseite, Albumpreview und Trophy-Schrank lesen ab V0015 persistierte gültige
Unlocks, offenbaren keine gesperrten Definitionen und schreiben bei GET nichts.
Verteilte Legacy-/`silent_reached`-Callbacks werden ab V0015 zu read-only
Popup-Adaptern; globale Writer sind deaktiviert. Profil und Statistik bleiben
gemäß Pakettrennung dokumentierte Legacy-Projektionen bis CB-013/014. Der
vollständige Nachweis steht in `04-implementation-reports/CB-005-report.md`.

#### CB-006 – Profilprivacy als äußeres Gate

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-18).**

- **Ziel:** `öffentlich/privat` vor alle fremden Profilprojektionen schalten und darunter Albumprivacy weiter anwenden; Tradepool nicht koppeln.
- **Product-Contract-Bezug:** PO-01; CA-010/011.
- **Betroffen:** Users-/Profileinstellungen, `App/services/album_privacy.py`, `collector_profiles.py`, Profil-/Albumrouten in `App/webapp.py`.
- **Abhängigkeiten:** CB-001 für historische Abschlussprojektion; fachlich unabhängig implementierbar, aber vor fremdem Feed/Profile-Release.
- **Datenänderung erforderlich:** JA. **Migration:** JA, sicherer Default und expliziter Cutover erforderlich.
- **Tests:** Owner/Freund/Fremder/Blockierter; privat verbirgt alle Sammlerdaten; öffentlich respektiert Albumstufen; Tradepool bleibt unabhängig; IDOR.
- **Risiko:** **mittel / hoch**.
- **Abnahme:** keine Route oder Feedprojektion umgeht das äußere Gate; Default leakt nichts.
- **Nicht Teil:** zusätzliche Section-Schalter oder neues Follower-Modell.

V0017 ergänzt `users.profile_privacy` additiv mit den ausschließlich zulässigen
Werten `public/private`; bestehende und neue Nutzer bleiben standardmäßig
`public`. Eine zentrale Policy lässt den Owner immer passieren, priorisiert
Blocks und öffnet private Sammlerwelten ausschließlich für bestätigte
gegenseitige Freunde. Erst danach greift unverändert die S27-Albumprivacy;
Tradepool, Matchbarkeit und laufende Trades bleiben unabhängig. Nicht erlaubte
Profilaufrufe werden vor Album-, Bestands-, Trophy-, Abschluss-, Rating- und
Tradeprojektionen auf eine minimale Identitäts-/Communitydarstellung reduziert.
Direkte Albumlinks benutzen dieselbe äußere Grenze. Migration, A–Z-Matrix,
isolierter realistischer Daten-Smoke sowie zwei vollständige Regressionen mit
je 628 Tests, 0 Fehlern und 0 Skips sind grün. Details stehen in
`04-implementation-reports/CB-006-report.md`.

#### CB-007 – Feed-Eventstore und minimale Producer

**Status: ABGESCHLOSSEN – technisch abgenommen (2026-08-18).**

- **Ziel:** persistente, deduplizierte Feedereignisse für eigene Reise, gegenseitige Freunde und zurückhaltende Sammlr News bereitstellen.
- **Product-Contract-Bezug:** PO-02/03; Audit 09; CA-007/034/035.
- **Betroffen:** neue Feedmigration/-service, Completion/Trophy-/Albumstartproducer, Freundschafts-/Privacyfilter, minimaler kontrollierter News-Schreibweg.
- **Abhängigkeiten:** CB-001, CB-003, CB-005, CB-006.
- **Datenänderung erforderlich:** JA. **Migration:** JA.
- **Tests:** strikte Zeitordnung, Dedupe, Freundschaft beidseitig, Privacy beim Lesen, privatisiertes Album, News-Dominanzgrenze, SmartMatches ausgeschlossen.
- **Risiko:** **groß / hoch**.
- **Abnahme:** reale Ereignisse sind chronologisch, privacy-sicher und genau einmal lesbar; kein Ableiten aus `user_activity` oder Notifications.
- **Nicht Teil:** Likes, Kommentare, algorithmische Sortierung, SmartMatches, komplexes Redaktionssystem.

V0018 operationalisiert den seit V0013 vorhandenen `feed_events`-Store additiv.
Albumstart und Erstabschluss schreiben innerhalb ihrer kanonischen
Transaktionsgrenzen; die Completion-Trophy erzeugt kein zweites Ereignis. Der
vollständig implementierte Trophy-Producer verwendet eine explizite, produktiv
leere Allowlist. Reads sortieren nach `occurred_at DESC, event_key DESC`, prüfen
aktuelle gegenseitige Freundschaft, Blocks, Profil- und Albumprivacy gebündelt
und nehmen höchstens eine kontrolliert veröffentlichte Sammlr News auf. Eigene
und Freundesereignisse belegen verfügbare Plätze zuerst. Notifications,
`user_activity`, Tradepool und SmartMatches sind keine Feedquellen. 11 gezielte,
156 kombinierte und zweimal 639 vollständige Tests sind fehler- und skipfrei;
isolierte Migration, Startup, Integrity und FK sind grün. Die lokale DB blieb
seit dem ersten CB-007-Prüfpunkt unverändert auf V7. Die Abweichung dieses
Prüfpunkts vom CB-006-Endhash wurde durch den Product Owner als beabsichtigte
reale Browser-/Nutzeränderung (`FWC4`) bestätigt, nicht durch CB-007 verursacht
und mit `082188...` als neuer legitimer Baseline geklärt. Details und der
vollständige Abnahmenachweis stehen in
`04-implementation-reports/CB-007-report.md`.

#### CB-008 – Closed-Beta Notification-Katalog

- **Status:** abgeschlossen und technisch abgenommen am 19. August 2026;
  Details in `04-implementation-reports/CB-008-report.md`. Der exakte
  Neun-Typen-Katalog, seine kanonischen Producer, Empfänger-/Dedupe-Regeln und
  der Ausschluss unerwünschter Writer sind umgesetzt. 11 gezielte, 199
  kombinierte und zweimal 650 vollständige Tests sind fehler- und skipfrei.
  Integrity/FK und isolierte V7→V18-Migration sind grün. Die vom Product Owner
  bestätigten manuellen Browseraktionen `problem_reported` und
  `problem_trade_closed` erklären die Baseline-Abweichung; die echte DB blieb
  auf V7 und `3eb9da3b...` ist die neue bestätigte Bestands-DB-Baseline.
- **Ziel:** nur eingefrorene Aufmerksamkeitstypen erzeugen; Bewertung, Ablehnung/nicht erfüllbare Anfrage und präzisierte Problemereignisse typisieren; unerwünschte Typen/Reminder stoppen.
- **Product-Contract-Bezug:** Audit 10; PO-09; CA-004/006/029/030.
- **Betroffen:** `App/services/typed_notifications.py`, Trade-/Problem-/Rating-/Friendship-Services, aktive Legacy-Schreibpfade in `App/webapp.py`.
- **Abhängigkeiten:** einheitliche Tradezustände CB-010.
- **Datenänderung erforderlich:** JA. **Migration:** NEIN – bestehende Tabelle und Dedupe-Infrastruktur; Altzeilen bleiben unangetastet.
- **Tests:** Empfänger, genau ein Event, Ziel/Ownership, keine Self-/Accepted-/Received-/Completed-/Friend-accepted-/Reminder-Meldungen, terminale Problemregel.
- **Risiko:** **groß / hoch**.
- **Abnahme:** eine Eventmatrix deckt jeden Producer ab; keine neuen `legacy`-Writes; kein Pingpong.
- **Nicht Teil:** Push, Kategorien-Einstellungen, Routine-Reminder.

#### CB-009 – Kleine Inbox: Read-State und Retention

- **Status:** abgeschlossen am 19. August 2026; Details im
  `04-implementation-reports/CB-009-report.md`.
- **Ziel:** sichtbare Einträge beim Öffnen sicher als gelesen behandeln, Badge synchron halten und gelesene Einträge nach spätestens 30 Tagen aus der Inbox entfernen.
- **Product-Contract-Bezug:** Audit 10; CA-031/032.
- **Betroffen:** Notificationservice, `/notifications`, Open-/Read-Routen, Badgeabfrage, Retentionjob/-cleanup.
- **Abhängigkeiten:** CB-008.
- **Datenänderung erforderlich:** JA. **Migration:** NEIN – vorhandene Felder
  `is_read` und `created_at` genügen.
- **Tests:** CSRF-/POST- oder sichere explizite Read-Mutation, nur sichtbare/eigene IDs, Pagination, Badge null, Ablaufgrenze, fachlich erledigte Ziele.
- **Risiko:** **mittel / mittel**.
- **Abnahme:** Inbox öffnen leert das Badge für sichtbare Einträge; einzelne Read-Buttons sind unnötig; Fachhistorien bleiben erhalten.
- **Nicht Teil:** unbegrenztes Archiv, Swipe-/Animationsdesign, Notification-Gruppierung.

#### CB-010 – Kanonische Trade-Erfolgsprojektion

- **Status:** abgeschlossen am 18. August 2026; Details im
  `04-implementation-reports/CB-010-report.md`.
- **Ziel:** eine gemeinsame Definition regulär erfolgreicher Deals und gerichteter erhalten/abgegeben-Mengen für Profil, Statistik und Historie schaffen.
- **Product-Contract-Bezug:** Audits 07/12; CA-019/027/028.
- **Betroffen:** neuer/erweiterter Trade-Read-Service, `collector_profiles.py`, `/statistik`, Tradearchiv; `trades`, `trade_positions`, Legacy-Requests read-only.
- **Abhängigkeiten:** vorhandener Lifecycle; keine neue Buchungslogik.
- **Datenänderung erforderlich:** NEIN. **Migration:** NEIN.
- **Tests:** beide Perspektiven, Problemendzustände, Legacy ohne Lifecycle, Mengenrichtung, Partnerdedupe, Rating erst qualifiziert.
- **Risiko:** **mittel / hoch**.
- **Abnahme:** jede Oberfläche zählt dieselbe Menge erfolgreicher Deals; Versand/Empfangsbuchungen bleiben unverändert korrekt.
- **Größter Trade:** Score ist verbindlich
  `max(given_quantity_total, received_quantity_total)`; beide Richtungswerte
  bleiben separat. Gleichstand: belastbarer Timestamp vor fehlendem/
  unparsebarem Timestamp, dann späteres `completed_at`, danach aufsteigend
  stabile kanonische Trade-ID als rein technischer Tie-Breaker.
- **Nicht Teil:** Lifecycle-Neubau, Cross-Album-UI, neue Bewertungsdetails.

#### CB-011 – Ausführbare Match-Priorisierung und unveränderte Anfrage

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-19).
- **Ziel:** albumbezogene Matches nach größtmöglicher gegenseitig realisierbarer Menge priorisieren und die ursprüngliche Anfrage bei Bestandsänderung unverändert blockieren.
- **Product-Contract-Bezug:** Audit 06/07; CA-025/026; PO-04.
- **Betroffen:** `top_match_optimization.py`, `trade_coverage.py`, `smart_trade_requests.py`, Tradekandidaten/-routen in `App/webapp.py`.
- **Abhängigkeiten:** vorhandene Availability-/Reservation-Services.
- **Datenänderung erforderlich:** NEIN. **Migration:** NEIN.
- **Tests:** Konfliktfreiheit, reservierte Mengen, Tie-Breaker, Recheck bei Annahme, kein Auto-Shrink, neuer Vorschlag verändert Original nicht.
- **Risiko:** **mittel / hoch**.
- **Abnahme:** Rangfolge entspricht realisierbarer Gegenseitigkeit; albumbezogener SmartTrade läuft vollständig in den gemeinsamen Lifecycle.
- **Nicht Teil:** Cross-Album-SmartTrades, regionale oder reputationsbasierte Sortierung.

**Umsetzungsnachweis:** Eine eigene read-only Matchprojektion bestimmt die
größtmögliche bilateral ausführbare Menge als Minimum der in beide Richtungen
aktuell effektiv verfügbaren unterschiedlichen Codes. Sie berücksichtigt
Reservations, Tradepool und Blocks, koppelt den Tradepool aber nicht neu an
Profilprivacy. Partner werden absteigend nach dieser Menge und danach stabil
nach Partner-ID sortiert; derselbe Vertrag speist Partnerliste und
konfliktfreie TopMatch-Pakete. Der alte parallele globale Optimierer wurde
entfernt. S22 speichert den bestätigten Anfrageinhalt weiterhin exakt und
blockiert Bestandsraces beim transaktionalen Recheck ohne Auto-Shrink oder
Stickerersetzung. Keine Migration, kein Backfill und keine Änderung an
CB-007/008/009/010. 10 gezielte Tests, kombinierte Fachsuiten und zwei
vollständige Läufe mit jeweils 666 Tests und 0 Skips sind grün; Integrity, FKs,
V7-Startup und Bestands-DB-Hash sind unverändert. Vollständiger Nachweis:
`04-implementation-reports/CB-011-report.md`.

#### CB-012 – sammlr.-Feed und Ablösung des operativen Home

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-21).
- **Ziel:** Home als strikt chronologische Projektion aus CB-007 rendern; Aufgaben, Prioritäten und laufende Trades entfernen.
- **Product-Contract-Bezug:** PO-02/03; CA-001–003/005/033/036.
- **Betroffen:** Home-Route/Renderer in `App/webapp.py`, `App/services/operational_home.py`, Home-CSS und Navigation.
- **Abhängigkeiten:** CB-006, CB-007, CB-008/009; Tradeaktionen bleiben unter Tauschen.
- **Datenänderung erforderlich:** NEIN. **Migration:** NEIN.
- **Tests:** Chronologie, drei Quellen, Privacy, Empty State, natürliche Ziele, keine Tasks/Trades/SmartMatches, 390-px Browser-Smoke.
- **Risiko:** **groß / hoch**.
- **Abnahme:** Home ist kein Arbeitskorb; Aufmerksamkeit und Operationen sind ohne Funktionsverlust über Glocke/Tauschen erreichbar.
- **Nicht Teil:** algorithmische Sortierung, Reaktionen, perfekte Kartenoptik.

**Umsetzungsnachweis:** `/` rendert ausschließlich die strikt chronologische,
privacy-geprüfte CB-007-Projektion aus `FeedEventService`; der alte operative
Home-Service wird nicht mehr konsumiert und bleibt nur bis CB-016 als
klassifizierter Legacypfad bestehen. Tasks, laufende Trades, SmartMatches und
alte Platzhalter sind vom Home entfernt; Glocke und Tauschen bleiben die
operativen Ziele. Keine Migration und kein Backfill. 11 gezielte CB-012-Tests,
eine kombinierte 326-Test-Fachsuite sowie zwei vollständige Läufe mit jeweils
711 Tests und 0 Skips sind grün. Nach einer im ersten echten 390-px-Safari-
Smoke gefundenen Box-Model-Regression korrigiert `border-box` ausschließlich
Feedkarten, Empty State und Bottom Navigation. Der Retest misst exakt 390 px
Dokumentbreite, vollständig innenliegende Elemente, erreichbare Glocke und
Tauschen sowie einen funktionierenden Feed-Deep-Link. Integrity, FKs,
V18-Startup auf isolierter Kopie und der unveränderte Bestands-DB-Hash sind
bestätigt. Vollständiger Nachweis:
`04-implementation-reports/CB-012-report.md`.

#### CB-013 – Sammlung und historische Abschlussprojektion

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-20).
- **Ziel:** vollständige Alben in der normalen Sammlung belassen und zusätzlich reduzierte historische Abschlusskarten nach Datum zeigen.
- **Product-Contract-Bezug:** Audit 13; CA-036/037.
- **Betroffen:** Sammlung-/Albumkarten in `App/webapp.py`, Completion-Read-Service, Styles.
- **Abhängigkeiten:** CB-003/004.
- **Datenänderung erforderlich:** NEIN. **Migration:** NEIN.
- **Tests:** aktueller Zustand vs Geschichte, sinkender Bestand, Reihenfolge, keine operativen Metriken, aktives Album als Ziel.
- **Risiko:** **mittel / mittel**.
- **Abnahme:** dasselbe aktive Album bleibt benutzbar und besitzt bei Historie genau eine zusätzliche Karte mit stabilem Datum.
- **Nicht Teil:** Albumlöschung und Read-only-Historienansicht.

**Umsetzungsnachweis:** Die neue read-only `CollectionProjectionService` trennt
aktive `user_albums` als Current State strikt von kanonischen Completion-Fakten
in `historical_album_records`. Alle aktiven Alben bleiben in der normalen
Sammlung; ausschließlich CB-003- beziehungsweise validierte CB-004-Abschlüsse
erzeugen zusätzlich eine reduzierte Karte mit Identität, Status und Datum.
Heutige 100 Prozent, Legacy-Trophäen und operative Kennzahlen werden nicht als
Historie interpretiert. Sortierung ist `completed_at DESC, user_album_id DESC`;
fremde Projektionen verwenden ProfilePrivacy, Albumprivacy und Blocks. Keine
Migration, kein Backfill und keine Vorziehung von Profil, Statistik, Home oder
Legacy-Cutover. 10 gezielte Tests, kombinierte Fachsuiten und zwei vollständige
Läufe mit jeweils 676 Tests und 0 Skips sind grün; Integrity, FKs, V18-Startup
auf isolierter Kopie und der unveränderte Bestands-DB-Hash sind bestätigt.
Vollständiger Nachweis: `04-implementation-reports/CB-013-report.md`.

#### CB-014 – Profil-/Account-Trennung und öffentliche Projektion

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-20).
- **Ziel:** Profil auf Identität, Vertrauen, Freunde, gültige Trophäen und Abschlüsse reduzieren; Accountverwaltung separat halten; PO-08-Zahlen verwenden.
- **Product-Contract-Bezug:** PO-01/08; CA-008/009/011/016/018.
- **Betroffen:** `collector_profiles.py`, Profilrouten/-renderer, Account-/Einstellungsnavigation, Privacyservice.
- **Abhängigkeiten:** CB-005, CB-006, CB-010, CB-013.
- **Datenänderung erforderlich:** NEIN. **Migration:** NEIN.
- **Tests:** eigenes/fremdes/privates Profil, vier Kernzahlen, keine Doppelten/globalen Missing, keine fremde Detailstatistik, Albumfilter.
- **Risiko:** **groß / hoch**.
- **Abnahme:** öffentlich erscheinen nur erlaubte Identitätsdaten; Accountaktionen dominieren das Profil nicht.
- **Nicht Teil:** Avatar-/Ausweis-Perfektion, Bewertungsdetails, Partnerzahl.

**Umsetzungsnachweis:** `CollectorProfileService` liefert nach dem äußeren
CB-006-Gate nur Identität, die vier PO-08-Aggregate, privacy-gefilterte
Albumidentitäten, kanonische CB-013-Abschlüsse und gültige kanonische
CB-005-Trophäen. Current-State-Doppelte/Missing, Legacy-Trophäen,
Bewertungsdetails, Partnerzahlen und profilbezogenes Tradepotenzial sind keine
öffentlichen Profildaten. Account- und Sicherheitsaktionen liegen getrennt
unter `/account`; der Tradepool bleibt unverändert. Keine Migration und kein
Backfill. 12 gezielte Tests, kombinierte Fachsuiten sowie zwei vollständige
Läufe mit jeweils 688 Tests und 0 Skips sind grün; Integrity, FKs,
V18-Startup-Smoke und der unveränderte Bestands-DB-Hash sind bestätigt.
Vollständiger Nachweis: `04-implementation-reports/CB-014-report.md`.

#### CB-015 – Statistikprojektion Current State versus Karriere

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-20).
- **Ziel:** Bestandswerte albumbezogen halten und historische Karriere ausschließlich aus kanonischen History-, Completion-, Trophy- und Tradeprojektionen lesen.
- **Product-Contract-Bezug:** Audit 12; CA-016–021.
- **Betroffen:** `/statistik`, Albumstatistik, neue Historyreads, `collector_profiles.py` nur über gemeinsame Services.
- **Abhängigkeiten:** CB-002–005, CB-010.
- **Datenänderung erforderlich:** NEIN. **Migration:** NEIN nach den Fundamentmigrationen.
- **Tests:** nicht sinkende Lifetime-Zugänge ab Cutover, gerichtete Trades, stabile Abschlüsse, keine globalen Missing/Doppelten, unbekannte Historie klar gekennzeichnet.
- **Risiko:** **groß / hoch**.
- **Abnahme:** keine Kennzahl nennt momentane Menge „Lebenszeit“; Profil und Statistik teilen Definitionen.
- **Nicht Teil:** vollständige Fortschrittskurve, Rankings, künstlicher Altbestand-Backfill.

**Umsetzungsnachweis:** `StatisticsProjectionService` trennt den heutigen,
albumbezogenen Bestand strikt von Karrierefakten. Aktueller Fortschritt,
vorhandene, fehlende und doppelte Sticker stammen ausschließlich aus dem
kanonischen Inventory-Read. Karrierewerte lesen ausschließlich CB-002-
Zugänge, CB-003/004-Abschlüsse, CB-005-Trophäen und CB-010-Trades; gerichtete
Trade-Mengen bleiben getrennt. Vor-Cutover-Historie wird als unbekannt
gekennzeichnet und weder aus aktuellem Bestand noch aus Legacy-Trophäen
rekonstruiert. Die CB-014-Profilprojektion teilt die erfolgreiche-Trade-
Definition über denselben Service. Keine Migration und kein Backfill. 12
gezielte Tests, drei kombinierte Fachsuiten sowie zwei vollständige Läufe mit
jeweils 700 Tests und 0 Skips sind grün; Integrity, FKs, V18-Startup-Smoke und
der unveränderte Bestands-DB-Hash sind bestätigt. Vollständiger Nachweis:
`04-implementation-reports/CB-015-report.md`.

#### CB-016 – Kontrollierter Legacy-Cutover

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-21).
- **Ziel:** ersetzte Schreib-/Read-/UI-Pfade nach erfolgreichen Verbraucherpaketen entfernen, ersetzen oder ausblenden, ohne historische Evidenz zu vernichten.
- **Product-Contract-Bezug:** CA-001–037; Legacy-Matrix in Abschnitt 7.
- **Betroffen:** `operational_home.py`, Trophy-Renderer/-Definitionen, Notificationproducer/-renderer, dynamische Vitrine/Statistik, veraltete Tests und Styles.
- **Abhängigkeiten:** CB-005, CB-008/009, CB-012–015.
- **Datenänderung erforderlich:** NEIN für Code-Cutover; Altzeilen bleiben klassifiziert. **Migration:** NEIN/UNKLAR je Cleanup.
- **Tests:** keine Legacy-Schreibpfade, keine tote Navigation, kein Verlust fachlicher Historie, Snapshot-/Browservergleich.
- **Risiko:** **mittel / hoch**.
- **Abnahme:** jeder Legacypfad besitzt explizites `REMOVE/REPLACE/HIDE/MIGRATE/DEFER`; keine Parallelwahrheit bleibt aktiv.
- **Nicht Teil:** physisches Löschen sämtlicher Legacydaten ohne Retentions-/Recoveryentscheidung.

**Umsetzungsnachweis:** Der nicht mehr konsumierte operative Home-Service und
der generische Notification-Writer wurden entfernt. Profil und Sammlung laufen
über die CB-013-/CB-014-Projektion; der Pre-History-Bestandsfallback ist
entfallen. Pre-V15-Trophy-Writer sowie dynamische, globale und generische
Trophy-Reads/-Renderer sind abgeschaltet beziehungsweise entfernt und verhalten
sich auf alten Schemas fail-closed. Sichere Redirects, kanonische
Popup-/Tradeadapter, CB-010-Legacy-Erfolgsreads und die lesbare Notification-
Historie bleiben als klassifizierte Kompatibilitätspfade erhalten. Es gab keine
Migration und keine Änderung der echten V7-Bestands-DB. 7 gezielte Tests, drei
kombinierte Fachsuiten, vier Privacy-Negativtests und zwei vollständige Läufe
mit jeweils 704 Tests sind grün; Integrity, FKs, isolierter V7→V18-Startup-
Smoke, zentrale HTTP-Pfade, SHA-256 und `git diff --check` sind bestätigt.
Vollständiger Nachweis: `04-implementation-reports/CB-016-report.md`.

#### CB-017 – Integrierter Closed-Beta-RC-Nachweis

- **Status:** ABGESCHLOSSEN – technisch abgenommen (2026-08-21).
- **Ziel:** alle Contract-, Service-, Privacy-, Browser- und Regressiontests als reproduzierbares Gate ausführen und reale Kernworkflows auf Mobile beweisen.
- **Product-Contract-Bezug:** gesamter Freeze; Gates 1–6.
- **Betroffen:** neue/angepasste Tests erst bei Umsetzung, Testdaten, Browser-E2E, Releasecheckliste; kein Produktcode als Selbstzweck.
- **Abhängigkeiten:** CB-001–016.
- **Datenänderung erforderlich:** NEIN in Produktion. **Migration:** NEIN.
- **Tests:** vollständige Strategie aus Abschnitt 9, insbesondere Tradekette und Exactly-once-Abschlusskette.
- **Risiko:** **groß / hoch** – Integration über viele Projektionen.
- **Abnahme:** alle sechs Gates grün, reale 390-px-Browser-Smokes, Migrationsprobe auf Datenkopie, keine offenen P0 und keine ungeklärte P1-Abweichung.
- **Nicht Teil:** Beweis sämtlicher Post-Beta-/Future-Funktionen.

**Umsetzungsnachweis:** Alle sechs integrierten Gates sind grün. Die
Contract-, Service-, Privacy-/Auth-, Mehrnutzer-/Race- und Recovery-Suites
sowie zwei vollständige Regressionen mit jeweils 706 Tests und 0 Skips sind
erfolgreich. Eine isolierte Kopie der realen V7-Bestands-DB wurde mit Backup
auf V18 migriert, ohne unzulässigen Backfill oder Verlust bestehender Daten;
Restore auf V7, Integrität, Foreign Keys, Startup und zentrale HTTP-Pfade sind
bestätigt. Im echten Safari bei 390 px wurde die komplette mobile Kernmatrix
einschließlich Quantity-Write, Glocke, Feed-Deep-Link und einer vollständigen
SmartTrade-Kette über zwei Nutzer geprüft. Der Smoke fand zwei gleichartige
responsive CSS-Ursachen: `width:100%` auf mobilen Quick-Cards im
`content-box`-Modell und ein nicht schrumpfendes vier-spaltiges Statistikgrid.
Der minimale Fix setzt die betroffenen Komponenten auf `border-box/min-width:0`
und die Statistik bei Mobile auf ein 2×2-Grid; der Wiederholungssmoke misst auf
allen Kernseiten `scrollWidth = innerWidth = 390`. Die echte V7-Bestands-DB
blieb unverändert. Vollständiger Nachweis:
`04-implementation-reports/CB-017-report.md`.

### P2 – Post-Beta: 9 Pakete

#### CB-101 – Einzelalbum-Löschung mit Historienwahl

- **Ziel:** aktives Album löschen und Abschlussgeschichte explizit bewahren oder mitlöschen.
- **Bezug/Betroffen:** PO-05/06, CA-021/022; Album-, Inventory-, Privacy-, Trophy-, Feed- und Completionservices/-routen.
- **Abhängigkeiten:** CB-003/013/015. **Datenänderung:** JA. **Migration:** wahrscheinlich NEIN nach CB-001.
- **Tests:** beide Wahlpfade, Bestätigung, Ownership, Trade-/Reservation-Konflikte, Statistikzählung. **Risiko:** groß/hoch.
- **Abnahme:** keine automatische Wahl; bewahrte Karte ist nicht anklickbar und zählt weiter. **Nicht Teil:** Read-only-Historienansicht.

#### CB-102 – Vollständige kuratierte Trophy-Kataloge

- **Ziel:** individuelle geprüfte Kataloge für alle unterstützten Alben vervollständigen.
- **Bezug/Betroffen:** Audit 11, CA-013; Trophydefinitionen und Assets.
- **Abhängigkeiten:** CB-005. **Datenänderung:** JA/UNKLAR. **Migration:** nur bei ID-Mapping.
- **Tests:** Katalogvalidierung, eindeutige IDs, keine generischen Fallbacks. **Risiko:** mittel/mittel.
- **Abnahme:** jedes unterstützte Album besitzt freigegebenen Inhalt. **Nicht Teil:** globale Trophäen.

#### CB-103 – Historische Statistik-UI

- **Ziel:** Albumstart, Sammeldauer, Lifetime-Zugänge und eine belastbare Fortschrittskurve sichtbar machen.
- **Bezug/Betroffen:** Audit 12, CA-017; Statistik-/Albumstatistik-Renderer.
- **Abhängigkeiten:** ausreichend Daten aus CB-002/003. **Datenänderung:** NEIN. **Migration:** NEIN.
- **Tests:** Cutoverkennzeichnung, Zeiträume, keine erfundene Vergangenheit. **Risiko:** mittel/mittel.
- **Abnahme:** UI unterscheidet vollständig/unvollständig bekannte Historie. **Nicht Teil:** Rankings oder Prognosen.

#### CB-104 – Feed- und Notification-Bündelung

- **Ziel:** mehrere fachlich zusammengehörige Ereignisse verständlich bündeln.
- **Bezug/Betroffen:** Audits 09/10; Feed-/Notification-Readmodels.
- **Abhängigkeiten:** CB-007–009. **Datenänderung:** NEIN/UNKLAR. **Migration:** UNKLAR.
- **Tests:** keine versteckte Handlung, stabile Deduplizierung. **Risiko:** mittel/mittel.
- **Abnahme:** weniger Kartenflut ohne Informationsverlust. **Nicht Teil:** algorithmisches Ranking.

#### CB-105 – Offlinefähige Stickerliste

- **Ziel:** fokussierten Tauschzettel bei schlechter Verbindung nutzbar machen.
- **Bezug/Betroffen:** Audit 05; Stickerlistenroute, Cache/Sync, Inventory-Konflikte.
- **Abhängigkeiten:** stabiler Inventoryvertrag. **Datenänderung:** UNKLAR. **Migration:** UNKLAR.
- **Tests:** Offline/Online-Sync, Konflikte, Doppelbuchung. **Risiko:** groß/hoch.
- **Abnahme:** physischer Trade wird nach Reconnect genau einmal gebucht. **Nicht Teil:** voller App-Offlinebetrieb.

#### CB-106 – Share-/Exportdarstellungen der Stickerliste

- **Ziel:** dieselbe Fehlende-/Doppelte-Datenbasis als Bild/Download/QR ausgeben.
- **Bezug/Betroffen:** Audit 05; Export-/Share-Renderer.
- **Abhängigkeiten:** stabiler Stickerlistenvertrag. **Datenänderung:** NEIN/UNKLAR. **Migration:** NEIN.
- **Tests:** Privacy, aktuelle Daten, sichere öffentliche Ziele. **Risiko:** mittel/mittel.
- **Abnahme:** keine zweite fachliche Liste entsteht. **Nicht Teil:** Social Network.

#### CB-107 – Historische Read-only-Abschlussansicht

- **Ziel:** optionales späteres Ziel für bewahrte Abschlüsse ohne aktives Album.
- **Bezug/Betroffen:** PO-06; Completion-Readmodel/-route.
- **Abhängigkeiten:** CB-101. **Datenänderung:** NEIN/UNKLAR. **Migration:** NEIN.
- **Tests:** Privacy, tote Albumreferenz, keine Bestandswiederherstellung. **Risiko:** mittel/mittel.
- **Abnahme:** Geschichte ist lesbar, aber nicht operativ. **Nicht Teil:** Closed Beta.

#### CB-108 – Profil-/Bewertungsvertiefung

- **Ziel:** spätere Sammlr-Ausweis-, Avatar- und Bewertungsdetails ergänzen.
- **Bezug/Betroffen:** Audit 08; Profil-/Ratingservices und Medienhandling.
- **Abhängigkeiten:** CB-006/014. **Datenänderung:** JA/UNKLAR. **Migration:** UNKLAR.
- **Tests:** Uploadsicherheit, Privacy, Moderation. **Risiko:** mittel/hoch.
- **Abnahme:** Ergänzungen bleiben Identität statt Accountverwaltung. **Nicht Teil:** vollständige fremde Statistik.

#### CB-109 – Cross-Album-SmartTrades End-to-End

- **Ziel:** mehrere Alben in Vorschlag und Anfrage durch den gemeinsamen Lifecycle führen.
- **Bezug/Betroffen:** PO-04, CA-024; Match-, Request-, Positions- und Trade-UI.
- **Abhängigkeiten:** CB-011 und stabile `trade_positions`. **Datenänderung:** JA/UNKLAR. **Migration:** UNKLAR.
- **Tests:** Multi-Album-Verfügbarkeit, Reservierung, Versand/Empfang je Position, Privacy/Tradepool. **Risiko:** groß/hoch.
- **Abnahme:** kein eigener Lifecycle; alle Positionen bleiben albumbezogen nachvollziehbar. **Nicht Teil:** Closed-Beta-Kernpfad.

### P3 – Future: 3 Pakete

#### CB-201 – Echte Mehrfachexemplare

- **Ziel:** Typ und konkrete Albuminstanz für Inventory, Privacy, Trophy und Abschluss trennen.
- **Bezug/Betroffen:** CA-023; gesamtes Album-/Inventorymodell.
- **Abhängigkeiten:** historische Verträge müssen exemplarbereit bleiben. **Datenänderung/Migration:** JA/JA.
- **Tests/Risiko:** vollständige Datenmodell-, URL-, Tradepool- und Migrationssuite; groß/hoch.
- **Abnahme:** mehrere Exemplare desselben Typs besitzen getrennte Geschichte. **Nicht Teil:** Closed Beta/Post-Beta-Kurzfrist.

#### CB-202 – Push-Zustellung

- **Ziel:** konsolidierte fachliche Notifications über einen optionalen Pushkanal zustellen.
- **Bezug/Betroffen:** Audit 10; Notification-/Deliveryservice.
- **Abhängigkeiten:** CB-008/009. **Datenänderung/Migration:** JA/UNKLAR.
- **Tests/Risiko:** Consent, Token, Dedupe, Zustellfehler; groß/hoch.
- **Abnahme:** Push erzeugt keine zweite Ereignislogik. **Nicht Teil:** Beta.

#### CB-203 – Erweiterte Match-/Reputationssignale

- **Ziel:** regionale, qualitative und vertiefte Reputationssignale nach Nutzungsdaten prüfen.
- **Bezug/Betroffen:** Audit 06/08; Matching/Profile.
- **Abhängigkeiten:** CB-011. **Datenänderung/Migration:** UNKLAR/UNKLAR.
- **Tests/Risiko:** Fairness, Privacy, Ranking; groß/hoch.
- **Abnahme:** reale Daten belegen Nutzen. **Nicht Teil:** Kernsortierung der Closed Beta.

## 4. Empfohlene Implementierungsreihenfolge

1. **CB-001** historischer Datenvertrag.
2. **CB-002** Erfassung ab Cutover.
3. **CB-003** Exactly-once-Abschluss.
4. **CB-005** persistente Trophy-Wahrheit und Katalogvalidität.
5. **CB-004** kontrollierter Abschluss-Backfill.
6. **CB-010** kanonische Trade-Erfolgsprojektion.
7. **CB-006** äußeres Privacy-Gate.
8. **CB-007** Feedstore und Producer.
9. **CB-008** Notification-Katalog.
10. **CB-009** Inbox-Semantik und Retention.
11. **CB-011** Match-Priorisierung und Anfrageimmutabilität.
12. **CB-013** Sammlung/Abschlussprojektion.
13. **CB-014** Profil-/Account-/öffentliche Projektion.
14. **CB-015** Statistikprojektion.
15. **CB-012** Home durch Feed ersetzen, sobald Glocke/Tauschen alle notwendigen Aktionen tragen.
16. **CB-016** Legacy-Cutover nach erfolgreichen Ersatzprojektionen.
17. **CB-017** integrierter RC-Nachweis.

CB-006 und CB-010 können nach CB-001 parallel vorbereitet werden; produktiv freigegeben werden ihre Verbraucher erst an den genannten Gates. P2/P3 beginnen nicht, solange dadurch ein P1 verzögert oder der Freeze geöffnet würde.

## 5. Historische Daten vor Closed Beta

| Historisierung | Einstufung | Minimaler Startvertrag | Kein Backfill aus |
|---|---|---|---|
| erster Albumabschluss | **MUSS VOR BETA BEGINNEN** | stabiler Zeitpunkt, Album/User-Identität, Exactly-once, Trophy-/Feed-Dedupe | aktuellem 100%-Bestand |
| Albumstart | **MUSS VOR BETA BEGINNEN** | Zeitpunkt bei neuer Zuordnung ab Cutover | `user_albums.id`, heutiger Mitgliedschaft |
| Lifetime-Stickerzugänge | **MUSS VOR BETA BEGINNEN** | positive bestätigte Zugänge je Mutation, niemals durch Abgabe senken | aktueller `quantity` |
| Fortschrittsdaten für spätere Kurve | **MUSS VOR BETA BEGINNEN** | sparsamer Punkt bei fachlicher Fortschrittsänderung, nicht jede Read-Anfrage | künstlicher Interpolation |
| Feed-Ereignisse | **MUSS VOR BETA BEGINNEN** | reale, typisierte, deduplizierte Events mit Privacyprüfung | Notifications oder `user_activity` |
| Trophy-Triggersticker | **MUSS VOR BETA BEGINNEN, WENN EINDEUTIG** | nullable Triggerreferenz nur bei kausal eindeutigem Sticker; sonst bewusst `NULL` | URL-Parameter, geratenem letzten Sticker |

Die sichtbare Verlaufskurve und tiefe Statistik dürfen P2 bleiben. Ihre Datengrundlage darf nicht erst dann beginnen.

## 6. Bestandsdatenstrategie

| Daten | Klasse | Vertrag |
|---|---|---|
| Inventories | **KEEP** | Current State und Buchungsquelle; nie Lebenszeitgeschichte |
| Lifecycle-Trades/-Positionen/-Versand/-Empfang/-Probleme | **KEEP** | kanonische operative Tradebasis |
| Legacy-Trades | **LEGACY_READ_ONLY** | für vorsichtige Erfolgs-/Mengenprojektion; keine erfundenen Zeitpunkte |
| gültige Trophy-Unlocks | **VALIDATE_BEFORE_MIGRATION** | albumbezogene Unlocks erhalten; Namen/Katalog vor Mapping prüfen |
| globale/generische Trophy-Zeilen | **LEGACY_READ_ONLY** | nicht in Closed-Beta-Zahlen; später gesondert entscheiden |
| typisierte Notifications | **TRANSFORM** | Ziel-/Empfängerstruktur behalten, Katalog und Retention konsolidieren |
| Legacy-Notifications | **REMOVE_LATER** aus Inbox nach Retention | keine semantische Rekonstruktion; aktive Legacy-Writer stoppen |
| Freundschaften und Blocks | **KEEP** | gegenseitige Beziehung und Sichtbarkeitsgrundlage |
| Albumprivacy/Tradepool | **KEEP** | innere Albumebene; äußeres Profil-Gate ergänzen |
| Albumzuordnungen | **TRANSFORM** | Startzeit ab Cutover; noch keine Mehrfachexemplarinterpretation |
| Abschluss-Trophy-Evidenz | **VALIDATE_BEFORE_MIGRATION** | nur eindeutige gültige Abschluss-Trophy übernimmt Datum |
| Current-State-100-Prozent | **DO_NOT_BACKFILL** | kein historisches Datum ableiten |
| aktueller Bestand/Notifications/Request-Erstellung | **DO_NOT_BACKFILL** | keine Karriere-, Feed- oder Abschlussgeschichte erfinden |

Der bekannte Fall `em24` ist verbindliche Migrationsfixture: `Album vollendet`
am **01.07.2026**, aktueller Bestand **709/728**. CB-004 hat die Evidenz separat
geprüft. Da CB-005 keinen freigegebenen EM24-Katalog besitzt, ist eine eindeutige
Validierung nicht möglich: kein Trophy- und kein Completion-Backfill. Der heutige
Current State bleibt ausdrücklich bedeutungslos; eine spätere Übernahme setzt
eine neue explizite Katalog-/Product-Owner-Entscheidung voraus.

## 7. Legacy-Abbauplan

| Legacythema | Maßnahme | Zielpaket | Begründung |
|---|---|---|---|
| Home „Das braucht dich“ | **REPLACE** | CB-012/016 | Glocke besitzt Aufmerksamkeit, Feed besitzt Chronologie |
| laufende Trades auf Home | **REMOVE** | CB-012/016 | operative Heimat ist Tauschen |
| globale Trophäen | **HIDE** + **DEFER** | CB-005/016 | nicht Teil des kurzfristigen Modells; Daten nicht blind löschen |
| generischer Trophy-Fallback | **REMOVE** | CB-005/016 | nur kuratierte Albumkataloge |
| dynamische Trophy-Reads | **REPLACE** | CB-005 | persistierte Unlocks sind Wahrheit |
| Locked-/Next-Trophy-Logik | **HIDE/REMOVE** | CB-005/016 | unerreichte Ziele bleiben verborgen |
| globale Missing-/Doppeltenstatistik | **REMOVE** | CB-015/016 | Current State gehört zum Album |
| Doppelte als Profilkennzahl | **REMOVE** | CB-014/016 | keine repräsentative Kernzahl |
| dynamische Vitrine | **REPLACE** | CB-003/013/014 | historischer Abschluss statt aktuelle 100 Prozent |
| operative Vitrinenmetriken | **REMOVE** | CB-013 | Abschlusskarte ist historische Projektion |
| automatische Paketverkleinerung | **REMOVE** | CB-011/016 | ursprüngliche Anfrage bleibt unverändert und blockiert |
| Bewertung nach Versand | **REPLACE** | CB-010/016 | erst nach qualifiziertem Abschluss |
| unerwünschte Notification-Typen | **REMOVE** als Writer, **MIGRATE/HIDE** als Altbestand | CB-008/016 | kleine Inbox |
| Routine-Reminder | **REMOVE** als Closed-Beta-Writer, **DEFER** | CB-008 | nur nach Nutzungsdaten neu entscheiden |
| unbegrenzte Notification-Historie | **REPLACE** | CB-009 | gelesene Meldungen höchstens 30 Tage sichtbar |
| einzelne „Als gelesen“-Buttons | **REMOVE** | CB-009/016 | Öffnen der Inbox ist Read-Aktion |

## 8. Voraussichtliche Migrationen

1. History-/Completion-/Feed-Schema mit Unique-, Zeit- und Dedupe-Verträgen (**CB-001**).
2. Cutoverfelder beziehungsweise Eventtabellen für Albumstart, Lifetime-Zugänge und Fortschritt (**CB-002**).
3. Exactly-once-Abschlussreferenzen und optionale Triggerreferenz (**CB-003/005**).
4. kontrollierter, vorab validierter Abschluss-Backfill (**CB-004**).
5. globales Profilprivacy-Feld mit leak-sicherem Default (**CB-006**).
6. Feed-Eventstore einschließlich Sammlr-News-Typ (**CB-007**).
7. Notification-Katalog-/Index-/Retentionanpassung nur soweit schemaabhängig (**CB-008/009**).

Jede Migration wird zuerst gegen eine Datenbankkopie, mit Backup, Dry-run/Inventur, Vor-/Nachzählungen und Rollbackpfad geprüft. P2/P3-Migrationen werden nicht vorgezogen.

## 9. Teststrategie

### A. Contract Tests

- Rollen von Sammlung, Feed, Tauschen, Glocke und Profil.
- Notification-Eventmatrix und Feed-Würdigkeit.
- Privacy-Gate plus Albumfilter.
- Current State versus historische Karriere.
- Anfrageimmutabilität, Fairness und Bewertungszeitpunkt.

### B. Service Tests

- Inventorymutationen und Historycapture genau einmal.
- Completion/Trophy/Feed in gemeinsamer Transaktionsgrenze.
- Reservations-, Shipping-, Receipt- und Problemzustände.
- Trade-Erfolgsprojektion aus beiden Nutzerperspektiven.
- Feed-/Notification-Dedupe und Retention.

### C. Authorization-/Privacy-Tests

- Owner, gegenseitiger Freund, Fremder, blockierter Nutzer und privates Profil.
- direkte URLs, Zielnavigation, IDOR, CSRF und Sessiongrenzen.
- nachträgliche Privatisierung bereits gespeicherter Feedereignisse.

### D. Browser-/E2E-Smokes

- reale Mobile-Viewportgröße 390 px; keine unerreichbare Hauptaktion oder Dock-/Bottom-Nav-Überdeckung.
- vollständige Kette: Album nutzen → Bestand pflegen → SmartMatch → Anfrage → Annahme → Reservierung → Versand → Ausbuchung → Empfang → Einbuchung → Abschluss → Bewertung → korrekte Statistik/Profile.
- Glocke → konkretes Ziel; Home bleibt chronologisch und frei von operativen Duplikaten.

### E. Regression Tests

- echte CSRF-/Quantity-Browserrequests und sichtbare Fehlermeldungsquelle.
- Bestandsbuchung exakt bei eigenem Versand/eigenem Empfang.
- nicht erfüllbare Anfrage erzeugt keine Reservierung und wird nicht verkleinert.
- letzter fehlender Sticker → Abschluss exactly once → Trophy exactly once → Feed exactly once → stabiles Datum.
- `em24` bleibt historisch abgeschlossen trotz `709/728`.

## 10. Closed-Beta-Gates

### GATE 1 – DATA CONTRACT

- **Voraussetzungen:** CB-001–005.
- **Tests:** Migration auf Kopie, Schema-/Service-/Idempotenztests, `em24`-Fixture.
- **Abnahme:** History beginnt verlustfrei; Abschluss/Trophy/Feed besitzen eine gemeinsame Wahrheit; kein erfundener Backfill.

### GATE 2 – TRADE CORE

- **Voraussetzungen:** CB-008, CB-010, CB-011 sowie vorhandener Lifecycle.
- **Tests:** kompletter Trade-Serviceflow, Reservierung, Versand/Empfang, Problem, Bewertung, Mengenrichtung.
- **Abnahme:** albumbezogener SmartTrade ist ausführbar; keine falsche Buchung, kein Auto-Shrink, eine Erfolgsdefinition.

### GATE 3 – PRODUCT PROJECTIONS

- **Voraussetzungen:** CB-007, CB-009, CB-012–015.
- **Tests:** Contract-/Projectiontests und reale Navigation.
- **Abnahme:** Feed, Sammlung, Glocke, Profil und Statistik lesen gemeinsame Wahrheiten und duplizieren keine operative Zuständigkeit.

### GATE 4 – PRIVACY / AUTH

- **Voraussetzungen:** CB-006 und alle fremden Verbraucher.
- **Tests:** Authorization-/Privacy-Matrix, direkte URLs, CSRF/Session/Ownership.
- **Abnahme:** privates Profil leakt keine Sammlerinformationen; öffentliches Profil respektiert Albumfreigaben.

### GATE 5 – MOBILE E2E

- **Voraussetzungen:** CB-001–016 integriert.
- **Tests:** echte Browserketten auf 390 px, harte Reloads, reale Requests, Layoutmessungen.
- **Abnahme:** Kernaktionen erreichbar, keine Dock-/Nav-Überdeckung, Trade- und Abschlussketten vollständig grün.

### GATE 6 – CLOSED-BETA RELEASE CANDIDATE

- **Voraussetzungen:** Gates 1–5, CB-017, Migrations-/Recoveryprobe, keine offenen P0 oder ungeklärten P1-Vertragsabweichungen.
- **Tests:** vollständige relevante Suite, Browser-Smokes, Backup/Restore, Mehrnutzer-Simulation und Known-Issue-Review.
- **Abnahme:** Kern ist verständlich, sicher, konsistent und benutzbar; verbleibende Punkte sind ausdrücklich P2/P3 und beeinträchtigen keinen Kernworkflow.

**Phase-8-Nachweis:** Die realistische Wegwerfsimulation mit 31 Nutzern und
verbundenen Account-, Sammlung-, Social-, SmartMatch-, Trade-, Problem-,
Inbox-, Feed-, Privacy- und Karrierejourneys ist grün. Zwei Albumabschlüsse,
zwei regulär erfolgreiche Trades, ein terminaler Problemtrade, ein
konkurrierender Last-Duplicate-Race und vier Integritätscheckpoints bestätigten
die gemeinsamen Wahrheiten. Das S35-Gate bestand 10/10 Pfade; zwei
Vollregressionen bestanden 713/713 ohne Fehler oder Skips. Nachweis:
`04-implementation-reports/Phase-8-realistic-simulation-report.md`.

Damit ist Phase 9 der nächste zulässige Schritt. Phase 9 konsolidiert die sechs
Gates und die vorhandenen CB-017-, Phase-7- und Phase-8-Nachweise zu einer
expliziten Go-/No-Go-Entscheidung; sie ist keine weitere Featurephase.

## 11. Scope-Creep-Schutz

Nicht jedes Auditdetail wird vor Beta perfektioniert. P1 endet beim eingefrorenen Vertrag, nicht bei der vollständigen Vision. Neue Animationen, Kartenvarianten, zusätzliche Statistiken, Trophyideen, Communityfunktionen oder Tradeformen werden klassifiziert und nicht beiläufig in ein laufendes CB-Paket aufgenommen. Ein Paket darf nur erweitert werden, wenn sein bestehendes Abnahmekriterium sonst logisch, sicher oder technisch nicht erreichbar ist.

## 12. Startentscheidung

Der Plan ist ohne weitere Product-Owner-Entscheidung startfähig. **CB-001** ist der erste zulässige Umsetzungsschritt. Vor tatsächlicher Implementierung sind lediglich normale technische Detailentscheidungen innerhalb des eingefrorenen Vertrags zu treffen: konkrete Tabellen-/Schlüsselnamen, Transaktionsmechanik und Migrationsform. Diese sind keine offenen Produktfragen.
