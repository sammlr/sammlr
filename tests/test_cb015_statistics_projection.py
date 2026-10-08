import atexit
from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb015-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.historical_collection import HistoricalCollectionService  # noqa: E402
from services.statistics_projection import StatisticsProjectionService  # noqa: E402
from trophy_definitions import canonical_album_trophy_definitions  # noqa: E402


class CB015StatisticsProjectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb015-")
        self.db_path = Path(self.temp_dir.name) / "statistics.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            for table in (
                "trade_ratings", "trade_receipt_report_positions",
                "trade_receipt_reports", "trade_receipt_status",
                "trade_shipping_status", "trade_reservations", "trade_events",
                "trade_positions", "trades", "trade_requests",
                "canonical_trophy_unlocks", "historical_sticker_acquisitions",
                "historical_album_progress_points", "historical_album_records",
                "feed_events", "notifications", "unlocked_trophies", "stickers",
                "user_albums",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.executemany(
                "INSERT INTO user_albums (user_id, album_id) VALUES (?, ?)",
                ((1, "vfl"), (1, "wm26"), (2, "vfl")),
            )
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def membership(self, connection, user_id=1, album_id="vfl"):
        return int(connection.execute(
            "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchone()[0])

    def set_inventory(self, quantities, album_id="vfl", user_id=1):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, 'owned', ?, ?)
                """,
                (
                    (user_id, album_id, code, max(quantity - 1, 0), quantity)
                    for code, quantity in quantities.items()
                ),
            )

    def add_history(self, *, quantity=3, completed=False, album_id="vfl"):
        with self.connection() as connection:
            membership = self.membership(connection, 1, album_id)
            service = HistoricalCollectionService(connection)
            service.record_album_start(
                membership,
                started_at="2026-08-01T10:00:00.000000Z",
                event_key=f"album-start:{membership}",
            )
            service.record_positive_acquisition(
                membership,
                sticker_code="1" if album_id == "vfl" else "FWC1",
                quantity=quantity,
                source_type="inventory",
                source_key=f"cb015:acquisition:{membership}",
                occurred_at="2026-08-02T10:00:00.000000Z",
            )
            if completed:
                service.record_first_album_completion(
                    membership,
                    completed_at="2026-08-11T10:00:00.000000Z",
                    event_key=f"album-completion:{membership}",
                    source_type="inventory_transition",
                    source_key=f"cb015:completion:{membership}",
                )
            return membership

    def projection(self):
        with self.connection() as connection:
            return StatisticsProjectionService(connection).for_user(1, 1)

    def test_current_album_metrics_follow_inventory_without_changing_career(self):
        self.add_history(quantity=4)
        self.set_inventory({"1": 2, "2": 1})
        first = self.projection()
        vfl = next(album for album in first.current_albums if album.album_id == "vfl")
        self.assertEqual((2, 3, 248, 1, 0), (
            vfl.collected, vfl.physical_quantity, vfl.missing,
            vfl.duplicate_quantity, vfl.percent,
        ))

        self.set_inventory({"1": 1})
        second = self.projection()
        updated = next(album for album in second.current_albums if album.album_id == "vfl")
        self.assertEqual((1, 249, 0), (
            updated.collected, updated.missing, updated.duplicate_quantity,
        ))
        self.assertEqual(4, second.career.recorded_acquisition_quantity)

    def test_recorded_acquisitions_are_non_decreasing_and_pre_cutover_unknown(self):
        self.add_history(quantity=7)
        self.set_inventory({"1": 7})
        before = self.projection().career.recorded_acquisition_quantity
        self.set_inventory({})
        after = self.projection().career.recorded_acquisition_quantity
        html = self.client.get("/statistik").get_data(as_text=True)
        self.assertEqual((7, 7), (before, after))
        self.assertIn("7 Stickerzugänge seit Historienstart erfasst", html)
        self.assertIn("Werte vor dem Historienstart sind unbekannt", html)
        self.assertNotIn("7 Sticker gesammelt", html)

    def test_completion_is_historical_and_current_full_album_is_not_completion(self):
        self.add_history(completed=True)
        self.set_inventory({"1": 1})
        self.assertEqual(1, self.projection().career.completed_album_count)
        self.set_inventory({})
        self.assertEqual(1, self.projection().career.completed_album_count)

        self.set_inventory({str(code): 1 for code in range(1, 251)}, "vfl")
        with self.connection() as connection:
            connection.execute("DELETE FROM historical_album_records")
        projection = self.projection()
        self.assertEqual(0, projection.career.completed_album_count)
        self.assertEqual(100, next(
            album.percent for album in projection.current_albums
            if album.album_id == "vfl"
        ))

    def test_album_history_exposes_first_completion_duration_and_stays_stable(self):
        self.add_history(quantity=2, completed=True)
        with self.connection() as connection:
            first = StatisticsProjectionService(connection).for_album(1, "vfl")
        self.set_inventory({})
        with self.connection() as connection:
            second = StatisticsProjectionService(connection).for_album(1, "vfl")
        self.assertEqual(10, first.career.first_completion_duration_days)
        self.assertEqual(first.career.completed_at, second.career.completed_at)
        html = self.client.get("/album/vfl/statistik").get_data(as_text=True)
        self.assertIn("Karriere in diesem Album", html)
        self.assertIn("Dauer bis zum ersten Abschluss: 10 Tage", html)

    def test_trade_career_uses_directed_cb010_aggregates_and_distinct_partners(self):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1", "2", "3"]', '["4"]', 'completed')
                """
            )
        career = self.projection().career
        self.assertEqual((1, 3, 1, 1), (
            career.successful_trades.successful_trade_count,
            career.successful_trades.given_quantity_total,
            career.successful_trades.received_quantity_total,
            career.successful_trades.distinct_partner_count,
        ))
        html = self.client.get("/statistik").get_data(as_text=True)
        self.assertIn("3 Sticker abgegeben", html)
        self.assertIn("1 Sticker erhalten", html)
        self.assertNotIn("4 Sticker getauscht", html)
        self.assertIn("Größter Trade: 1 erhalten · 3 abgegeben", html)

    def test_only_valid_persistent_trophies_count(self):
        with self.connection() as connection:
            membership = self.membership(connection)
            valid = canonical_album_trophy_definitions("vfl", 250)[0]
            for definition_id in (valid["id"], "not-approved.v1"):
                connection.execute(
                    """
                    INSERT INTO canonical_trophy_unlocks
                        (event_key, trophy_definition_id, user_album_id, user_id,
                         album_id, trophy_name, unlocked_at, source_type, source_key)
                    VALUES (?, ?, ?, 1, 'vfl', ?,
                            '2026-08-10T10:00:00.000000Z',
                            'inventory_transition', ?)
                    """,
                    (f"trophy:{definition_id}", definition_id, membership,
                     definition_id, f"source:{definition_id}"),
                )
            connection.execute(
                "INSERT INTO unlocked_trophies "
                "(user_id, album_id, trophy_name, unlocked_at) "
                "VALUES (1, 'vfl', 'Legacy', CURRENT_TIMESTAMP)"
            )
        self.assertEqual(1, self.projection().career.valid_trophy_count)

    def test_global_current_missing_and_duplicates_are_only_album_scoped(self):
        self.set_inventory({"1": 2})
        html = self.client.get("/statistik").get_data(as_text=True)
        career = html[html.index("<h2>Karriere</h2>"):]
        self.assertNotIn("Sticker fehlen", career)
        self.assertNotIn("Sticker doppelt", career)
        self.assertNotIn("Nächst", html)
        self.assertIn("249 fehlen · 1 doppelt", html)

    def test_statistics_are_owner_only_and_album_membership_fails_closed(self):
        with self.connection() as connection:
            service = StatisticsProjectionService(connection)
            self.assertIsNone(service.for_user(1, 2))
            self.assertIsNone(service.for_album(1, "vfl", 2))
            self.assertIsNone(service.for_album(1, "em24", 1))
        self.assertEqual(404, self.client.get("/album/em24/statistik").status_code)

    def test_profile_and_statistics_share_successful_trade_definition(self):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1"]', '["2"]', 'completed')
                """
            )
            statistics = StatisticsProjectionService(connection).for_user(1)
            profile = CollectorProfileService(connection).by_user_id(1, 1)
        self.assertEqual(
            statistics.career.successful_trades.successful_trade_count,
            profile.successful_trade_count,
        )

    def test_projection_is_deterministic_immutable_read_only_and_has_no_migration(self):
        self.add_history(quantity=1, completed=True)
        before_hash = sha256(self.db_path)
        first = self.projection()
        second = self.projection()
        self.assertEqual(first, second)
        self.assertEqual(before_hash, sha256(self.db_path))
        with self.assertRaises(FrozenInstanceError):
            first.career.completed_album_count = 99
        self.assertEqual(27, max(migration.version for migration in load_migrations()))

    def test_projection_query_count_is_bounded_for_closed_beta_album_set(self):
        with self.connection() as connection:
            reads = []
            connection.set_trace_callback(
                lambda statement: reads.append(statement)
                if statement.lstrip().lower().startswith("select") else None
            )
            projection = StatisticsProjectionService(connection).for_user(1)
            connection.set_trace_callback(None)
        self.assertEqual(2, len(projection.current_albums))
        self.assertLessEqual(len(reads), 40, "\n".join(reads))

    def test_legacy_schema_marks_history_unavailable_instead_of_reconstructing(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        shutil.copy2(FIXTURE, legacy_path)
        connection = sqlite3.connect(legacy_path)
        connection.row_factory = sqlite3.Row
        try:
            projection = StatisticsProjectionService(connection).for_user(1)
        finally:
            connection.close()
        self.assertFalse(projection.career.history_available)
        self.assertIsNone(projection.career.recorded_acquisition_quantity)
        self.assertIsNone(projection.career.completed_album_count)


if __name__ == "__main__":
    unittest.main()
