from pathlib import Path
import hashlib
import shutil
import sqlite3
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FIXTURE = PROJECT_ROOT / "App" / "Database" / "sammlr_reference_s00.db"
REFERENCE_SQL = PROJECT_ROOT / "App" / "Database" / "sammlr_reference_s00.sql"
LOCAL_DB = PROJECT_ROOT / "App" / "Database" / "sammlr.db"

from App.Database.migration_runner import current_version, migrate, rollback  # noqa: E402
from App.services.historical_collection import (  # noqa: E402
    HistoricalCollectionError,
    HistoricalCollectionService,
    HistoricalWriteConflict,
    historical_collection_schema_available,
)


CORE_TABLES = (
    "users",
    "albums",
    "user_albums",
    "stickers",
    "trade_requests",
    "trades",
    "unlocked_trophies",
    "notifications",
)
HISTORICAL_TABLES = {
    "historical_album_records",
    "historical_sticker_acquisitions",
    "historical_album_progress_points",
    "feed_events",
    "trophy_unlock_history_context",
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rowcounts(connection):
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in CORE_TABLES
    }


class HistoricalCollectionContractTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb001-")
        self.db_path = Path(self.temp_dir.name) / "cb001.db"
        self.connections = []

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        for connection in self.connections:
            connection.close()
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        self.connections.append(connection)
        return connection

    def copy_fixture(self):
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)

    def migrate_fixture(self):
        self.copy_fixture()
        with self.connect() as connection:
            migrate(connection, 13)

    @staticmethod
    def first_album_context(connection):
        row = connection.execute(
            """
            SELECT id, user_id, album_id
            FROM user_albums
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise AssertionError("reference fixture needs one user album")
        return int(row[0]), int(row[1]), row[2]

    def test_fresh_project_database_runs_complete_migration_chain(self):
        with self.connect() as connection:
            connection.executescript(REFERENCE_SQL.read_text(encoding="utf-8"))
            self.assertEqual(tuple(range(1, 14)), migrate(connection, 13))
            self.assertEqual(13, current_version(connection))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertTrue(HISTORICAL_TABLES <= tables)
            self.assertEqual([("ok",)], connection.execute(
                "PRAGMA integrity_check"
            ).fetchall())
            self.assertEqual([], connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall())

    def test_upgrade_preserves_core_rows_repeat_up_and_backout(self):
        self.copy_fixture()
        with self.connect() as connection:
            migrate(connection, 12)
            before = rowcounts(connection)
            self.assertEqual((13,), migrate(connection, 13))
            self.assertEqual(before, rowcounts(connection))
            self.assertEqual((), migrate(connection, 13))
            self.assertEqual(before, rowcounts(connection))
            self.assertEqual((13,), rollback(connection, 12))
            self.assertEqual(before, rowcounts(connection))
            self.assertFalse(historical_collection_schema_available(connection))

    def test_schema_enforces_positive_counts_context_and_idempotency(self):
        self.migrate_fixture()
        with self.connect() as connection:
            user_album_id, user_id, album_id = self.first_album_context(connection)
            valid = (
                user_album_id, user_id, album_id, "2", 1, "inventory",
                "quantity-request:1", "2026-08-16T10:00:00Z",
            )
            connection.execute(
                """
                INSERT INTO historical_sticker_acquisitions
                    (user_album_id, user_id, album_id, sticker_code, quantity,
                     source_type, source_key, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                valid,
            )
            for invalid_quantity in (0, -1):
                with self.subTest(quantity=invalid_quantity), self.assertRaises(
                    sqlite3.IntegrityError
                ):
                    connection.execute(
                        """
                        INSERT INTO historical_sticker_acquisitions
                            (user_album_id, user_id, album_id, sticker_code,
                             quantity, source_type, source_key, occurred_at)
                        VALUES (?, ?, ?, '3', ?, 'inventory', ?, ?)
                        """,
                        (
                            user_album_id, user_id, album_id, invalid_quantity,
                            f"invalid:{invalid_quantity}",
                            "2026-08-16T10:01:00Z",
                        ),
                    )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO historical_sticker_acquisitions
                        (user_album_id, user_id, album_id, sticker_code, quantity,
                         source_type, source_key, occurred_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    valid,
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO historical_album_progress_points
                        (user_album_id, user_id, album_id, event_key, captured_at,
                         owned_count, total_count)
                    VALUES (999999, ?, ?, 'bad-fk', ?, 1, 10)
                    """,
                    (user_id, album_id, "2026-08-16T10:02:00Z"),
                )

    def test_completion_contract_is_once_and_survives_current_state_changes(self):
        self.migrate_fixture()
        with self.connect() as connection:
            context = self.first_album_context(connection)
            connection.execute(
                """
                INSERT INTO historical_album_records
                    (user_album_id, user_id, album_id, completed_at,
                     completion_event_key, completion_source_type,
                     completion_source_key)
                VALUES (?, ?, ?, ?, ?, 'inventory_transition', ?)
                """,
                (
                    *context,
                    "2026-08-16T11:00:00Z",
                    "album-completion:1",
                    "inventory-mutation:99",
                ),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO historical_album_records
                        (user_album_id, user_id, album_id, completed_at,
                         completion_event_key, completion_source_type,
                         completion_source_key)
                    VALUES (?, ?, ?, ?, ?, 'inventory_transition', ?)
                    """,
                    (
                        *context,
                        "2026-08-17T11:00:00Z",
                        "album-completion:2",
                        "inventory-mutation:100",
                    ),
                )
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (context[1], context[2]),
            )
            completed_at = connection.execute(
                """
                SELECT completed_at FROM historical_album_records
                WHERE user_album_id=?
                """,
                (context[0],),
            ).fetchone()[0]
            self.assertEqual("2026-08-16T11:00:00Z", completed_at)

    def test_optional_trophy_trigger_allows_null_without_changing_unlock(self):
        self.migrate_fixture()
        with self.connect() as connection:
            context = self.first_album_context(connection)
            trophy_id = connection.execute(
                """
                INSERT INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (?, ?, 'CB001 Test Trophy', '2026-08-16T12:00:00Z')
                """,
                (context[1], context[2]),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO trophy_unlock_history_context
                    (unlocked_trophy_id, user_album_id, user_id, album_id,
                     trigger_sticker_code, trigger_source_key)
                VALUES (?, ?, ?, ?, NULL, NULL)
                """,
                (trophy_id, *context),
            )
            trigger = connection.execute(
                """
                SELECT trigger_sticker_code, trigger_source_key
                FROM trophy_unlock_history_context
                WHERE unlocked_trophy_id=?
                """,
                (trophy_id,),
            ).fetchone()
            self.assertEqual((None, None), trigger)
            self.assertEqual(
                "CB001 Test Trophy",
                connection.execute(
                    "SELECT trophy_name FROM unlocked_trophies WHERE id=?",
                    (trophy_id,),
                ).fetchone()[0],
            )

    def test_service_writes_reads_and_deduplicates_each_supported_fact(self):
        self.migrate_fixture()
        with self.connect() as connection:
            context = self.first_album_context(connection)
            service = HistoricalCollectionService(connection)

            start = service.record_album_start(
                context[0],
                started_at="2026-08-16T13:00:00Z",
                event_key="album-start:1",
            )
            self.assertTrue(start.created)
            self.assertFalse(service.record_album_start(
                context[0],
                started_at="2026-08-16T13:00:00Z",
                event_key="album-start:1",
            ).created)
            self.assertEqual(
                "2026-08-16T13:00:00Z",
                service.album_history(context[0]).started_at,
            )
            with self.assertRaises(HistoricalWriteConflict):
                service.record_album_start(
                    context[0],
                    started_at="2026-08-17T13:00:00Z",
                    event_key="album-start:2",
                )

            acquisition = service.record_positive_acquisition(
                context[0],
                sticker_code="2",
                quantity=2,
                source_type="inventory",
                source_key="quantity-request:2",
                occurred_at="2026-08-16T13:01:00Z",
            )
            self.assertTrue(acquisition.created)
            self.assertFalse(service.record_positive_acquisition(
                context[0],
                sticker_code="2",
                quantity=2,
                source_type="inventory",
                source_key="quantity-request:2",
                occurred_at="2026-08-16T13:01:00Z",
            ).created)
            with self.assertRaises(HistoricalWriteConflict):
                service.record_positive_acquisition(
                    context[0],
                    sticker_code="2",
                    quantity=3,
                    source_type="inventory",
                    source_key="quantity-request:2",
                    occurred_at="2026-08-16T13:01:00Z",
                )
            with self.assertRaises(HistoricalCollectionError):
                service.record_positive_acquisition(
                    context[0],
                    sticker_code="2",
                    quantity=0,
                    source_type="inventory",
                    source_key="quantity-request:zero",
                    occurred_at="2026-08-16T13:01:00Z",
                )

            progress = service.record_progress_point(
                context[0],
                event_key="progress:1",
                captured_at="2026-08-16T13:02:00Z",
                owned_count=10,
                total_count=100,
            )
            self.assertTrue(progress.created)
            self.assertFalse(service.record_progress_point(
                context[0],
                event_key="progress:1",
                captured_at="2026-08-16T13:02:00Z",
                owned_count=10,
                total_count=100,
            ).created)

            feed = service.record_feed_event(
                event_key="feed:album-start:1",
                event_type="album_started",
                actor_user_id=context[1],
                user_album_id=context[0],
                target_type="album",
                target_key=context[2],
                occurred_at="2026-08-16T13:03:00Z",
            )
            self.assertTrue(feed.created)
            self.assertFalse(service.record_feed_event(
                event_key="feed:album-start:1",
                event_type="album_started",
                actor_user_id=context[1],
                user_album_id=context[0],
                target_type="album",
                target_key=context[2],
                occurred_at="2026-08-16T13:03:00Z",
            ).created)
            self.assertEqual("album_started", service.feed_event(
                "feed:album-start:1"
            ).event_type)

            self.assertEqual(1, len(service.acquisitions_for_album(context[0])))
            self.assertEqual(1, len(service.progress_for_album(context[0])))
            counts = {
                table: connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in (
                    "historical_album_records",
                    "historical_sticker_acquisitions",
                    "historical_album_progress_points",
                    "feed_events",
                )
            }
            self.assertEqual(
                {
                    "historical_album_records": 1,
                    "historical_sticker_acquisitions": 1,
                    "historical_album_progress_points": 1,
                    "feed_events": 1,
                },
                counts,
            )


if __name__ == "__main__":
    unittest.main()
