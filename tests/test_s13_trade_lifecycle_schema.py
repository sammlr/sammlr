import hashlib
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FIXTURE = PROJECT_ROOT / "App" / "Database" / "sammlr_reference_s00.db"
PRODUCTION_DB = PROJECT_ROOT / "App" / "Database" / "sammlr.db"

from App.Database.migration_runner import (  # noqa: E402
    current_version,
    migrate,
    rollback,
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema(connection):
    return tuple(
        connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()
    )


class TradeLifecycleMigrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.fixture_hash_before = sha256(REFERENCE_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.production_hash_before == sha256(PRODUCTION_DB)
        assert cls.fixture_hash_before == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s13-")
        self.test_path = Path(self.test_dir.name) / "migration.db"

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.test_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def copy_fixture(self):
        shutil.copy2(REFERENCE_FIXTURE, self.test_path)

    def test_empty_database_migrates_forward(self):
        with self.connect() as connection:
            self.assertEqual((1,), migrate(connection, target_version=1))
            self.assertEqual(1, current_version(connection))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertTrue(
            {"schema_migrations", "trades", "trade_positions", "trade_events"}
            <= tables
        )

    def test_fixture_migration_preserves_completed_trade_and_json_packages(self):
        self.copy_fixture()
        with self.connect() as connection:
            before = connection.execute(
                "SELECT * FROM trade_requests WHERE id=1"
            ).fetchone()
            migrate(connection, target_version=1)
            after = connection.execute(
                "SELECT * FROM trade_requests WHERE id=1"
            ).fetchone()
            lifecycle_rows = connection.execute(
                "SELECT COUNT(*) FROM trades"
            ).fetchone()[0]
        self.assertEqual(before, after)
        self.assertEqual("completed", after[6])
        self.assertEqual('["2"]', after[4])
        self.assertEqual('["4"]', after[5])
        self.assertEqual(0, lifecycle_rows)

    def test_migration_is_idempotent(self):
        self.copy_fixture()
        with self.connect() as connection:
            self.assertEqual((1,), migrate(connection, target_version=1))
            schema_after_first_run = schema(connection)
            self.assertEqual((), migrate(connection, target_version=1))
            self.assertEqual(schema_after_first_run, schema(connection))
            count = connection.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
        self.assertEqual(1, count)

    def test_backout_restores_fixture_schema_and_data(self):
        self.copy_fixture()
        with self.connect() as connection:
            schema_before = schema(connection)
            trade_before = connection.execute(
                "SELECT * FROM trade_requests WHERE id=1"
            ).fetchone()
            migrate(connection, target_version=1)
            self.assertEqual((1,), rollback(connection))
            self.assertEqual(0, current_version(connection))
            self.assertEqual(schema_before, schema(connection))
            self.assertEqual(
                trade_before,
                connection.execute(
                    "SELECT * FROM trade_requests WHERE id=1"
                ).fetchone(),
            )

    def test_backout_restores_an_empty_database(self):
        with self.connect() as connection:
            self.assertEqual((), schema(connection))
            migrate(connection, target_version=1)
            rollback(connection)
            self.assertEqual((), schema(connection))

    def test_forward_backout_forward_is_reproducible(self):
        self.copy_fixture()
        with self.connect() as connection:
            migrate(connection, target_version=1)
            first_schema = schema(connection)
            rollback(connection)
            self.assertEqual((1,), migrate(connection, target_version=1))
            self.assertEqual(first_schema, schema(connection))

    def test_lifecycle_foundation_has_positions_events_and_timestamps(self):
        with self.connect() as connection:
            migrate(connection, target_version=1)
            trades = {row[1] for row in connection.execute("PRAGMA table_info(trades)")}
            positions = {
                row[1] for row in connection.execute("PRAGMA table_info(trade_positions)")
            }
            events = {
                row[1] for row in connection.execute("PRAGMA table_info(trade_events)")
            }
        self.assertTrue(
            {"legacy_trade_request_id", "lifecycle_state", "created_at", "updated_at", "completed_at"}
            <= trades
        )
        self.assertTrue(
            {"trade_id", "from_user_id", "to_user_id", "album_id", "sticker_code", "quantity", "created_at"}
            <= positions
        )
        self.assertTrue(
            {"trade_id", "event_type", "actor_user_id", "payload_json", "occurred_at"}
            <= events
        )

    def test_position_constraints_form_reservation_basis_without_reservations(self):
        with self.connect() as connection:
            migrate(connection, target_version=1)
            trade_id = connection.execute(
                """
                INSERT INTO trades
                    (requester_user_id, partner_user_id, lifecycle_state)
                VALUES (1, 2, 'accepted')
                """
            ).lastrowid
            connection.execute(
                """
                INSERT INTO trade_positions
                    (trade_id, from_user_id, to_user_id, album_id, sticker_code, quantity)
                VALUES (?, 1, 2, 'vfl', '2', 1)
                """,
                (trade_id,),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO trade_positions
                        (trade_id, from_user_id, to_user_id, album_id, sticker_code, quantity)
                    VALUES (?, 1, 2, 'vfl', '3', 0)
                    """,
                    (trade_id,),
                )
            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertNotIn("reservations", table_names)
        self.assertNotIn("inventory_reservations", table_names)

    def test_legacy_user_version_is_not_repurposed(self):
        self.copy_fixture()
        with self.connect() as connection:
            before = connection.execute("PRAGMA user_version").fetchone()[0]
            migrate(connection, target_version=1)
            after = connection.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(1, before)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
