# CB-016 – Kontrollierter Legacy-Cutover

**Stand:** 21. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Echte Bestands-DB verändert:** NEIN

## 1. Ergebnis

CB-016 hat die nach CB-001 bis CB-015 verbliebenen operativen
Parallelwahrheiten kontrolliert entfernt oder fail-closed geschaltet. Für Home,
Feed, Notifications/Inbox, Profil/Account, Sammlung/Completion, Statistik,
Trophäen, Trade-Erfolg, SmartMatch und Privacy bleibt jeweils der bereits
abgenommene kanonische Servicevertrag maßgeblich.

Es wurden keine neuen Produktfunktionen, keine neue Semantik und keine
Datenmigration eingeführt. Historische Zeilen in Notifications, Trophäen,
Trades, Completion und Feed wurden weder gelöscht noch umgedeutet.

## 2. Vollständige Legacy-Inventur und Klassifikation A–E

### A – operative Legacy-Pfade, in CB-016 entfernt oder abgeschaltet

- `OperationalHomeService`: nach dem CB-012-Home-Cutover ohne Runtime-
  Verbraucher; Service und isolierte S25-Service-Suite entfernt.
- `services.notifications`: generischer, untypisierter Notification-Writer und
  paralleler Unread-Reader entfernt. Test-Fixtures legen historische Altzeilen
  nun ausdrücklich direkt an; produktive Writes bleiben beim CB-008-Katalog.
- Pre-V15-Trophy-Writer in `record_trophy_unlocks`: schreibt auf alten Schemas
  nicht mehr nach `unlocked_trophies`; kanonische V15+-Unlocks bleiben
  unverändert read-only für Popups nutzbar.
- dynamische Pre-V15-Trophy-Reads: Bestandsmenge wird nicht mehr als historisch
  freigeschaltete Trophy ausgegeben. Alte Schemas verhalten sich fail-closed.
- globale/generische Trophy-Berechnung und globale Trophy-Renderer: entfernt;
  `/trophaeen` zeigt nur die kanonische Unlock-Anzahl, sonst null.
- Pre-History-Profilfallback: `_legacy_current_albums` und dessen direkte
  Inventory-Fortschrittsberechnung entfernt. `CollectorProfileService` liest
  Sammlung und Abschlüsse ausschließlich über `CollectionProjectionService`.

### B – notwendige kontrollierte Kompatibilitätspfade, bewusst erhalten

- `/home` leitet nach `/`; `/zentrale` und `/sammlr-zentrale` leiten nach
  `/sammlung`. Die Redirects schreiben nicht und schaffen keine zweite Wahrheit.
- bestehende Singular-/Plural-Trade-Deep-Links bleiben sichere Route-Aliasse auf
  denselben Lifecycle-Handlern.
- `trade_is_successfully_completed` bleibt ein UI-Adapter, delegiert aber
  vollständig an die statischen CB-010-Prädikate.
- CB-010 liest deduplizierte erfolgreiche Legacy-Trades weiterhin
  `LEGACY_READ_ONLY`; dies ist historischer Erfolgsnachweis, kein Writer.
- Legacy-Notification-Zeilen bleiben über `NotificationHistoryService` lesbar,
  erhalten aber kein rekonstruiertes Ziel und keinen neuen generischen Producer.
- `record_trophy_unlocks` bleibt für bestehende Mutation-Callsites als
  read-only Popup-Adapter; es filtert ausschließlich bereits kanonisch
  persistierte Unlocks und schreibt nie selbst.
- Auf Pre-Community-Migrationsständen verwendet die kanonische
  `CollectionProjectionService` die dort vorhandene Albumprivacy-Schnittstelle.
  Das ist nur Policy-Kompatibilität: Sammlung bleibt dieselbe Projektion und
  Current State wird nie als Completion-Historie rekonstruiert.
- `TopMatchOptimizationService` bleibt als Konfliktoptimierer über
  `ExecutableTradeMatchService`; er besitzt keine alternative Matchbarkeit.

### C – historische Bestandsdaten, unangetastet

- `unlocked_trophies` einschließlich nicht validierter/globaler Legacy-Zeilen;
- alte und typisierte `notifications`-Zeilen;
- Legacy-`trade_requests`, kanonische Lifecycle-Trades und Tradehistorie;
- `historical_album_records`, Completion-Fakten und Inventory-History;
- `canonical_trophy_unlocks` und zugehörige Evidenz;
- `feed_events`, `user_activity` sowie Account-/Profilinformationen.

Der gezielte Test beweist sowohl den unveränderten Zeilenbestand bei Reads als
auch, dass eine Legacy-Trophy nicht in die kanonische Produktwahrheit aufsteigt.

### D – sicher entfernter toter Code

- nicht mehr importierter `operational_home.py` samt S25-Servicetest;
- ungenutzte globale Trophy-Definition-Adapter und Renderer;
- ungenutzte generische/nearest/locked-next-Trophy-Helper;
- globale Trophy-Unlock-Prüfung und deren indirekter Popup-Aufruf;
- veraltete RC-Coverage-Verweise auf S25 und den alten Trophy-Writer.

### E – außerhalb CB-016, dokumentiert und nicht vorgezogen

- Archive, Rescue-/Backup-Dateien und frühere Sprintreports sind nicht Teil des
  produktiven Imports und bleiben als Entwicklungsartefakte bestehen;
- `LegacyTrophyBackfillService` und das CB-004-Backfill-Skript bleiben für den
  bereits abgenommenen expliziten Audit-/Apply-Prozess erhalten, nicht als
  Runtime-Writer;
- physische Löschung historischer Tabellen/Zeilen, neue Retentionregeln und
  Post-Beta-Pakete CB-101 ff.;
- Styles ohne nachweislich exklusiven Legacy-Verbraucher wurden nicht auf
  Verdacht entfernt. Produktive Templates sind inline; es wurde kein separat
  ladendes Alt-Template gefunden.

## 3. Kanonische Source of Truth je Produktbereich

- Home und Feed: `FeedEventService` (CB-007/012).
- Notification-Produktion: `TypedNotificationService` und bestätigter
  CB-008-Katalog; Inbox: `NotificationHistoryService` (CB-009).
- Profil: `CollectorProfileService`; Account: `AccountSettingsService`
  (CB-014).
- Sammlung/Completion: `CollectionProjectionService` plus kanonische
  Completion-Fakten (CB-003/004/013).
- Statistik: `StatisticsProjectionService` (CB-015).
- Trophäen: `CanonicalTrophyUnlockService` und kuratierte Definitionen
  (CB-005).
- erfolgreicher Trade: `SuccessfulTradeProjectionService` (CB-010).
- Matchbarkeit/Priorisierung: `ExecutableTradeMatchService`, darauf aufbauend
  konfliktfreie Auswahl durch `TopMatchOptimizationService` (CB-011).
- äußeres Privacy-Gate: `ProfilePrivacyService`; innere Albumebene:
  `AlbumPrivacyService` (CB-006/S27).

## 4. Redirect-, Deep-Link- und Privacy-Verhalten

Die drei alten Home-/Zentralen-URLs redirecten deterministisch auf die
kanonischen Ziele. Trade-Aliasse treffen dieselben autorisierten Handler.
Notification-Legacyzeilen besitzen bewusst kein semantisch rekonstruiertes
Ziel. Private Profile, private/friends-only Alben und Blocks bleiben auch über
direkte Profil-, Album-, Sticker-, Match- und Tradepfade fail-closed.

Vier explizite Negativtests für Blockvorrang, private Profil-Deep-Links,
Albumprivacy und blockierte Match-/Tradepfade sind grün.

## 5. Migration und Datenwirkung

CB-016 ist ein reiner Code-, Routing- und Service-Cutover. Es gibt keine V0019,
keinen Backfill und keine Datenlöschung. Eine isolierte Kopie der echten V7-DB
wurde erfolgreich nach V18 migriert und ausschließlich für Startup-/HTTP-
Smokes verwendet.

Echte Bestands-DB vor und nach CB-016:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

Die echte DB blieb auf dem bestätigten V7-Stand (`schema_migrations`), wurde
nicht migriert und nicht verändert.

## 6. Geänderte Dateien

- `App/webapp.py`: Trophy-Legacy-Reads/-Writer/-Renderer entfernt oder
  fail-closed; kanonische Cabinet-Route vereinheitlicht.
- `App/services/notifications.py`: generischen parallelen Writer/Reader
  entfernt.
- `App/services/operational_home.py`: toten Pre-CB-012-Service entfernt.
- `App/services/collector_profiles.py`: parallele Pre-History-
  Inventoryprojektion entfernt.
- `App/services/collection_projection.py`: eng begrenzte Privacy-Policy-
  Kompatibilität für alte Migrationsfixtures innerhalb derselben Projektion.
- `tests/test_cb016_legacy_cutover.py`: gezielter Cutover-Vertrag.
- `tests/test_cb005_canonical_trophy_truth.py`,
  `tests/test_cb012_feed_home_cutover.py`,
  `tests/test_s03_side_effect_security_gate.py`,
  `tests/test_s16_trade_receipt.py`,
  `tests/test_s17_trade_problems_partial_receipt.py`,
  `tests/test_s23_typed_notifications.py`,
  `tests/test_s33_http_integrity_hardening.py`,
  `tests/test_s38_release_candidate.py`: alte Writer-/Home-Erwartungen auf den
  Cutover und die kanonischen RC-Nachweise aktualisiert.
- dieser Report und der Closed-Beta-Bauplan.

## 7. Tests

Gezielte CB-016-Suite:

- **7/7**, `OK`, 0 Fehler, 0 Skips.

Kombinierte Routing/Legacy/Privacy-Suite:

- **77/77**, `OK`, 0 Fehler, 0 Skips.

Kombinierte Collection/Profile/Stats/Feed/Notification-Suite:

- **136/136**, `OK`, 0 Fehler, 0 Skips.

Kombinierte Trade/Lifecycle/SmartMatch-Suite:

- **247/247**, `OK`, 0 Fehler, 0 Skips.

Privacy-/Deep-Link-Negativtests:

- **4/4**, `OK`, 0 Fehler, 0 Skips.

Vollständige Regressionen im expliziten S32/S35-Testenvironment:

- Lauf 1: **704/704**, `OK`, 0 Fehler, 0 Skips;
- Lauf 2: **704/704**, `OK`, 0 Fehler, 0 Skips.

Ein vorheriger Diagnose-Discover ohne das explizite S32-Test-Secret war kein
Abnahmelauf. Er deckte außerdem zwei veraltete RC-Metadatenverweise und eine
alte S33-Trophy-Writer-Erwartung auf; alle drei wurden auf den bestätigten
kanonischen Vertrag aktualisiert. Die beiden oben ausgewiesenen vollständigen
Abnahmeläufe wurden danach sauber neu ausgeführt.

## 8. Integrity, FK, Startup, HTTP und Diff

- echte V7-Bestands-DB: `PRAGMA integrity_check = ok`;
- echte V7-Bestands-DB: `PRAGMA foreign_key_check` ohne Treffer;
- isolierte V7→V18-Kopie: Migrationen 8 bis 18 erfolgreich,
  `integrity_check = ok`, FK-Check ohne Treffer;
- Startup-Smoke auf isolierter V18-Kopie: Import erfolgreich;
- `/healthz`, `/`, `/sammlung`, `/trades`, `/notifications`, `/profil`,
  `/account`, `/statistik`, `/trophaeen`: jeweils HTTP 200;
- `git diff --check`: ohne Befund;
- Bestands-DB-SHA-256 vor/nachher: unverändert und identisch zur bestätigten
  Baseline.

## 9. Product-Contract-Bewertung und Restrisiken

Product-Contract-Verletzung: **NEIN**. Keine neue Produktlogik, kein Feature,
keine Migration, kein Datenverlust und kein Privacy-Bypass wurden eingeführt.

Bewusste Restrisiken sind ausschließlich kontrollierte Kompatibilität:
Legacy-Trades bleiben gemäß CB-010 als deduplizierter historischer
Erfolgsnachweis lesbar; alte Notification-Zeilen bleiben ohne rekonstruiertes
Ziel lesbar; Archive und Backfill-Werkzeuge bleiben außerhalb des Runtime-
Imports erhalten. Diese Pfade sind keine alternativen Writer.

## 10. Abschluss und nächster Block

CB-016 ist formal abgeschlossen und technisch abgenommen. Damit sind **16 von
17** Closed-Beta-Kernblöcken abgeschlossen.

**CB-017 – Integrierter Closed-Beta-RC-Nachweis** ist als nächster und letzter
P1-Kernblock bereit.
