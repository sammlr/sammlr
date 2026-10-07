# LIFECYCLE-03 — Acceptance, Revalidation und einmaliges Gegenangebot

Stand: 2026-10-07. Ausgangscommit `16fecc5fa987a8a9808b77a40407b85aef82a39e` (`feat: add lifecycle v1 trade requests`). Branch `feature/wm-special-trophies`, Upstream `origin/feature/wm-special-trophies`, Remote `https://github.com/sammlr/sammlr.git`.

Vor Änderungen: erwarteter HEAD, Branch und Upstream bestätigt; Index leer, getrackter Arbeitsbaum sauber; alle 16 geschützten DBs entsprechen der autorisierten Baseline. Lokale Privat-/Runtime-Dateien sind kein Bestandteil dieses Pakets.

## Fundament und verbindliche Regeln

Geprüft: L01-Revisionen, minimale versionierte `RuleSnapshot`-Struktur, Consents, Claims, Richtungszustände und Commandidentitäten; L02-Request-Service/Expiry/UI; gemeinsame `trade_reservations`, InventoryRead/Write/Guard, Legacy Acceptance, ältere SmartTradeRequestService-48h-Verträge, explizites SmartDeal-V1 mit 24h, TradeV2Domain, Solver und `trade_events`.

Das vorhandene Fundament passt zum geschlossenen Vertrag. Sender-Give und eigene Pending-Claims existieren bereits. `accepted_revision_id` verlangt einen versiegelten Snapshot und zwei Consents; committed Claims sind auch für die zweite Seite zulässig. Die gemeinsame Hold-Materialisierung wurde aus der vorhandenen Pending-Methode in eine wiederverwendbare Foundation-Methode extrahiert, ohne neue Supplyquelle.

Gegenangebotssemantik ist ausdrücklich entschieden: [Fachvertrag §5](TRADE_LIFECYCLE_V1_CONTRACT.md#5-revalidierung-und-höchstens-ein-gegenangebot) verlangt atomar Original → superseded, alte Holds/Claims frei, neue Senderholds/eigene Claims und **eigene neue 72 Stunden**. Rechnen allein sendet nichts. Genau eine Counterrevision ist durch den bestehenden Unique-Index abgesichert. Bei ungültiger Counterannahme endet die Verhandlung. Die initiale SmartDeal-Mindestgröße fünf bleibt bestehen; kleinere Gegenangebote behalten ihre Herkunft und werden nicht still manuell umklassifiziert (Fachvertrag §1).

## Migration 0025

`0025_trade_lifecycle_acceptance` erweitert ausschließlich die neue Lifecycle-Persistenz. Die Migrationen **0022, 0023 und 0024 sind unverändert**.

Die in 0024 auf genau eine Zeile pro Trade beschränkte Request-Hülle wird verlustfrei zu einer Zeile pro unveränderlicher Angebotsrevision erweitert. Dazu baut 0025 `lifecycle_requests` innerhalb der Migrationstransaktion neu auf und kopiert sämtliche bisherigen Felder/Zeilen unverändert. Keine Legacy-Tabelle wird umgebaut, keine Altsemantik migriert. Historische Originalhülle bleibt nach Counter erhalten; ein partieller Unique-Index erlaubt höchstens ein offenes Angebot je Trade. Zustände ergänzen accepted, superseded und invalidated. Neue immutable `lifecycle_acceptances` speichert Trade, angenommene Revision, annehmenden Nutzer und UTC-Zeit.

Synthetischer Upgrade mit existierender L02-Anfrage, leerer Down/Up-Roundtrip und verweigerter populierter Downgrade geprüft. Keine geschützte DB migriert oder kopiert. Produktive Acceptance-/Counter-Controls und Commands benötigen 0025; eine reale Migrationsfreigabe bleibt ausstehend. Auf Schema 0024 bleiben L02-Anfragen möglich, ohne Acceptance-Controls; der geschützte lokale Stand bleibt unverändert.

## Eine Acceptance-Schreibgrenze

`LifecycleAcceptance.accept` verwendet dieselbe `LifecycleFoundation.transaction()` mit `BEGIN IMMEDIATE` wie die vorhandenen Requests. Original und Gegenangebot durchlaufen **denselben** Code.

1. Expliziten Contract-Type, aktive authentifizierte Identität, aktuellen Empfänger und erwartete aktuelle Revision prüfen.
2. Idempotenz über vorhandene `lifecycle_commands`: Actor/Trade/Key/Operation und Payload-Digest. Gleicher Command liefert gespeichertes Ergebnis; geänderter Payload ist Konflikt.
3. Serverseitige UTC-Zeit nach Lock-Erwerb; `now >= expires_at` gewinnt als expired. Bereits terminale Zustände werden nicht angenommen; erfolgreicher Retry reserviert nichts erneut.
4. Senderholds und Pending-Claims müssen exakt den versiegelten Positionen entsprechen. Keine stillschweigende Reparatur einer fehlenden Bindung.
5. Frischen `TradeV2Domain.market` mit ausschließlich diesem Angebot zugeordneten Hold-/Claim-Credits lesen. Beide Supplies/Needs, andere Bindungen, Pools, Eligibility, aktuelle bilaterale Cross-Regeln und Balance validieren. Keine clientseitige Paketautorität und keine Selbstblockade durch eigene Bindungen.
6. Erst nach vollständiger Prüfung Empfänger-Give im gemeinsamen Holdsystem materialisieren. Vorhandene Sender-Give bleibt dieselbe Reservation, keine Doppelzeile. Sender-Pending-Claims werden committed; zweite Receive-Seite erhält committed Mengenclaims.
7. Aus genau den validierten aktuellen Album-/Cross-Regeln den bestehenden minimalen `RuleSnapshot` erstellen: Schema V1, Angebotserstellerperspektive, Gegenpartei, Herkunft, Gleichheitsregel, relevante Alben und bilaterale Pool-/Cross-Freigaben. Keine vollständigen Userobjekte.
8. Zwei Consents auf dieselbe Revision persistieren: ausdrückliches Senden des aktuellen Angebots und ausdrückliche Empfängerannahme. `accepted_revision_id`, immutable Acceptancebeleg, Request/Contract/Trade accepted, Ereignis und beide Richtungen committen atomar.

Fehler nach begonnener Materialisierung rollen neue Holds, Claims, Snapshot, Consents und Acceptance vollständig zurück. Ein ungültiges Original bleibt offen und unverändert; Ergebnis `not_possible` wird fachlich angezeigt. Kein 20→17-Silent-Shrink. Ein ungültiger Counter wird dagegen atomar invalidated, seine Bindungen werden freigegeben; kein drittes Angebot.

## Bindender Zustand und Einstellungen

Beide Richtungen existieren aus L01. Acceptance setzt `preparation_state='ready'` als eindeutigen Einstieg für spätere Packarbeit; Shipping/Receipt bleiben unberührt. Acceptancezeit liegt dauerhaft vor. Kein Pack-Countdown, keine Packlisten-/Foto-/Adress-/Versandsteuerung und keine 72h-Packworkflow-Implementierung.

Angenommene Revision und Stickerpositionen bleiben immutable. Normales Withdraw/Reject wird nach Acceptance serverseitig verweigert, Expiry überspringt accepted. Globale Pool-/Cross-Änderungen verändern den persistierten Deal/Snapshot nicht; neue/offene Angebote prüfen weiterhin aktuelle Einstellungen. Spätere Reduktionen/Abwicklung sind nicht implementiert.

SAP-/Trade-v2-Projektion berücksichtigt beide committed Need-Seiten. Legacy-Reader, Legacy-Need-Eigenschaften, Fristen und Acceptance bleiben unverändert. Neue und alte Vorgänge respektieren weiterhin dieselbe mengenbasierte physische Reservationsquelle.

## Counter: Berechnung, Bestätigung und atomarer Wechsel

`preview_counter` berechnet nach Rollen-/Revisions-/Frist-/Bindungsprüfung das größte aktuell gültige gleich große Paket zwischen denselben Parteien. Der vorhandene exakte Solver wird mit einem expliziten Counter-Minimum von eins wiederverwendet. Initiale Requests/Discovery behalten Default fünf; keine zweite Matchingengine und keine Änderung des bisherigen Rankings. Auch 1↔1-Counter erhalten ein Ergebnis; sie werden nicht durch die Effizienzbewertung gegenüber dem leeren Discovery-Plan unterdrückt.

Preview sendet nichts und legt keine Revision oder Bindung an. Die UI zeigt den genauen neuen Deal und verlangt „Gegenangebot senden“. Eine actor-/trade-/revisionsgebundene signierte Vorschau enthält die bestätigten Positionen und Commandidentität.

Beim Send unter derselben Schreibsperre: ursprüngliche Rolle/Revision erneut prüfen, Dreierlimit des neuen Senders prüfen, aktuell größtes Paket erneut berechnen und mit der bestätigten Vorschau vergleichen. Bei Änderung keine stille Anpassung, sondern erneute Prüfung verlangen. Danach alte Holds/Claims freigeben, Original superseded, Counterrevision versiegeln und aktuell setzen, aktuelle Regeln erneut validieren, ausschließlich neue Sender-Give/eigene Receive-Claims binden, Frist `counter_sent_at + 72h` speichern und Event/Command committen. Jeder Fehler stellt den ursprünglichen Zustand vollständig wieder her.

Die stabile Trade-Teilnehmeridentität wird nicht vertauscht; aktueller Sender/Empfänger wird aus der Angebotsrevision ermittelt. Ursprünglicher Sender kann den Counter über dieselbe Acceptance annehmen oder ablehnen. Ablehnung beendet ihn ohne Rücksprung. Retry verlängert keine Frist und erzeugt keine zweite Counterrevision.

## UI und Ereignisse

Vorhandene `/tauschen/anfragen/<id>`- und `/tauschen/laufend`-Ansichten werden erweitert. Nur aktueller Empfänger einer offenen Anfrage erhält „Annehmen“; nur beim Original zusätzlich „Tausch neu berechnen“. Sender-Withdraw und Empfänger-Reject bleiben rollenabhängig. Ungültige Originalannahme zeigt „Dieser Tausch ist so nicht mehr vollständig möglich“ und lässt das Paket unverändert.

Counter-Vorschau und expliziter Send-POST sind getrennt. Die Gegenseite sieht Herkunft des Gegenangebots und den neuen genauen Deal. Accepted zeigt „Tausch angenommen“ und „Als Nächstes: Sticker vorbereiten“, ohne Withdraw/Reject oder funktionslose Folgecontrols. Invalidated fordert einen neuen Trade und bietet keine weitere Neuberechnung.

Vorhandene `trade_events` referenziert die konkrete Revision: `OfferAccepted`, `OfferCountered`, `CounterAccepted`, `CounterRejected`, `CounterInvalidated` sowie bestehende/frisch abgegrenzte Release-Ereignisse. Keine Push- oder neue typisierte Notification-Infrastruktur behauptet. Alte Notificationtargets werden nicht umgedeutet.

## Tests und Browserabnahme

Vollständige source-only Arbeitskopie unter `/private/tmp/lifecycle03/`. Testdatenbanken ausschließlich frisch synthetisch aus Schema-/Fixture-SQL, keine realen DB-Kopien. Release- und Browserharness besitzen einen SQLite-Audit-Hook, der Datenbankpfade außerhalb `/private/tmp` verweigert. Temporäre synthetische Browser-DBs werden nach dem Lauf entfernt.

- **1.467 Release-Tests** grün, 0 Fehler/Failures/Skips. **12 bestehende Ausschlüsse unverändert**.
- Darin **45 neue L03-Tests**: 40 Domain/State/Migration/Concurrency, fünf produktive HTTP/UI-Tests. L01/L02 sowie Inventory, Reservation, Legacy, SAP, TradeV2 und SmartDeal enthalten.
- **8 separate Pax-/Trade-v2-Preview-Tests** grün.
- **900 bestehende binäre und 40 bestehende mengenbasierte unabhängige Solververgleiche** weiterhin grün.
- Browserflow A: senden → Gegenpartei nimmt exakt an → accepted, unveränderte Positionen und keine normalen Releaseaktionen.
- Browserflow B: Empfängersupply sinkt → Originalannahme scheitert verständlich → explizite Countervorschau und Send → ursprünglicher Sender nimmt Revision 2 an. Original bleibt historisch unverändert (10 ursprüngliche Positionszeilen, acht Counterzeilen im 5→4-Beispiel).
- Browserflow C: Counter wird ebenfalls ungültig → invalidated, alle offenen Bindungen frei, genau zwei Revisionen und keine weitere Neuberechnung.
- Keine JS-Fehler; terminale Ansicht ohne horizontalen Overflow bei 375/390/430/1280 px. **Acht Screenshots** und `results.json` unter `/private/tmp/lifecycle03/browser/`.

Explizite Konkurrenzfälle: Accept/Accept, Accept/Expiry, Accept/Withdraw, Accept/Reject; zwei Annahmen auf letzte Empfängersupply bzw. denselben Empfängerneed; Counter-Doppelklick, Counter/Expiry, Counter/Withdraw, Counter/Reject, Counter/kanonischer InventoryGuard; Counterannahme/anderer Accept und Counterannahme/kanonischer InventoryGuard. Gewinnerzustand und Mengen werden geprüft. Zusätzlich 20→17 ohne Shrink, asymmetrische manuelle Erstellerperspektive, kleiner Counter mit erhaltener SMARTDEAL-Herkunft, Counter-Dreierlimit, Rollback nach injiziertem Fehler, unveränderliche Snapshots/Accepted-Revision und Settingsänderungen.

Während der Entwicklung korrigierte ein neuer Test seine Erwartung auf die bewusst größtmögliche Countermenge statt nur den alten Ein-Sticker-Deal. Mindestgrößenprobe 1↔1 deckt explizit die Abgrenzung vom leeren Discovery-Plan ab. Bestehende Testanpassungen betreffen nur die neue Latest-Migration 25 beziehungsweise den entsprechenden vollständigen Migrationsbereich; keine neue Ausnahme oder abgeschwächte Legacy-Assertion.

Nachweise: `/private/tmp/lifecycle03/release-results.json`, `release.log`, `focused.log`, `ui.log`, `preview.log`, `browser/results.json`, `db-start.json`, `db-final.json`. Alle 16 geschützten DBs sind gegenüber der autorisierten Startbaseline bytegleich. Keine DB im Commitumfang, keine reale Migration.

## Abschluss und Grenzen

Keine normale Post-Acceptance-Cancellation, keine Packlisten, keine Kontrollfotos, keine Deal-Reduktion, keine Adressen, Versand, Empfang, Probleme, Bewertung, Zentrale oder Push. Kein Deploy. LIFECYCLE-04 nicht begonnen. Reale Migrationen benötigen weiterhin eine separate Freigabe.

`git diff --check` und `git diff --cached --check` werden vor Commit ohne Befund bestätigt; Index ausschließlich nach folgender L03-Dateiliste. Commitmessage: `feat: add lifecycle v1 trade acceptance`. End-Commit ist der Commit, der dieses Audit hinzufügt; vollständiger Hash und unabhängiger Remotevergleich werden im Abschlussbericht angegeben, ohne selbstreferenziellen Hash im Audit.

## Exakte Dateien

- `App/Database/migrations/0025_trade_lifecycle_acceptance.down.sql`
- `App/Database/migrations/0025_trade_lifecycle_acceptance.up.sql`
- `App/lifecycle_acceptance_routes.py`
- `App/lifecycle_request_routes.py`
- `App/services/_smartdeal_flow.py`
- `App/services/lifecycle_planning.py`
- `App/services/smartdeal_optimizer.py`
- `App/services/trade_lifecycle_acceptance.py`
- `App/services/trade_lifecycle_foundation.py`
- `App/services/trade_lifecycle_requests.py`
- `App/services/trade_v2_domain.py`
- `App/templates/lifecycle_counter_review.html`
- `App/templates/lifecycle_requests.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `docs/LIFECYCLE_03_AUDIT.md`
- `tests/research/check_lifecycle03.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle01_foundation.py`
- `tests/test_lifecycle03_acceptance.py`
- `tests/test_lifecycle03_ui.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`

## DB-SHA256 — vorher = nachher

| Datei | SHA256 |
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
