"""S38 release-candidate gates on isolated SQLite copies only."""

from __future__ import annotations

import hashlib
import ast
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FIXTURE = PROJECT_ROOT / "App" / "Database" / "sammlr_reference_s00.db"
LOCAL_DATABASE = PROJECT_ROOT / "App" / "Database" / "sammlr.db"
# Bootstrap remains V20; the additive lifecycle shipping migration is V28.
LATEST_VERSION = 20
LATEST_MIGRATION_VERSION = 28


sys.path.insert(0, str(PROJECT_ROOT))

from App.Database.migration_runner import (  # noqa: E402
    applied_migrations,
    current_version,
    load_migrations,
    migrate,
)
from App.Database.sqlite_recovery import (  # noqa: E402
    sha256_file,
    validate_artifact,
)
from Scripts.predeploy import run_predeploy  # noqa: E402


REQUIRED_RC_TESTS = {
    "account": (
        "tests.test_s32_auth_session_csrf",
        "AuthSessionCsrfTestCase",
        "test_registration_stores_only_canonical_scrypt_and_hides_details",
    ),
    "profile": (
        "tests.test_s26_collector_profiles",
        "CollectorProfilesTestCase",
        "test_own_profile_remains_reachable_and_editable",
    ),
    "data_export": (
        "tests.test_s36_user_data_export_compliance",
        "UserDataExportComplianceTestCase",
        "test_complete_export_contains_owned_domains_and_trade_history",
    ),
    "deactivate_reactivate": (
        "tests.test_s35_account_lifecycle_privacy_performance",
        "AccountLifecyclePrivacyPerformanceTestCase",
        "test_deactivate_invalidates_session_and_explicit_reactivation_creates_it",
    ),
    "collection": (
        "tests.test_s01_inventory_regression",
        "InventoryRegressionTestCase",
        "test_add_existing_sticker_updates_quantity_and_duplicates",
    ),
    "album_add": (
        "tests.test_s04_home_collection_routes",
        "HomeCollectionRoutesTestCase",
        "test_album_addition_returns_to_collection_and_preserves_membership",
    ),
    "inventory_remove": (
        "tests.test_s01_inventory_regression",
        "InventoryRegressionTestCase",
        "test_remove_existing_sticker_updates_quantity_and_duplicates",
    ),
    "inventory_filter": (
        "tests.test_s01_inventory_regression",
        "InventoryRegressionTestCase",
        "test_stickerwall_filter_predicate_covers_all_states",
    ),
    "inventory_undo": (
        "tests.test_s01_inventory_regression",
        "InventoryRegressionTestCase",
        "test_undo_restores_add_inventory_change",
    ),
    "trophies": (
        "tests.test_cb005_canonical_trophy_truth",
        "CanonicalTrophyTruthTestCase",
        "test_persisted_unlock_remains_visible_after_inventory_reduction",
    ),
    "incoming_transit": (
        "tests.test_s19_receipt_ux_hardening",
        "ReceiptUxHardeningRouteRegressionTestCase",
        "test_wall_marks_missing_transit_and_keeps_progress_and_filters_physical",
    ),
    "manual_trade": (
        "tests.test_s02_tradeflow_regression",
        "TradeflowRegressionTestCase",
        "test_trade_request_creates_open_manual_package_without_booking",
    ),
    "smart_trade": (
        "tests.test_s22_smart_trade_requests",
        "SmartTradeRequestTestCase",
        "test_route_happy_path_creates_request_then_existing_acceptance_reserves",
    ),
    "reservation": (
        "tests.test_s14_trade_reservations",
        "TradeReservationTestCase",
        "test_valid_acceptance_reserves_every_outgoing_position",
    ),
    "shipping": (
        "tests.test_s15_trade_shipping",
        "TradeShippingTestCase",
        "test_both_sides_ship_independently_without_completing_trade",
    ),
    "receipt": (
        "tests.test_s16_trade_receipt",
        "TradeReceiptTestCase",
        "test_second_receipt_completes_trade_and_lifecycle",
    ),
    "problem": (
        "tests.test_s19_receipt_ux_hardening",
        "ReceiptUxHardeningRouteRegressionTestCase",
        "test_missing_route_inventory_transit_report_retry_and_resolution",
    ),
    "wrong_sticker": (
        "tests.test_s19_receipt_ux_hardening",
        "ReceiptUxHardeningRouteRegressionTestCase",
        "test_wrong_sticker_route_inventory_transit_report_retry_and_resolution",
    ),
    "damaged_sticker": (
        "tests.test_s19_receipt_ux_hardening",
        "ReceiptUxHardeningRouteRegressionTestCase",
        "test_damaged_route_inventory_transit_report_retry_and_resolution",
    ),
    "problem_close_and_late_resolution": (
        "tests.test_s18_2_problem_trade_finalization",
        "ProblemTradeFinalizationTestCase",
        "test_close_and_late_resolution_are_idempotent_and_append_only",
    ),
    "notification": (
        "tests.test_s24_notification_history_navigation",
        "NotificationHistoryNavigationTestCase",
        "test_lifecycle_notification_click_uses_canonical_trade_target",
    ),
    "notification_badge": (
        "tests.test_s24_notification_history_navigation",
        "NotificationHistoryNavigationTestCase",
        "test_badge_zero_one_ninety_nine_and_hundred",
    ),
    "notification_history_read": (
        "tests.test_s24_notification_history_navigation",
        "NotificationHistoryNavigationTestCase",
        "test_request_notification_click_reads_and_opens_with_origin",
    ),
    "home": (
        "tests.test_cb012_feed_home_cutover",
        "CB012FeedHomeCutoverTestCase",
        "test_own_start_and_completion_render_in_canonical_order_and_deep_link",
    ),
    "privacy": (
        "tests.test_s27_album_privacy_trade_pool",
        "AlbumPrivacyTradePoolTestCase",
        "test_private_and_friends_hide_profile_aggregates_wall_and_detail",
    ),
    "public_privacy": (
        "tests.test_s27_album_privacy_trade_pool",
        "AlbumPrivacyTradePoolTestCase",
        "test_public_foreign_wall_and_detail_are_exact_read_only",
    ),
    "trade_pool": (
        "tests.test_s27_album_privacy_trade_pool",
        "AlbumPrivacyTradePoolTestCase",
        "test_coverage_top_match_and_smart_request_share_trade_pool",
    ),
    "rating": (
        "tests.test_s28_trade_ratings",
        "TradeRatingsTestCase",
        "test_one_final_rating_per_direction_independent_and_no_delete_route",
    ),
    "rating_aggregation": (
        "tests.test_s28_trade_ratings",
        "TradeRatingsTestCase",
        "test_average_rounding_count_and_immediate_profile_aggregation",
    ),
    "community": (
        "tests.test_s29_friendships_community",
        "FriendshipsCommunityTestCase",
        "test_request_notifies_recipient_but_accept_does_not_notify",
    ),
    "community_block_unblock": (
        "tests.test_s29_friendships_community",
        "FriendshipsCommunityTestCase",
        "test_block_cancels_only_unaccepted_requests_preserves_running_trade_and_unblock_does_not_restore",
    ),
    "community_search": (
        "tests.test_s29_friendships_community",
        "FriendshipsCommunityTestCase",
        "test_search_prefix_limit_sort_and_existing_friend_marker",
    ),
}


class ReleaseCandidateGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_hash = sha256_file(REFERENCE_FIXTURE)
        cls.local_hash = sha256_file(LOCAL_DATABASE)

    @classmethod
    def tearDownClass(cls):
        assert cls.fixture_hash == sha256_file(REFERENCE_FIXTURE)
        assert cls.local_hash == sha256_file(LOCAL_DATABASE)

    def test_fresh_s00_copy_migrates_to_latest_repeatedly_and_cleanly(self):
        with tempfile.TemporaryDirectory(prefix="sammlr-s38-fresh-") as directory:
            database = Path(directory) / "rc1-fresh.db"
            shutil.copy2(REFERENCE_FIXTURE, database)
            with sqlite3.connect(database) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                self.assertEqual(0, current_version(connection))
                self.assertEqual(
                    tuple(range(1, LATEST_MIGRATION_VERSION + 1)), migrate(connection)
                )
                self.assertEqual((), migrate(connection))
                self.assertEqual(LATEST_MIGRATION_VERSION, current_version(connection))
                self.assertEqual(
                    list(range(1, LATEST_MIGRATION_VERSION + 1)),
                    [entry.version for entry in applied_migrations(connection)],
                )
                self.assertEqual([("ok",)], connection.execute(
                    "PRAGMA integrity_check"
                ).fetchall())
                self.assertEqual([], connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall())
            artifact = validate_artifact(database, expected_version=LATEST_MIGRATION_VERSION)
            self.assertEqual(database.resolve(), artifact.path)

    def test_realistic_v0007_copy_is_backed_up_then_upgraded_to_latest(self):
        with tempfile.TemporaryDirectory(prefix="sammlr-s38-upgrade-") as directory:
            root = Path(directory)
            database = root / "rc1-upgrade.db"
            backup_directory = root / "backups"
            shutil.copy2(LOCAL_DATABASE, database)
            with sqlite3.connect(database) as connection:
                before = current_version(connection)
            self.assertEqual(7, before)

            result = run_predeploy(database, backup_directory)

            self.assertEqual(
                list(range(8, LATEST_VERSION + 1)), result["applied_migrations"]
            )
            self.assertEqual(before, result["backup_version"])
            self.assertEqual(LATEST_VERSION, result["database_version"])
            backup = Path(result["backup_path"])
            self.assertTrue(backup.is_file())
            validate_artifact(backup, expected_version=before)
            upgraded = validate_artifact(database, expected_version=LATEST_VERSION)
            self.assertNotEqual(result["backup_sha256"], upgraded.sha256)
            environment = os.environ.copy()
            environment.update({
                "DATABASE_PATH": str(database),
                "PYTHONDONTWRITEBYTECODE": "1",
                "SAMMLR_ENV": "testing",
                "SAMMLR_SECRET_KEY": "s38-upgrade-smoke-secret",
            })
            smoke = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.path.insert(0, 'App'); import webapp; "
                    "print(webapp.app.test_client().get('/healthz').status_code)",
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=20,
                check=True,
            )
            self.assertEqual("200", smoke.stdout.strip().splitlines()[-1])

    def test_production_import_health_login_assets_and_debug_surface(self):
        with tempfile.TemporaryDirectory(prefix="sammlr-s38-prod-") as directory:
            database = Path(directory) / "rc1-production.db"
            shutil.copy2(REFERENCE_FIXTURE, database)
            with sqlite3.connect(database) as connection:
                migrate(connection, LATEST_VERSION)
            probe = r'''
import json, os, sqlite3, sys
from pathlib import Path
sys.path.insert(0, "App")
import services.runtime_operations as runtime
runtime.PRODUCTION_DATABASE_PATH = Path(os.environ["DATABASE_PATH"])
from gunicorn.util import import_app
application = import_app("webapp:app")
client = application.test_client()
login_page = client.get("/login")
with client.session_transaction() as login_session:
    csrf_token = login_session["csrf_token"]
login = client.post("/login", data={
    "username": "fixture_user_1", "password": "fixture-only",
    "_csrf_token": csrf_token,
})
pages = {
    path: client.get(path).status_code
    for path in ("/", "/sammlung", "/trades", "/notifications", "/profil")
}
mutating_gets = {
    path: client.get(path).status_code
    for path in ("/logout", "/add/vfl/1", "/undo", "/notifications/1/read")
}
with client.session_transaction() as active_session:
    logout_token = active_session["csrf_token"]
logout = client.post("/logout", data={"_csrf_token": logout_token})
logged_out_home = client.get("/")
print(json.dumps({
    "gunicorn_app": application.name,
    "proxy": type(application.wsgi_app).__name__,
    "health": client.get("/healthz").status_code,
    "login_page": login_page.status_code,
    "login": login.status_code,
    "asset": client.get("/static/style.css").status_code,
    "debug_db": client.get("/debug-db").status_code,
    "debug_seed": client.get("/debug-seed-now").status_code,
    "pages": pages,
    "mutating_gets": mutating_gets,
    "logout": logout.status_code,
    "logged_out_home": logged_out_home.status_code,
}, sort_keys=True))
'''
            environment = os.environ.copy()
            environment.update({
                "DATABASE_PATH": str(database),
                "PORT": "8000",
                "PYTHONDONTWRITEBYTECODE": "1",
                "SAMMLR_ENV": "production",
                "SAMMLR_SECRET_KEY": "s38-isolated-production-secret",
            })
            result = subprocess.run(
                [sys.executable, "-c", probe],
                cwd=PROJECT_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=True,
            )
            contract = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual("webapp", contract["gunicorn_app"])
            self.assertEqual("ProxyFix", contract["proxy"])
            self.assertEqual(200, contract["health"])
            self.assertEqual(200, contract["login_page"])
            self.assertEqual(302, contract["login"])
            self.assertEqual(200, contract["asset"])
            self.assertEqual({"/debug-db": 404, "/debug-seed-now": 404}, {
                "/debug-db": contract["debug_db"],
                "/debug-seed-now": contract["debug_seed"],
            })
            self.assertTrue(all(code == 200 for code in contract["pages"].values()))
            self.assertTrue(
                all(code == 405 for code in contract["mutating_gets"].values())
            )
            self.assertEqual(302, contract["logout"])
            self.assertEqual(302, contract["logged_out_home"])

    def test_production_secret_is_fail_closed_and_scrypt_is_available(self):
        self.assertTrue(hasattr(hashlib, "scrypt"))
        probe = "import sys; sys.path.insert(0, 'App'); import webapp"
        environment = os.environ.copy()
        environment.update({
            "SAMMLR_ENV": "production",
            "DATABASE_PATH": "/var/data/sammlr.db",
            "PORT": "8000",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        environment.pop("SAMMLR_SECRET_KEY", None)
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("SAMMLR_SECRET_KEY is required", result.stderr)

    def test_rc_core_journey_has_executable_contract_coverage(self):
        with tempfile.TemporaryDirectory(prefix="sammlr-s38-journey-") as directory:
            database = Path(directory) / "rc1-journey.db"
            shutil.copy2(REFERENCE_FIXTURE, database)
            with sqlite3.connect(database) as connection:
                migrate(connection, LATEST_VERSION)
                self.assertGreaterEqual(
                    connection.execute("SELECT COUNT(*) FROM users").fetchone()[0], 3
                )
                self.assertGreaterEqual(
                    connection.execute(
                        "SELECT COUNT(DISTINCT album_id) FROM user_albums"
                    ).fetchone()[0],
                    3,
                )
                inventory_profiles = connection.execute(
                    "SELECT user_id, COUNT(*), SUM(quantity), SUM(duplicates) "
                    "FROM stickers GROUP BY user_id ORDER BY user_id"
                ).fetchall()
                self.assertGreaterEqual(len(inventory_profiles), 3)
                self.assertGreaterEqual(
                    len({tuple(profile[1:]) for profile in inventory_profiles}), 2
                )
        for capability, (module_name, class_name, method_name) in REQUIRED_RC_TESTS.items():
            with self.subTest(capability=capability):
                source = PROJECT_ROOT.joinpath(*module_name.split(".")).with_suffix(".py")
                tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
                classes = {
                    node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
                }
                self.assertIn(class_name, classes)
                methods = {
                    node.name
                    for node in classes[class_name].body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                self.assertIn(method_name, methods)

    def test_migration_manifest_is_contiguous_and_canonical_files_are_unchanged(self):
        migrations = load_migrations()
        self.assertEqual(
            list(range(1, LATEST_MIGRATION_VERSION + 1)),
            [item.version for item in migrations],
        )
        self.assertEqual(self.fixture_hash, sha256_file(REFERENCE_FIXTURE))
        self.assertEqual(self.local_hash, sha256_file(LOCAL_DATABASE))


if __name__ == "__main__":
    unittest.main()
