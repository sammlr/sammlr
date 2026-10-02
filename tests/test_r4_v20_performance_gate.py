import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DB = ROOT / "App" / "Database" / "sammlr.db"
FIXTURE = ROOT / "App" / "Database" / "sammlr_reference_s00.db"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Scripts"))

from r4_v20_performance_gate import (  # noqa: E402
    DatasetScale, inspect_query_plans, prepare_database, sqlite_lock_probe,
)
from services.executable_trade_matches import ExecutableTradeMatchService  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_coverage import TradeCoverageService  # noqa: E402
from services.statistics_projection import StatisticsProjectionService  # noqa: E402
import sqlite3


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R4V20PerformanceGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="sammlr-r4-performance-", dir="/private/tmp"
        )
        self.database = Path(self.temp_dir.name) / "gate.db"
        self.result = prepare_database(
            self.database,
            DatasetScale(users=4, albums=2, stickers_per_album=10,
                         trades=20, notifications=40, friendships=4),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dataset_is_reproducible_current_and_isolated(self):
        self.assertEqual(20, self.result["schema_version"])
        self.assertEqual("ok", self.result["integrity"])
        self.assertEqual(0, self.result["foreign_key_violations"])
        self.assertEqual(80, self.result["counts"]["stickers"])
        self.assertEqual(20, self.result["counts"]["trade_requests"])
        self.assertEqual(40, self.result["counts"]["notifications"])
        self.assertTrue(str(self.database).startswith("/private/tmp/"))

    def test_query_plan_and_lock_evidence_are_machine_readable(self):
        plans = inspect_query_plans(self.database)
        self.assertEqual({
            "trade_user_status_time", "trade_user_lookup", "notification_unread",
            "notification_page_time", "notification_retention",
        }, set(plans))
        self.assertTrue(all(plans.values()))
        lock = sqlite_lock_probe(self.database)
        self.assertEqual("delete", lock["journal_mode"])
        self.assertTrue(lock["competing_write_locked"])
        self.assertTrue(lock["data_preserved"])

    def test_executable_matching_uses_bounded_batch_queries(self):
        statements = []
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            connection.set_trace_callback(statements.append)
            service = ExecutableTradeMatchService(
                TradeCoverageService(InventoryReadService(connection))
            )
            service.matches(
                1, "perf01", tuple(f"PERF {code:03d}" for code in range(1, 11)),
                (2, 3, 4),
            )
        selects = [statement for statement in statements
                   if statement.lstrip().upper().startswith(("SELECT", "PRAGMA"))]
        self.assertLess(len(selects), 40)

    def test_profile_batch_statistics_equal_canonical_single_album_results(self):
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            service = StatisticsProjectionService(connection)
            rows = service._memberships(1)
            expected = tuple(service._current_album(1, row) for row in rows)
            actual = service.current_albums_for_memberships(
                1, tuple(int(row["user_album_id"]) for row in rows)
            )
        self.assertEqual(expected, actual)

    def test_canonical_databases_remain_unchanged(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))

    def test_non_private_targets_fail_closed(self):
        with self.assertRaises(ValueError):
            prepare_database(Path("/sammlr-forbidden-performance.db"))

    def test_harness_routes_synthetic_catalogs_through_service_imports(self):
        source = (ROOT / "App" / "performance_wsgi.py").read_text(
            encoding="utf-8"
        )
        for module in (
            "album_completion", "statistics_projection", "trophy_unlocks"
        ):
            self.assertIn(
                f"{module}.all_codes = _performance_catalog_codes", source
            )
        self.assertIn('app.config["SESSION_COOKIE_SECURE"] = False', source)

    def test_profile_projections_use_existing_sqlite_read_serialization(self):
        source = (ROOT / "App" / "webapp.py").read_text(encoding="utf-8")
        self.assertIn(
            '@app.route("/profil")\n@serialized_sqlite_projection\ndef profil()',
            source,
        )
        self.assertIn(
            '@app.route("/profil/<username>")\n'
            '@serialized_sqlite_projection\ndef public_profile(username)',
            source,
        )


if __name__ == "__main__":
    unittest.main()
