# SD-T1 Acceptance Fix 1.1 — V21-Testbaseline

Stand: 2026-09-10. Ausschließlich Test-/Release-Erwartungen. Alle 18 ursprünglichen Fehler wurden einzeln mit Assertion und vollständiger Testmethode geprüft: reine veraltete V20-Migrationsannahmen, keine semantische Regression. Keine festen Schema-/Fixture-Hashes neu berechnet; bestehende Hash-, Daten-, Legacy- und Constraint-Assertions bleiben erhalten.

| Testdatei | Methode | Ursprüngliche Assertion / Einordnung | Anpassung |
| --- | --- | --- | --- |
| [test_cb008_notification_catalog.py](../tests/test_cb008_notification_catalog.py) | `test_catalog_is_exact_and_no_cb008_migration_exists` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb009_inbox_read_retention.py](../tests/test_cb009_inbox_read_retention.py) | `test_no_migration_or_cb008_catalog_and_domain_sources_unchanged` | `self.assertEqual(20, max(migration.version for migration in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb011_executable_match_contract.py](../tests/test_cb011_executable_match_contract.py) | `test_no_migration_and_cb008_to_cb010_sources_untouched` | `self.assertEqual(20, max(item.version for item in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb012_feed_home_cutover.py](../tests/test_cb012_feed_home_cutover.py) | `test_no_migration_or_parallel_reconstruction_is_added` | `self.assertEqual(20, max(item.version for item in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb013_collection_completion_projection.py](../tests/test_cb013_collection_completion_projection.py) | `test_projection_is_read_only_immutable_and_adds_no_migration` | `self.assertEqual(20, max(item.version for item in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb014_profile_account_projection.py](../tests/test_cb014_profile_account_projection.py) | `test_no_migration_and_no_notification_or_feed_side_effect` | `self.assertEqual(20, max(item.version for item in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb015_statistics_projection.py](../tests/test_cb015_statistics_projection.py) | `test_projection_is_deterministic_immutable_read_only_and_has_no_migration` | `self.assertEqual(20, max(migration.version for migration in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_cb016_legacy_cutover.py](../tests/test_cb016_legacy_cutover.py) | `test_cutover_adds_no_schema_migration` | `self.assertEqual(20, max(item.version for item in load_migrations()))`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s26_collector_profiles.py](../tests/test_s26_collector_profiles.py) | `test_s26_adds_no_migration` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s27_album_privacy_trade_pool.py](../tests/test_s27_album_privacy_trade_pool.py) | `test_v0007_backfill_defaults_constraints_repeat_and_backout` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s28_trade_ratings.py](../tests/test_s28_trade_ratings.py) | `test_v0008_migration_existing_completed_trade_repeat_down_and_fail_closed` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s29_friendships_community.py](../tests/test_s29_friendships_community.py) | `test_v0009_migration_repeat_constraints_and_fail_closed_backout` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s31_ui_foundation.py](../tests/test_s31_ui_foundation.py) | `test_s31_adds_no_migration_and_reuses_existing_icons` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s32_auth_session_csrf.py](../tests/test_s32_auth_session_csrf.py) | `test_v0010_forward_repeat_and_fail_closed_backout` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s33_http_integrity_hardening.py](../tests/test_s33_http_integrity_hardening.py) | `test_v0011_forward_repeat_and_data_preserving_backout` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s35_account_lifecycle_privacy_performance.py](../tests/test_s35_account_lifecycle_privacy_performance.py) | `test_v0012_forward_repeat_and_fail_closed_backout` | `self.assertEqual(20, load_migrations()[-1].version)`; höchste verfügbare Migration | exakt 21 statt 20 |
| [test_s38_release_candidate.py](../tests/test_s38_release_candidate.py) | `test_fresh_s00_copy_migrates_to_latest_repeatedly_and_cleanly` | `tuple(range(1, LATEST_VERSION + 1)) gegen migrate(connection)`; vollständige aktuelle Migrationsfolge | separate LATEST_MIGRATION_VERSION=21, Folge1–21 |
| [test_s38_release_candidate.py](../tests/test_s38_release_candidate.py) | `test_migration_manifest_is_contiguous_and_canonical_files_are_unchanged` | `list(range(1, LATEST_VERSION + 1)) gegen Migrationsmanifest`; vollständige aktuelle Migrationsfolge | separate LATEST_MIGRATION_VERSION=21, Folge1–21 |

## Abgrenzung

16 punktuelle Maximalversions-Assertions und zwei S38-Migrationsprüfungen aktualisiert. Historische Fixture-Versionen (z. B. V6/V7/V18), gezielte Upgrade-/Rollbackziele und Datenprüfungen bleiben unverändert. S38 trennt `LATEST_MIGRATION_VERSION=21` von `LATEST_VERSION=20` für den bestehenden Produktionsvertrag. Der Runtime-Startguard und Bootstrap sind weiterhin V20; ein V21-Produktionsstart wird hier weder freigeschaltet noch als geprüft behauptet.

Ein erster Lauf mit gemeinsam auf21 gesetzter S38-Konstante erzeugte einen zusätzlichen Produktions-Smoke-Error: der unveränderte Startguard lehnte das unbeabsichtigt auf21 erzeugte Produktionsfixture korrekt ab. Deshalb wurden die Konstanten getrennt und der ursprüngliche V20-Produktionsprüfvertrag wiederhergestellt, ohne Runtime-Änderung oder Entfernung von Assertions.

`docs/R5_RELEASE_FILES.json` nimmt genau die vier bereits implementierten SD-T1-Dateien zusätzlich auf (Migration0021 UP/DOWN, Domain-Helper,18 Foundationtests). Reproduzierbarer Allowlist-Export:2215 Dateien, keine manuellen Code-Overlays erforderlich. Keine Änderung der Cohort-Klassifikation;9 historische und3 Baseline-Methoden bleiben wie im B1.1-Vertrag getrennt.

## Prüfung

- Foundation und fokussierte Schema-/Migrationsprüfungen:29/29 bestanden (18 Foundation +11 Schema/Migration).
- Ursprüngliche18 Fehlermethoden einzeln erneut ausgeführt:18/18 bestanden.
- Trade-/Legacy-Regression:126/126 bestanden.
- Vollständiger finaler Release-Lauf: **885/885 bestanden**,0 Failures,0 Errors,0 Skips;897 entdeckt, davon unverändert9 historisch und3 Baseline separat klassifiziert.

Logs: `/private/tmp/sdt11-focused-final.log`, `/private/tmp/sdt11-original18.log`, `/private/tmp/sdt11-trade.log`, `/private/tmp/sdt11-full-final.log`. Isolierter Export: `/private/tmp/sammlr-sdt11-final`; ausschließlich synthetische Testdaten.

Kanonische DB bleibt V20, SHA-256 vorher/nachher: `a183302bea3a50201d3036f5b14999da5d138a0a5156044f814c3d30880d0c56`; Integrity `ok`, FK0. Runtime, Services, UI, Routes, Migration0021, Bible und Algorithm Contract unverändert. Kein SD-T2a, kein git add/Commit/Push/Deploy.
