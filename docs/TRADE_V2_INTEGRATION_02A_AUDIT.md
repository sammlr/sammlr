# INTEGRATION-02A – gemeinsame produktive Trade-v2-Präferenzen

## Ergebnis und Grenze

Domain + additive Persistenz + produktiver Read-Pfad umgesetzt. Keine Settings-UI,
keine SAP-01-Implementierung, keine Requests, Reservierungen, Slots oder Lifecycle-
Mutationen. Keine lokale/produktive DB migriert. Kein Commit, Push oder Deploy.
BORSE-UI-01 samt akzeptiertem kanonischem Bubble-Bestandsfehler bleibt unverändert.

## Persistenzbefund und Migrationsplan

Bisherige Source of Truth: `user_albums.trade_pool_enabled` (Migration 0007),
bezogen auf die existierende User-/Album-Mitgliedschaft. `users.favorite_album_id`
bleibt unverändert. Die isolierten Trade-v2-Preview-Fixtures waren bisher keine
produktive Präferenzpersistenz und werden nicht als Datenquelle übernommen.

Neue einzige Source of Truth: `user_albums.cross_album_mode`. Migration 0022
fügt ausschließlich diese NOT-NULL-TEXT-Spalte mit CHECK-Constraint und Default
`SAME_ALBUM_ONLY` hinzu. Keine neue Tabelle, Schatten-JSON oder Datenkopie.
Bestehende Pool-Freigaben, Mitgliedschaften, Inventare und Trades bleiben erhalten.

Vorhandener Migrationsrunner bleibt zuständig. Auf Schema 20/21 wird eine noch
fehlende Spalte ausschließlich lesend als fehlende Präferenz ausgewertet. Der
zentrale Default ist SAME_ALBUM_ONLY; unbekannte Werte werden abgelehnt. Es gibt
keine automatische Migration beim Lesen oder Appstart. Das interne Schreib-Hook
setzt eine existierende Mitgliedschaft und Schema 22 voraus; Authentisierung und
Transaktionsabschluss obliegen dem späteren aufrufenden Service. Kein HTTP-Write-
Endpunkt wurde ergänzt.

Der produktive App-Einstieg und Healthcheck akzeptieren explizit Schema 20, 21
und 22. Der bestehende strikte Default des allgemeinen DB-Validators sowie der
Bootstrap auf Schema 20 bleiben erhalten. Migration 0021 liegt vor 0022 und wird
nicht umgangen. Die Kompatibilitätsprojektion der drei vor V21 fehlenden Request-
SELECT-Felder wurde unverändert aus der Trade-Shell in einen gemeinsamen Adapter
verschoben; sie schreibt keine Legacy-Daten um.

Migration/Backout wurden nur auf aus SQL erzeugten synthetischen DBs unter
`/private/tmp` getestet. Für einen späteren realen Rollout sind vor Anwendung der
bestehende DB-Sicherungsprozess, verifizierte Sicherung und kontrollierte Migration
20 → 21 → 22 nötig. Dieser Auftrag hat keine reale Migration oder Kopie ausgeführt.
Der 0022-Backout verweigert das Entfernen der Spalte, sobald explizite CROSS-
Freigaben existieren, damit Zustimmung nicht still verloren geht.

## Zentrale Domain und SmartDeal

- `TradeV2Domain.market(actor, selected_albums=None)` liest in einem konsistenten
  Snapshot die kanonischen freigegebenen Alben, berechtigten Partner, relevanten
  Give-/Receive-Kandidaten, Reservierungen und bereits gebundenen Eingänge.
- `balance_groups` bildet je eingeschränktem Album einen eigenen Bereich und
  genau einen Pool der für beide Nutzer CROSS-freigegebenen Alben. Pool-disabled
  Alben gelangen über die kanonische Schnittmenge nicht in die Planung.
- `maximum_equal` summiert die richtungsbezogenen Minima pro zulässigem Bereich.
  `market.pairs` enthält auch Paare mit null Kapazität für spätere SAP-Suchen;
  `market.opportunities` nur positive Möglichkeiten.
- `validate_deal` kontrolliert konkrete Mengen, verfügbare/relevante Codes,
  doppelte Einträge, erlaubte Bereiche und Receive ≤ Give je Bereich. Freiwillig
  asymmetrische manuelle Angebote sind aus Sicht des Vorschlagenden zulässig;
  die Gegenpartei muss später explizit zustimmen. Vor einer späteren Bindung muss
  der aufrufende Service einen frischen serverseitigen Market lesen.
- `smartdeals` benutzt den bestehenden exakten SmartDeal-Optimizer. Die produktive
  Trade-Shell liest jetzt diese zentrale Market-Basis; auch der Partner-Deal nutzt
  die gleichen Opportunities. SAP, manuelle Auswahl und Amendments können später
  dieselbe Validierung auf ihr exaktes Paket anwenden, statt Regeln zu duplizieren.

Notwendige minimale Solver-Erweiterung: Der bisherige globale Partner-Fluss konnte
Give aus einem gesperrten Album mit Receive aus einem anderen Album verrechnen.
Optionale Balance-Gruppen ergänzen den vorhandenen Optimizer. Bei mehreren Gruppen
werden eigene erhaltende Bucket-Kanten und eine exakte ganzzahlige Suche über deren
Summen eingesetzt. Keine heuristische Abschneidung. Zielfunktion E/G/D/J/C,
Partnerauswahl, Mindestgröße, Ressourcenregeln und deterministische Tie-Breaks
bleiben erhalten; SmartDeals bleiben je Bereich symmetrisch. Legacy-Aufrufer ohne
Balance-Gruppen benutzen weiterhin die bisherige Semantik. Bestehende gebundene
Legacy-/SmartDeal-V1-Pakete werden weder migriert noch neu interpretiert.
Die exakte Suche hat wie der bestehende Optimizer kombinatorische Worst-Case-
Kosten; dies ist keine Behauptung einer neuen Produktions-Lastzusage.

## Nachweise

- Releasegate: **1.315 Tests bestanden**, keine Fehler/Skips. Die **12 bestehenden
  R5-Vertragsausschlüsse** bleiben unverändert; keine neuen Ausschlüsse.
- Separate Pax-/Trade-v2-Preview-Gates: **8 Tests bestanden**.
- Darin 12 neue Domain-/Migrations-/Solver-Tests: A–J und L direkt abgedeckt;
  K durch All-Cross-Parität mit dem alten Optimizer und unveränderte bestehende
  Favoriten-/Ranking-Regressionen. Migration vergleicht alle vorher vorhandenen
  Spalten sämtlicher Anwendungstabellen vor/nach Migration; Integrität/FKs,
  Idempotenz, Default, Constraint und verweigerter verlustbehafteter Backout geprüft.
- **900 unabhängige exhaustive Feasibility-Vergleiche** auf 60 deterministischen
  Graphen: exakte Größen, Größenintervalle, Gesamtgrenzen, festgelegte Ein-/Ausgänge,
  Ressourcen und mehrere Balance-Gruppen. Separater globaler Allokationstest.
- Produktive Flask-Routen/Healthcheck auf synthetischem Schema 20 und 22 geprüft:
  ohne Cross-Freigabe kein unerlaubter Vorschlag; mit beidseitiger Freigabe ein
  gültiger Vorschlag. DB-Hash jeweils vor/nach HTTP identisch.
- Historische Tests mit Erwartung „letzte vorhandene Migration = 21“ wurden gezielt
  auf 22 aktualisiert. Der ausdrücklich V21 prüfende SD-T1-Test migriert jetzt
  explizit auf 21. Keine Assertions entfernt oder neue Ausschlüsse eingeführt.
- Anfangs fehlgeschlagene Testläufe: falscher Rollback-Import im neuen Test,
  veraltete Latest-Version-Erwartungen und eine zu breite HTTP-200-Erwartung für
  einen Partner ohne gültigen Deal. Diese Testfehler wurden korrigiert und die
  betreffenden Gates vollständig erneut ausgeführt.
- DB-Schutz: **15/15 lokale Dateien vorhanden und SHA256-identisch**; nur synthetische
  SQL-Testdaten unter `/private/tmp`, keine reale DB als Testquelle. Hashpaare in
  `tests/research/artifacts/integration-02a/db-hashes.json`.

Maschinenlesbare Ergebnisse liegen unter `tests/research/artifacts/integration-02a/`.

## Exakter Dateiumfang dieses Auftrags

Geänderte bestehende Dateien:

- `App/services/_smartdeal_flow.py`
- `App/services/runtime_operations.py`
- `App/services/smartdeal_optimizer.py`
- `App/services/smartdeal_pairwise.py`
- `App/trade_shell.py`
- `App/webapp.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`
- `tests/test_sd_t1_contract_foundation.py`

Neue Implementierungs-/Test-/Auditdateien:

- `App/Database/migrations/0022_trade_v2_album_preference.up.sql`
- `App/Database/migrations/0022_trade_v2_album_preference.down.sql`
- `App/services/trade_planning_compat.py`
- `App/services/trade_v2_rules.py`
- `App/services/trade_v2_preferences.py`
- `App/services/trade_v2_domain.py`
- `App/services/_trade_v2_flow.py`
- `tests/test_integration02a_trade_preferences.py`
- `tests/research/check_integration02a.py`
- `docs/TRADE_V2_INTEGRATION_02A_AUDIT.md`

Neue Ergebnisdateien:

- `tests/research/artifacts/integration-02a/browser-gates.json`
- `tests/research/artifacts/integration-02a/checks.json`
- `tests/research/artifacts/integration-02a/db-hashes.json`
- `tests/research/artifacts/integration-02a/git-status-summary.json`
- `tests/research/artifacts/integration-02a/http-smoke.json`
- `tests/research/artifacts/integration-02a/release-tests.json`
- `tests/research/artifacts/integration-02a/scope.json`

## Finale Regression und Gitstatus

TRADE-01–11 Browserregressionen bestanden bei 375/390/430/1280 px, einschließlich
Lifecycle, manueller Auswahl, Interaktion, reduzierter Animation und Overflow.
Zusätzlich 28 kanonische numerische Stack-Vergleiche für Mengen 1/2/5/6/10/15/37:
Wall-Cap 5, Trade-Cap 10, Geometrieparität bestätigt. Browserbilder liegen ausschließlich
in der isolierten Testkopie `/private/tmp/integration01-tests/tests/research/artifacts/`;
die bestehenden visuellen Abnahme-Artefakte im Projekt wurden nicht überschrieben.

`git diff --check` und `git diff --cached --check`: beide ohne Befund.
Index leer. HEAD unverändert `89c957de0b3ab9f412c6d8f6648cb00f3184a051`.
27 tracked Modifikationen insgesamt: 24 in diesem Auftrag, dazu drei unveränderte
vorbestehende BORSE-UI-Dateien (CSS, JS, Template). Die vorhandenen BORSE-Änderungen
in `App/trade_shell.py` bleiben ebenfalls erhalten. Viele bereits vorher ungetrackte
Projekt-/Design-Artefakte bleiben ungestagt; Statuszählung im Ergebnis-JSON.
Alle getesteten Implementierungs-/Testdateien stimmen bytegenau mit der isolierten
Testkopie überein. Keine neue DB im Repository; 15/15 geschützte DBs bytegleich.

## SAP-01-Bereitschaft

Ja: SAP-01 kann fachlich auf dem zentralen Market und der konkreten Dealvalidierung
aufbauen, ohne die Album-/Mengenregeln zu erfinden. Fehlende persistierte Präferenzen
haben bereits eine eindeutige konservative Bedeutung. Für echte persistierte CROSS-
Freigaben muss die getestete Migration 0022 separat kontrolliert ausgerollt werden;
eine Einstellungsoberfläche und produktive Write-Flows sind nicht Teil dieses Schritts.
