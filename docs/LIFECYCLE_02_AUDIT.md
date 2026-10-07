# LIFECYCLE-02 — V1-Anfrage, Reservation, Need-Claim und Freigabe

Stand: 2026-10-07. Ausschließlich pre-acceptance `trade_lifecycle_v1`.
Ausgangspunkt: `d1cf841221a4a8eafb4fb87088ee1f3f06c95083` (`feat: add trade lifecycle v1 foundation`).
Branch/Upstream: `feature/wm-special-trophies` / `origin/feature/wm-special-trophies`.
Remote: `https://github.com/sammlr/sammlr.git`.
Vor Beginn: erwarteter HEAD, leerer Index, sauberer getrackter Arbeitsbaum und alle 16 autorisierten DB-Hashes bestätigt. Bestehende lokale Privatdateien sind kein Commitbestandteil.

## Bestehende Wege und Wiederverwendung

| Weg / Baustein | Befund und Umsetzung |
|---|---|
| SAP `/tauschen`, `/tauschen/sammlr` | `trade_search_routes.py` → `trade_search.search` → `TradeV2Domain.market`. Suche/Ranking bleiben bestehen. Ein Link führt auf die vorhandene Fläche `/tauschen/laufend`. |
| Profil → automatisch | `profile_trade_html`, `partner_trade.partner_deal` und `trade_shell.partner_deal`: serverseitig konkreter Deal aus dem existierenden Solver. Send-Formular nur bei vorhandener Requestmigration. |
| SmartDeal-Vorschlag | `/tauschen/vorschlag/<partner>` nutzt denselben Send-Service; exakte angezeigte Positionen bleiben unverändert. Keine Neuberechnung anstelle des bestätigten Pakets. |
| Manuelle Auswahl | Bestehende kanonische Liste und `/manual/check`; Fingerprint und frische Domainvalidierung bleiben. Erfolgreiche Prüfung führt auf eine genaue Bestätigungsansicht und danach denselben Create-Service. Mengenexemplare werden über serverseitig bekannte Listenschlüssel zu Positionen aggregiert. |
| Persistenz bisher | SAP/Profile/Manual haben vorher keine Anfrage geschrieben. Alte Webapp-Einstiege persistieren `trade_requests`, getrennt über `smart_trade_requests`, `smartdeal_requests` und Legacy-Routen. |
| Legacy-S22 | Marker -22, bisherige 48h und eigenes Limit unverändert. |
| Expliziter `smartdeal_v1` | 24h, beidseitige Pending-Holds, alte Create/Accept/Release-Services und ihr Dispatch unverändert. Keine neuen Lifecycle-IDs in `trade_requests`. |
| Legacy-Accept / Inventory | `TradeReservationService` und `InventoryReadService` verwenden dieselben aktiven mengenbasierten `trade_reservations`; neue Senderholds schützen deshalb auch gegenüber Legacy-Zugriffen. Keine physischen Inventorywrites in L02. |
| Planungsreader | `SmartDealPlanningService` / `LegacyPlanningReadAdapter` bleiben unverändert. Additiver Lifecycle-Adapter im Trade-v2-Markt berücksichtigt explizite Ziele und Claims. Keine globale Umdeutung alter Needs. |
| Notifications / History | `trade_events` persistiert `OfferSent`, `OfferWithdrawn`, `OfferRejected`, `OfferExpired` mit Trade, Revision, Akteur und Serverzeit. Die neun bestehenden typisierten Notification-Verträge/alten Targets werden nicht zweckentfremdet. Neue Inbox-/Push-Zustellung wird nicht behauptet; die fachlichen Ereignisse sind dauerhaft vorbereitet. |
| Preview | `App/trade_v2` bleibt sessionStorage-Preview. Einzige JS-Erweiterung reagiert im bestehenden `data.live`-Zweig auf die produktive Review-URL. Keine Preview-Domain übernommen; acht Preview-Tests grün. |

## Autoritative Schreibgrenze und Persistenz

`LifecycleRequests.create` ist die zentrale neue Create-Grenze. Die Route gewinnt den Actor aus der authentifizierten Session; bestehende globale Auth-/Auth-Version-/CSRF-Prüfungen gelten weiter. Der Service prüft aktive Accounts erneut, verbietet Self-Trade und nutzt den frischen zentralen Trade-v2-Markt für Teilnehmerberechtigung, Pool, bilaterale Cross-Freigaben, Bestand, relevante Needs und Balance.

Ein `BEGIN IMMEDIATE` umfasst Expiry-Sweep, Command-Replay, Dreierlimit, frische Validierung, Tradeidentität, versiegelte Originalrevision, Sender-Give-Holds, eigene Receive-Claims, unveränderliche Frist und Ereignis. Jeder Fehler rollt die ganze Transaktion zurück. Kein fremder Supply-Hold/Need-Claim, kein physischer Bestandsabgang, kein Annahme-Snapshot, keine Packphase.

Manuell bleibt `Receive <= Give` je zulässiger Balancegruppe; SmartDeal ist gleich groß und mindestens fünf je Richtung. Ein clientseitig veränderter Deal wird nicht vertraut. Serverseitig signierte, actor-gebundene Vorschautokens enthalten genaue Positionen und einen Create-Key; sie laufen nach einer Stunde ab. Dies ist nur Vorschaufrische, keine Verkürzung der gespeicherten 72h-Anfrage. Der Service validiert trotz Signatur erneut. Derselbe Command-Key und Payload liefert dieselbe Trade-ID, auch nach Terminalisierung; geänderter Payload ist Konflikt.

Neue additive Migration **0024_trade_lifecycle_requests**: `lifecycle_requests` mit Trade-/Revision-/Senderbezug, senderweit eindeutiger Create-Commandidentität, Payload-Digest, `created_at`, `expires_at`, offen/withdrawn/rejected/expired und Endzeit. Constraints/Trigger schützen Zuordnung, ursprüngliche Revision, Zeitidentität und terminale Zustände. Populierter Down-Pfad verweigert destruktives Rollback; leerer Roundtrip getestet. Migrationen **0022 und 0023 bytegleich** zum Ausgangscommit. Keine geschützte Datenbank migriert.

Die reale lokale DB bleibt auf ihrem bisherigen Stand. Ohne 0024 gibt es keinen Send-Button und Schreib-/Request-Detailpfade liefern 503; kein Auto-Migrate, kein Legacy-Fallback, kein Anlegen einer fehlenden DB. Produktive Routen wurden auf einer frisch synthetisch migrierten DB getestet. Die spätere reale Migrationsfreigabe bleibt erforderlich.

## Mengen, Planung und Solver

- Give verwendet die gemeinsame Reservationsquelle, jeweils nur Senderpositionen und nur die konkrete Menge. Bestand und Eigenexemplar bleiben unverändert.
- Need verwendet die L01-Zielmenge: `max(target − physical − legacy/new committed − own pending, 0)`. Ziel 2 → Claim 1 → freier Need 1; weitere 1 → 0; Withdraw/Reject geben jeweils exakt ihre Menge frei.
- Empfänger-Give bleibt frei; ein späterer Bestandsverbrauch verändert die unveränderliche Anfrage nicht. Annahmerevalidierung ist L03.
- SAP/Trade-v2 wenden die Mengenprojektion zusätzlich zum bestehenden Reader an. Bei Deadlineüberschreitung ist die Projektion bereits read-only wirksam; sie schreibt weder Bestände noch Legacy-Zustände. Nur eigene neue abgelaufene Holds werden für diesen Read ausgeblendet, die Legacy-Holdprojektion bleibt erhalten.
- Der bestehende Integer-Flow-Solver verarbeitet in einem expliziten `quantities=True`-Modus Mengen pro Kandidatenkante und globalem Need. Keine zweite Matchingengine, keine Heuristik und keine neue Rankingregel. Legacy-Aufrufer behalten die binären Eingabeprüfungen. Ausgabe aggregiert gleiche Albumcodes mit Menge; globale Supply-/Need-Postconditions prüfen die Summe aller Vorschläge.
- Bestehende 900 binäre Scoped-Flow-Orakelvergleiche bleiben grün. Zusätzlich prüfen 40 unabhängig exhaustiv enumerierte Mengenfälle die erweiterten Kapazitäten sowie einen gemeinsamen Need/Supply über zwei Vorschläge.

## Zeit, Quote, Releases und Nebenläufigkeit

Zeit wird serverseitig nach Erwerb der Schreibsperre als UTC-Instant erfasst. `expires_at = created_at + timedelta(hours=72)`; kein Tagesende, keine lokale Kalendertagslogik und keine Fristverlängerung durch Replay. `now == expires_at` ist expired.

Nur eigene offene neue Requests zählen; maximal drei unter derselben serialisierten Schreibgrenze. Eingehende Requests, Legacy und terminale Requests zählen nicht. Vier eingehende Requests und konkurrierende dritte/vierte eigene Anfrage sind geprüft.

`LifecycleRequests.expire` ist derselbe idempotente atomare Sweep für lazy Read/Write und einen späteren Scheduler. Create und Teilnehmeransichten führen ihn aus; reine Marktreads projizieren abgelaufene Bindungen bereits als unwirksam. Keine Reminder-Simulation und kein Hintergrundscheduler.

Withdraw ist sender-, Reject empfängergebunden. Vor Fristende gewinnt genau die erste serialisierte Transition. Ab Deadline wird auch beim Withdraw-/Reject-Versuch ausschließlich expired gespeichert. Status, Freigabe beider Bindungen und Ereignis committen gemeinsam. Wiederholung liefert den bereits terminalen Zustand, keine zweite Freigabe und kein zweites Terminalereignis. Falsche Rolle und fremde Leser werden abgewiesen. Da L02 genau eine unveränderliche Originalrevision hat, ist der terminale Command durch Trade/Rolle/Aktion eindeutig; spätere Revisionswechsel sind nicht implementiert.

## UI und Abnahme

- SmartDeal: vorhandene Dealansicht → Tausch anfragen → `/tauschen/anfragen/<trade_id>`.
- Manuell: vorhandene Auswahl → `/manual/check` → `/tauschen/anfragen/entwurf` → bewusster Send-POST.
- `/tauschen/laufend`: bestehende Legacy-Liste plus getrennte neue Requests mit Sender/Empfänger, genauen gerichteten Mengen, Status und 72h-Ablauf.
- Sender kann zurückziehen; Empfänger kann ablehnen. Kein V1-Annehmen-Button und kein Accept-Endpoint.
- Browserabnahme auf echtem Flask-HTTP-Server mit zwei getrennten authentifizierten Chromium-Kontexten: SmartDeal/Reject, Manual/Withdraw, Lazy Expiry, danach wieder verfügbarer Deal, keine JS-Fehler und kein horizontaler Overflow bei 375/390/430/1280.
- Sieben Screenshots und Ergebnisdatei: `/private/tmp/lifecycle02/browser/`. Nur synthetische Nutzer, keine echten Profile/Sammlungen/Adressen.

## Tests und Integrität

Release-Gate in vollständiger source-only Arbeitskopie unter `/private/tmp/lifecycle02/`, frische SQL-generierte synthetische DBs. SQLite-Audit-Hook verweigert DB-Zugriff außerhalb `/private/tmp`; reale DBs wurden weder kopiert noch als Fixture verwendet. Der Browserharness erzwingt denselben Pfadschutz. Kein neuer DB-Pfad im Repository.

Finale Ergebnisse:

- **1.422 Release-Tests**, 0 Fehler, 0 Failures, 0 Skips; 12 unveränderte historische/Baseline-Ausschlüsse.
- Darin **38 neue L02-Tests** (31 Request/State/Concurrency, fünf produktive HTTP/UI, zwei Mengen-Solver), sowie die 31 L01-Fundamenttests und bestehende Legacy/SmartDeal/Trade-v2-Regressionen.
- **8 separate Pax-/Trade-v2-Preview-Tests** bestanden.
- **900 bestehende + 40 neue unabhängige Scoped-Flow-Vergleiche** innerhalb der Tests bestanden.
- Produktiver Browsertest `tests/research/check_lifecycle02.py` bestanden.
- `git diff --check` und `git diff --cached --check` ohne Befund vor Commit.
- Alle **16 geschützten DBs** gegenüber autorisierter Startbaseline bytegleich; kein Profil-/Privatdatenbestand im Dateiumfang.

Während der Entwicklung wurden Migrationserwartungen 23→24 und der Teststub für die erweiterte Solver-Signatur angepasst. Zwei neue Testannahmen wurden korrigiert (bestehender CSRF-Status 403, kanonischer EM24-Code `TOPPS 1`). Keine neue Testausnahme; abschließend sämtliche Gates grün. Source-/Diffprüfung zeigt keine Annahme, Migration echter DBs, physischen Inventorywrites oder Änderungen an Legacy-Fristen.

Lokale Nachweise: `/private/tmp/lifecycle02/release-results.json`, `release.log`, `preview.log`, `browser/results.json`, `db-start.json`, `db-final.json`, `final-files.json`. Temporäre Artefakte/DBs sind nicht gestaged.

## Grenzen und Abschluss

Keine Annahme, kein Gegenangebot, keine bilaterale Reservation, kein Acceptance-Regel-Snapshot, keine Fotos, Adressen, Versand-, Empfangs- oder Ratingaktionen. Keine Zentrale, kein Push-/Reminder-System. Bedarfseinstellungen bleiben der bestehende interne Mengenadapter ohne neue Settings-UI. Altverträge besitzen weiterhin ihre dokumentierten Need-Eigenschaften; keine rückwirkende globale Need-Exklusivität behauptet.

Die App ist auf alten Schemata weiter lesend nutzbar; neue Anfragen benötigen die separat freizugebende reale Migration. Kein Deploy. LIFECYCLE-03 nicht begonnen.

Commitumfang ausschließlich nachstehende L02-Dateien. Commitmessage: `feat: add lifecycle v1 trade requests`. End-Commit ist der Commit, der dieses Audit hinzufügt; Hash und nach dem Push unabhängig gelesener Remote-HEAD werden im Abschlussbericht ausgegeben (kein selbstreferenzieller Hash im Commit).

## Exakter Dateiumfang

- `App/Database/migrations/0024_trade_lifecycle_requests.down.sql`
- `App/Database/migrations/0024_trade_lifecycle_requests.up.sql`
- `App/lifecycle_request_routes.py`
- `App/profile_trade.py`
- `App/services/_smartdeal_flow.py`
- `App/services/_trade_v2_flow.py`
- `App/services/lifecycle_planning.py`
- `App/services/partner_trade.py`
- `App/services/smartdeal_optimizer.py`
- `App/services/trade_contracts.py`
- `App/services/trade_lifecycle_foundation.py`
- `App/services/trade_lifecycle_requests.py`
- `App/services/trade_v2_domain.py`
- `App/templates/lifecycle_request_review.html`
- `App/templates/lifecycle_requests.html`
- `App/templates/trade_search.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `App/trade_v2/assets/manual_view.js`
- `docs/LIFECYCLE_02_AUDIT.md`
- `tests/research/check_lifecycle02.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle01_foundation.py`
- `tests/test_lifecycle02_quantities.py`
- `tests/test_lifecycle02_requests.py`
- `tests/test_lifecycle02_ui.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`
- `tests/test_sd_t3b_optimizer.py`

## Geschützte DBs — SHA256 vor/nach identisch

| Datei | SHA256 (vor = nach) |
|---|---|
| `App/Database/sammlr_reference_s00.db` | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` |
| `App/Database/s20_coverage_debug.db` | `dadac1c379a45ec0245208293aef3eccd732cc41b3c07e4b8c523cace1444d9e` |
| `App/Database/sammlr.db` | `c317d3ee7418f9caeaf655e9ed13c04ccdd88f1b8599652b42d56b1163905771` |
| `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db` | `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e` |
| `App/Database/Database:Backups/collectr_backup_popup_clean.db` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_before_users.db` | `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039` |
| `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db` | `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f` |
| `Backups/sammlr_local_pre_v0005_20260803_211622.db` | `cb69ff4407f6c9c166e84d472f8a89b32e33692cde109b437b1d60ebb0aa0a01` |
| `Backups/sammlr_local_pre_v0003_20260802_091642.db` | `ff96c936c3a4fe86433f3cd42dfbc51e24a034a02c147ccc5e40aefdb436c5d8` |
| `Backups/sammlr_before_valy_password_reset_20261004T084422847704Z.db` | `0748a936250c2771173a5bfb3853b7718c79e376fed25409438d0927062c5eb1` |
| `Backups/collectr_2026-06-02_22-14-58.db` | `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c` |
| `Backups/sammlr_local_pre_v0006_20260808_010509.db` | `159cc562b648ebf567878622b4db815cc2acf86601b9d2bc2a586793b8cd5912` |
| `Backups/sammlr_local_pre_v0004_20260802_232331.db` | `2063fddc7991cd699dc5321f8210b1278ee8180a96dbaf0ab0a89a87aafcd466` |
| `Backups/sammlr_local_pre_v0007_20260808_023853.db` | `752292434f44c637f7518c71494d5b7f787d786d881bca06024b8547c732eac8` |
| `App/Database/collectr.db Kopie` | `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a` |
