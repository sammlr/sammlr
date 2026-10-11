# LIFECYCLE-08 — Abschluss, Problemauflösung und Bewertungen

Abnahme: 11.10.2026. Autorisierung: aktueller LIFECYCLE-08-Auftrag mit ausdrücklichem Commit/Push-Gate §34, anschließend „fertigmachen bitte“. Ausgangscommit `800a2d3945484c975a9c731b27387fe3d1bbaabb`, Branch `feature/wm-special-trophies`, Upstream `origin/feature/wm-special-trophies`. Ausgangs-HEAD unabhängig mit Remote abgeglichen; tracked Tree und Index zunächst leer. Vorhandene fremde ungetrackte Dateien vor Änderungen erfasst und gehasht. Die frühere L07-Read-only-Anweisung wurde nicht als Autorisierung für L08 verwendet.

## Architektur und Richtungs-/Gesamtabschluss

`LifecycleCompletion` komponiert die bestehenden Receipt-, Shipping-, Foundation-, Event- und Notificationdienste. Kein zweiter Inventorywriter oder Ratingbestand. Die L07-Receiptfakten bleiben unveränderlich; eine eigene unveränderliche Resolution pro Trade/Richtung beschreibt `complete`, `problem_accepted` oder `after_wait`. Jeder neue vollständige saubere Receipt erzeugt diese Auflösung und die eigene Bewertungsberechtigung in derselben IMMEDIATE-Transaktion. Der letzte erforderliche Richtungsabschluss erzeugt genau einen Gesamtabschluss, setzt den Contract auf `ended` und den bestehenden kanonischen Tradezustand auf `completed` bzw. `closed_with_problem`.

Eine offene Problemmeldung oder bloße Senderreaktion reichen niemals. Ohne jede dokumentierte Problemhistorie entsteht `TradeCompletedSuccessfully`, andernfalls `TradeCompletedWithProblem`; auch zwischenzeitliche Nichtankunft mit anschließendem vollständigen Empfang wird nicht als problemfrei dargestellt. Keine zusätzliche bilaterale Bestätigung. Normale Preparation-/Address-/Shipping-/Receiptbefehle erfordern weiterhin den aktiven Contract; nach Abschluss bleiben Ratings im eigenen Fenster sowie sichere identische Wiederholungen möglich.

Historische L07-Receipts werden bei der ersten autorisierten Abschlussansicht bzw. Bewertungsoperation in derselben Transaktion nachgezogen, ohne erneute Bestandsbuchung und mit dem ursprünglichen Receiptzeitpunkt als Eligibility/Directionzeit. Migration0030 führt keinen operativen Datenlauf durch. Für bestehende, niemals erneut aufgerufene L07-Trades gibt es keinen Hintergrund-Backfill in diesem Paket; neue L08-Receipts schließen ohne diesen Nachholpfad atomar ab.

## Problemakzeptanz, Streitfrist und Nichtankunft

Nur der tatsächliche Empfänger der betreffenden Richtung darf einen verbindlichen Problemempfang sofort akzeptieren. Ein ungelöstes Problem darf außerdem ab exakt authoritative `reported_at + 14×24h` endgültig geschlossen werden, unabhängig von Zustimmung oder Reaktion des Senders. Non-Arrival erlaubt ausschließlich diesen Fristabschluss und nur solange kein späterer verbindlicher Receipt vorliegt. Die sieben Tage vor der ursprünglichen L07-Nichtankunftsmeldung bleiben unverändert.

Ein endgültiger Non-Arrival-Abschluss erzeugt keinen Zugang, keinen Sender-Restore und erstmals die eigene Bewertungsberechtigung. Danach werden spätere Receipts auf dieser Richtung service- und datenbankseitig abgewiesen. Ein zukünftiger gesonderter Korrektur-/Nachbuchungsprozess wird nicht vorweggenommen. Die UI verlangt eine signierte zweite Bestätigung mit ausdrücklichem Hinweis auf Endgültigkeit, fehlenden Restore und spätere Briefe. Die ursprüngliche Problemhistorie und Senderreaktion bleiben sichtbar. Keine Schuldentscheidung, Sanktion, Zwangsbewertung oder Zuverlässigkeitsstrafe.

## Restclaims und Inventory

`LifecycleFoundation.release_received_remainder` ist die zentrale Freigabeoperation. Sie verlangt eine finale Problemresolution und selektiert nur die gebundene Revision und Senderrichtung dieses Trades. Nur committed Claims mit `received_quantity < quantity` werden released; vollständig erfüllte Zeilen bleiben unverändert. Erwartungs- und Erfüllungsmengen bleiben auditierbar. Die vorhandene Verfügbarkeitsprojektion berücksichtigt nur den unerfüllten Anteil aktiver Claims: 3 erwartet, 2 akzeptiert, 1 fehlt ergibt vor Abschluss physical=2/committed=1/free_need=0 und danach 2/0/1. Der Need wird auch in der echten TradeV2-/Matchingprojektion wieder sichtbar.

Keine Phantomgutschrift, keine negative Verfügbarkeit, keine zweite Freigabe, kein anderer Tradebinding-Write und keine Änderung des physischen Bestands. L04-/L06-Serviceimplementierungen und ihr Exactly-once-Ledger bleiben unverändert. Die notwendige Shipping-Triggeranpassung ist unten ausdrücklich beschrieben.

## Bewertungen, Fristen und Blind-Reveal

Bestehendes `trade_ratings` und `TradeRatingService` werden erweitert. V1-Zusatzdaten halten ausschließlich Eligibility, positive Tags und Publikationsnachweise. Keine konkurrierende Bewertungswelt. Sterne sind ganze Zahlen 1–5 (Bool wird abgelehnt), Tags optional, eindeutig und serverseitig begrenzt auf Gut verpackt, Schnell verschickt, Freundlicher Tausch, Sticker wie beschrieben, Zuverlässig. Kein Freitext, keine negativen Tags. Genau eine unveränderliche Bewertung pro Nutzer/Trade. Gleiche Wiederholung idempotent, widersprüchliche zweite Bewertung abgelehnt.

Verbindlicher Voll- oder Problemempfang beginnt sofort das eigene 14-Tage-Fenster; die Gegenrichtung ist irrelevant. Eine bloße Nichtankunftsmeldung qualifiziert nicht, ihr endgültiger Abschluss schon. Gültig ist `[eligible_at, eligible_at + 14 Tage)`, maßgeblich UTC-Serverzeit. Exakt am Ende keine neue Bewertung, bestehende identische Retries bleiben gültig. Problemabschluss verlängert ein bereits beim Receipt gestartetes Fenster nicht.

Die fremde Bewertung ist erst sichtbar, wenn beide bewertet haben oder die tatsächlich gestartete Eligibilityfrist der jeweils anderen Person abgelaufen ist. Eine noch nie begonnene Gegenfrist wird nicht erfunden; das Ende der eigenen Frist allein reicht nicht. Die eigene Bewertung bleibt für ihren Autor sichtbar. Profile und empfangene Exportbewertungen verwenden denselben öffentlichen Sichtbarkeitsfilter; Legacy-Ratings bleiben wie bisher öffentlich. Ratingwerte erscheinen weder in allgemeinen Events/Notifications noch in Commandresult-Payloads. HTML enthält vor Reveal keine fremden Sterne/Tags (der allgemeine wählbare Tagkatalog ist selbstverständlich sichtbar).

Zeitabhängiges Reveal wird bei jedem Projektionsread korrekt anhand der Serverzeit berechnet. `RatingRevealed` und Notification werden idempotent beim nächsten autorisierten Completion-Aufruf bzw. Ratingcommand materialisiert, mit dem tatsächlichen effektiven Revealzeitpunkt. Kein Scheduler wird eingeführt; zwischen Fristablauf und diesem Aufruf kann die Sichtbarkeit bereits gültig sein, während Event/Notification noch nicht materialisiert sind. Beidseitige Ratingabgabe publiziert beide atomar im letzten Ratingcommand. Das ist keine vorzeitige Offenlegung.

## Ownership, Security, Historie und Transaktionen

Aktiver Account, Trade-Teilnahme, tatsächliche Empfangsrichtung und exakte gebundene Revision werden im Service validiert. Signierte Tokens binden Actor/Trade/Revision/Operation/Problem; CSRF bleibt aktiv. Ratingziel, Eligibility und Deadline kommen nie vom Client. Unbekannte Ratingfelder, nicht eindeutige Skalarwerte und ungültige Sterne/Tags werden abgewiesen. Fremder GET erhält 404; fremde signierte Commands scheitern. Private Ansichten verwenden `private, no-store` und `no-referrer`. Schemagates verhindern implizite Migration beim Zugriff.

Immutable Ereignisse: `DirectionResolvedComplete`, `DirectionResolvedProblemAccepted`, `DirectionResolvedAfterWait`, `TradeCompletedSuccessfully`, `TradeCompletedWithProblem`, `RatingSubmitted`, `RatingRevealed`. Keine Adressen oder privaten Fotos in den Payloads. Trigger sichern neue Abschluss-/Eligibility-/Tag-/Publikationsfakten und ihre Historie gegen Update, Delete und Replace. Bestehende immutable Ratingtrigger bleiben aktiv.

BEGIN IMMEDIATE serialisiert relevante Rennen. Resolution, eigene Restclaimfreigabe, eventuell letzter Gesamtabschluss, History, Notifications und Commandresult committen gemeinsam. Der Receipt-Hook läuft innerhalb der bestehenden Receipt-/Inventorytransaktion. Fehler an Claim, Completion, Event, Notification oder Commandresult rollen alles zurück; ein Fehler nach letztem Receipt auch dessen Bestandsbewegungen. Rating-/Tag-/Reveal-Fehler rollen die gesamte neue Bewertung zurück.

## Migration und Legacy-Abgrenzung

Neue Migration **0030**, keine Änderung an **0022–0029**, keine bestehenden Daten-/Ratingtabellen ersetzt. Fünf additive Metadatentabellen und Schutztrigger. Eine notwendige kompatible Anpassung: der bestehende `lifecycle_shipping_no_cancel`-Trigger wird innerhalb0030 neu definiert. Sein einzig neuer erlaubter Übergang ist accepted→ended bei unveränderter accepted_revision **und bereits vorhandener unveränderlicher Completionevidenz**. Normales Cancel, Revisionwechsel und Wiederöffnung bleiben gesperrt. Dies ist kein neuer L06-Abbuchungspfad.

Down ist ausschließlich bei vollständig leeren neuen Tabellen zulässig und stellt den originalen Shipping-Trigger wieder her. Bereits persistierte Receiptresolution, Eligibility, Completion oder Ratingdetails verhindern Rückbau. Forward, erlaubter Reverse, erneutes Forward, verbotener Reverse sowie FK-/Integritycheck wurden synthetisch geprüft. Keine reale Datenbank geöffnet, kopiert oder migriert.

Legacy-Commands/Qualification und ihre shared Ratings bleiben unverändert. V1 wird über `lifecycle_contracts` abgegrenzt; fehlende legacy_request_id verhindert Legacy-Commandkollision. Ein öffentliches Rating wird nur einmal gezählt. Getestete bestehende Profil-, Rating-, History-, Notification-, Datenschutz- und Legacy-Verträge bleiben grün. Die übrigen bestehenden Testdateien enthalten ausschließlich die notwendige Latest-Migrationserwartung 29→30 (bzw. Range/Kommentar), keine neuen Ausschlüsse oder abgeschwächten Fachassertions.

## UI und Abnahme

Abschlussansicht `/tauschen/abschluss/<trade>` zeigt beide Richtungen, akzeptierte Mengen und Abweichungen, Problemzeit/14-Tage-Grenze, Senderreaktion, endgültigen Status sowie unabhängige Bewertungskarte. Aktive Requests und Receipts verlinken dorthin; abgeschlossene Receipts leiten nach Ownershipprüfung auf diese dauerhafte Ansicht. Reduzierte bindende Revisionen bleiben nach Contractende in der Requestübersicht auffindbar. Notifications führen zur berechtigten Abschluss-/Problemansicht. Keine neue Messenger- oder Zentraleoberfläche.

Sämtliche Tests liefen in `/private/tmp/lifecycle08/candidate`, Testdatenbanken ausschließlich aus SQL/synthetischen Fixtures unter `/private/tmp`, mit SQLite-Audit-Hook gegen andere DB-Pfade. Kein geschütztes DB-File als Fixture kopiert.

- **1.667 Release-Tests erfolgreich**, 1.679 entdeckt, **dieselben 12 Ausschlüsse**, 0 Failures/Errors/Skips. Lifecycle01–08, Inventory/Need-Claims/Missing-Holds, TradeV2/SAP/SmartDeal, Legacy, Ratings/Profiles, Notifications, Privacy/Security und bestehende Solverprüfungen enthalten.
- Zusätzlich **8 Preview-Tests erfolgreich**.
- **37 gezielte L08-Tests erfolgreich** (31 Domain/Integration, 6 HTTP), zugleich Bestandteil des Release-Laufs. Beide vollständigen Richtungen; eine vollständige/eine problemaufgelöste; beide Probleme; einzelne Richtung bleibt aktiv; offenes Problem bleibt offen; 3→2/1 und fremde Claims; vollständig akzeptierter Schaden gibt keinen erfüllten Claim frei.
- Fristen vor/exakt/nach14 Tagen; Rating vor Eligibility, ab Eligibility, kurz vor/exakt/nach Ablauf; Problemempfang qualifiziert ohne Resolution; Non-Arrival erst final. Reveal wartet auf echte Gegenfrist, nie auf die eigene. Hidden-Werte in HTML, Profilsummary, Export und Events geprüft.
- Concurrency: doppelte/parallele Problemauflösung, beide Probleme gleichzeitig, Problemabschluss gegen letzten Receipt, Non-Arrival-Abschluss gegen späten Receipt, Senderreaktion gegen Abschluss, gleiche/parallele/beidseitige Ratings, neue Ratings an der exakten Deadline. Keine doppelten fachlichen Events, Claims oder Bewertungen.
- Rollback-Injektionen für Claim-/Completion-/History-/Notification-/Command-/Tag-/Publikationswrites; Migrationupgrade mit historischen L07-Receipts; unveränderliche Evidenz; unverändert strikte Shipping-/Reopen-Sperren; CSRF/Actor/Trade/Token/zusätzliche Felder sowie unmigrierter503-Zugriff ohne Write.
- Browser: **10 Ansichten/Flussstationen × 375/390/430/1280 px**. Einseitige Eligibility, verdeckte Bewertung, automatischer Vollabschluss, beidseitiger Reveal, Teilempfang/Problem, Bestätigung, Problemabschluss mit 3→2/1-Claimkontrolle, strittiger Abschluss nach15 Tagen, Nichtankunftswarnung, endgültiger Nichtankunftsabschluss samt Eligibility und abgelehntem spätem Receipt. Fremdzugriff404. **Kein horizontaler Overflow, keine JavaScript-Fehler.** Mobile Bestätigung375px und beidseitiger Reveal390px zusätzlich visuell geprüft.

Entwicklungsbefunde wurden behoben: Der unveränderte Shipping-Trigger verhinderte anfangs auch legitimen endgültigen Abschluss; die neue eng evidenzgebundene Ausnahme behebt dies. Zwei neue Testannahmen (offene SQLite-Transaktion nach absichtlich verworfenem UPDATE; Zählen aller released Historienclaims statt der betroffenen Restclaims) wurden korrekt auf die Fixtures/Claimrelationen angepasst. Der Browserfixture fehlte zunächst das Foreign-Key-Pragma; korrigiert. Diese fehlgeschlagenen Zwischenläufe werden nicht als Abnahme gewertet. Aktuelle vollständige Wiederholungen sind grün.

Nachweise: `/private/tmp/lifecycle08/release-results.json`, `release.log`, `focused.log`, `preview.log`, `browser/results.json`, `browser/*.png`, `db-start.json`, `foreign-start.json`, `git-start.txt`, `final-verification.json`. Browserreproduktion: `tests/research/check_lifecycle08.py` ausschließlich im isolierten synthetischen Kandidaten.

## Integrität, Git und offene Grenzen

Alle **16** geschützten DBs nach Tests bytegleich zur Startbaseline und zum vorherigen autorisierten L07-Abschluss. Alle **9.736** vorhandenen fremden ungetrackten Einträge unverändert (Datei-SHA-256 bzw. Symlinkziel), insbesondere Social Studio. Keine fremden Dateien gelöscht, überschrieben, zurückgesetzt oder gestagt. Keine Änderung an bestehenden Migrationen0022–0029 oder am12-Ausschlussvertrag. `git diff --check` und Abgleich des getesteten Quellkandidaten sind Abschlussgates.

Beauftragter Commit: `feat: add lifecycle v1 completion and ratings`, ausschließlich die unten aufgeführten **43 Dateien**. Normaler Push auf bestehenden Upstream; unabhängiger Local-/Remote-HEAD-Abgleich und sauberer tracked Tree/leerer Index anschließend im Abschlussbericht. Keine selbstreferenzielle Commit-ID in diesem Audit.

Keine festgestellten offenen Abnahmeblocker. Bewusste Grenzen: kein Hintergrund-Backfill alter L07-Abschlüsse, zeitbasierte Reveal-Events/Notifications werden beim nächsten fachlichen Aufruf materialisiert, nie gestartete Gegenfrist lässt ein Rating weiter blind. Kein nachträglicher Receipt nach finaler Nichtankunft, kein Ersatz-/Retouren-/Korrekturprozess und keine administrative Streitentscheidung. Diese Grenzen sind oben explizit beschrieben. **Kein Deploy, keine reale Migration; Lifecycle-09 nicht begonnen.**

## Exakte Dateiliste
- `App/Database/migrations/0030_trade_lifecycle_completion.down.sql`
- `App/Database/migrations/0030_trade_lifecycle_completion.up.sql`
- `App/lifecycle_acceptance_routes.py`
- `App/lifecycle_completion_routes.py`
- `App/lifecycle_receipt_routes.py`
- `App/services/trade_lifecycle_completion.py`
- `App/services/trade_lifecycle_foundation.py`
- `App/services/trade_lifecycle_receipts.py`
- `App/services/trade_lifecycle_requests.py`
- `App/services/trade_ratings.py`
- `App/services/typed_notifications.py`
- `App/services/user_data_export.py`
- `App/templates/lifecycle_completion.html`
- `App/templates/lifecycle_receipts.html`
- `App/templates/lifecycle_requests.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `docs/LIFECYCLE_08_AUDIT.md`
- `docs/TRADE_LIFECYCLE_V1_CONTRACT.md`
- `docs/TRADE_LIFECYCLE_V1_IMPLEMENTATION_PLAN.md`
- `docs/TRADE_LIFECYCLE_V1_INVARIANTS.md`
- `docs/TRADE_LIFECYCLE_V1_STATE_MACHINE.md`
- `tests/research/check_lifecycle08.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle01_foundation.py`
- `tests/test_lifecycle08_completion.py`
- `tests/test_lifecycle08_ui.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`

## Geschützte Datenbanken — SHA-256 vorher = nachher

- `App/Database/sammlr_reference_s00.db`: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`
- `App/Database/s20_coverage_debug.db`: `dadac1c379a45ec0245208293aef3eccd732cc41b3c07e4b8c523cace1444d9e`
- `App/Database/sammlr.db`: `c317d3ee7418f9caeaf655e9ed13c04ccdd88f1b8599652b42d56b1163905771`
- `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db`: `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e`
- `App/Database/Database:Backups/collectr_backup_popup_clean.db`: `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3`
- `App/Database/Database:Backups/collectr_backup_before_users.db`: `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039`
- `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db`: `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3`
- `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db`: `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f`
- `Backups/sammlr_local_pre_v0005_20260803_211622.db`: `cb69ff4407f6c9c166e84d472f8a89b32e33692cde109b437b1d60ebb0aa0a01`
- `Backups/sammlr_local_pre_v0003_20260802_091642.db`: `ff96c936c3a4fe86433f3cd42dfbc51e24a034a02c147ccc5e40aefdb436c5d8`
- `Backups/sammlr_before_valy_password_reset_20261004T084422847704Z.db`: `0748a936250c2771173a5bfb3853b7718c79e376fed25409438d0927062c5eb1`
- `Backups/collectr_2026-06-02_22-14-58.db`: `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c`
- `Backups/sammlr_local_pre_v0006_20260808_010509.db`: `159cc562b648ebf567878622b4db815cc2acf86601b9d2bc2a586793b8cd5912`
- `Backups/sammlr_local_pre_v0004_20260802_232331.db`: `2063fddc7991cd699dc5321f8210b1278ee8180a96dbaf0ab0a89a87aafcd466`
- `Backups/sammlr_local_pre_v0007_20260808_023853.db`: `752292434f44c637f7518c71494d5b7f787d786d881bca06024b8547c732eac8`
- `App/Database/collectr.db Kopie`: `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a`
