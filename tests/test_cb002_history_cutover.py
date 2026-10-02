import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb002-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate, rollback  # noqa: E402
from services.history_cutover import (  # noqa: E402
    CANONICAL_UTC,
    HistoricalInventoryWriteService,
    canonical_utc_timestamp,
)


class HistoryCutoverTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb002-")
        self.db_path = Path(self.temp_dir.name) / "cutover.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with self.connect() as connection:
            migrate(connection, 14)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id

    def scalar(self, statement, parameters=()):
        with self.connect() as connection:
            return connection.execute(statement, parameters).fetchone()[0]

    def quantity(self, user_id, code, album_id="vfl"):
        return self.scalar(
            """
            SELECT COALESCE(MAX(quantity), 0) FROM stickers
            WHERE user_id=? AND album_id=? AND sticker_code=?
            """,
            (user_id, album_id, code),
        )

    def create_open_trade(self):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open')
                """
            )
            return int(cursor.lastrowid)

    def test_v0014_upgrade_repeat_down_and_no_backfill(self):
        isolated = Path(self.temp_dir.name) / "v13.db"
        shutil.copy2(REFERENCE_FIXTURE, isolated)
        connection = sqlite3.connect(isolated)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            migrate(connection, 13)
            before = {
                table: connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in ("users", "user_albums", "stickers", "trades")
            }
            self.assertEqual((14,), migrate(connection, 14))
            self.assertEqual((), migrate(connection, 14))
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM historical_inventory_mutations"
            ).fetchone()[0])
            after = {
                table: connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in before
            }
            self.assertEqual(before, after)
            self.assertEqual([("ok",)], [
                tuple(row) for row in connection.execute(
                    "PRAGMA integrity_check"
                ).fetchall()
            ])
            self.assertEqual([], connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall())
            self.assertEqual((14,), rollback(connection, 13))
            self.assertEqual(13, current_version(connection))
        finally:
            connection.close()

    def test_album_start_only_for_new_cutover_membership_and_retry(self):
        self.assertEqual(0, self.scalar(
            "SELECT COUNT(*) FROM historical_album_records WHERE user_id=1"
        ))
        self.client.post(
            "/add/vfl/2", data={"_history_mutation_id": "pre-cutover-write"}
        )
        self.assertEqual(0, self.scalar(
            "SELECT COUNT(*) FROM historical_album_records WHERE user_id=1"
        ))

        self.login_as(2)
        first = self.client.post("/alben/hinzufuegen/wm26")
        second = self.client.post("/alben/hinzufuegen/wm26")
        self.assertEqual((302, 302), (first.status_code, second.status_code))
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT h.started_at, h.start_event_key
                FROM historical_album_records h
                JOIN user_albums ua ON ua.id=h.user_album_id
                WHERE ua.user_id=2 AND ua.album_id='wm26'
                """
            ).fetchall()
        self.assertEqual(1, len(rows))
        self.assertRegex(rows[0]["started_at"], CANONICAL_UTC)
        self.assertTrue(rows[0]["start_event_key"].startswith("album-start:"))

    def test_manual_positive_set_negative_and_retry_contract(self):
        with self.connect() as connection:
            service = HistoricalInventoryWriteService(connection)
            plus_one = service.set_quantity(
                1, "vfl", "2", 2, event_key="manual:set:one"
            )
            replay = service.set_quantity(
                1, "vfl", "2", 2, event_key="manual:set:one"
            )
            connection.commit()
            self.assertEqual((1, 2), (
                plus_one.previous_quantity, plus_one.quantity
            ))
            self.assertEqual((1, 2), (
                replay.previous_quantity, replay.quantity
            ))
        self.assertEqual(2, self.quantity(1, "2"))
        self.assertEqual(1, self.scalar(
            "SELECT SUM(quantity) FROM historical_sticker_acquisitions"
        ))

        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).set_quantity(
                1, "vfl", "1", 2, event_key="manual:set:negative"
            )
            connection.commit()
        self.assertEqual(2, self.quantity(1, "1"))
        self.assertEqual(1, self.scalar(
            "SELECT SUM(quantity) FROM historical_sticker_acquisitions"
        ))

    def test_batch_and_unequal_offline_trade_are_idempotent(self):
        batch = {
            "codes": ["2", "3"],
            "_history_mutation_id": "batch-once",
        }
        self.client.post("/bulk_add/vfl", data=batch)
        self.client.post("/bulk_add/vfl", data=batch)
        self.assertEqual((2, 1), (self.quantity(1, "2"), self.quantity(1, "3")))

        transfer = {
            "give_codes": ["1"],
            "get_codes": ["3", "3"],
            "_history_mutation_id": "paper-once",
        }
        before_give = self.quantity(1, "1")
        self.client.post("/album/vfl/liste/trade", data=transfer)
        self.client.post("/album/vfl/liste/trade", data=transfer)
        self.assertEqual(before_give - 1, self.quantity(1, "1"))
        self.assertEqual(3, self.quantity(1, "3"))
        self.assertEqual(4, self.scalar(
            "SELECT SUM(quantity) FROM historical_sticker_acquisitions"
        ))
        self.assertEqual(2, self.scalar(
            """
            SELECT SUM(quantity) FROM historical_sticker_acquisitions
            WHERE source_type='paper_trade'
            """
        ))

    def test_progress_is_sparse_and_uses_album_total_and_utc(self):
        with self.connect() as connection:
            service = HistoricalInventoryWriteService(connection)
            service.add(1, "vfl", "1", event_key="progress:duplicate")
            service.add(1, "vfl", "3", event_key="progress:first")
            service.add(1, "vfl", "3", event_key="progress:more")
            service.set_quantity(1, "vfl", "3", 0, event_key="progress:remove")
            connection.commit()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT captured_at, owned_count, total_count
                FROM historical_album_progress_points
                ORDER BY id
                """
            ).fetchall()
        self.assertEqual(2, len(rows))
        self.assertEqual([250, 250], [row["total_count"] for row in rows])
        self.assertGreater(rows[0]["owned_count"], rows[1]["owned_count"])
        self.assertTrue(all(CANONICAL_UTC.fullmatch(row["captured_at"]) for row in rows))
        self.assertRegex(canonical_utc_timestamp(), CANONICAL_UTC)

    def test_lifecycle_receipt_histories_incoming_only_and_retries_once(self):
        trade_id = self.create_open_trade()
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/accept")
        self.login_as(1)
        self.client.post(f"/trade/{trade_id}/ship")
        shipping_acquisitions = self.scalar(
            "SELECT COUNT(*) FROM historical_sticker_acquisitions"
        )
        self.assertEqual(0, shipping_acquisitions)

        before = self.quantity(2, "1")
        self.login_as(2)
        first = self.client.post(f"/trade/{trade_id}/receive")
        second = self.client.post(f"/trade/{trade_id}/receive")
        self.assertEqual((302, 302), (first.status_code, second.status_code))
        self.assertEqual(before + 1, self.quantity(2, "1"))
        self.assertEqual(1, self.scalar(
            """
            SELECT COUNT(*) FROM historical_sticker_acquisitions
            WHERE source_type='trade_receipt'
            """
        ))

    def test_history_failure_rolls_back_inventory_and_cutover_receipt(self):
        before = self.quantity(1, "2")
        with self.connect() as connection:
            service = HistoricalInventoryWriteService(connection)
            with patch(
                "services.history_cutover.HistoricalCollectionService."
                "record_positive_acquisition",
                side_effect=RuntimeError("forced history failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced history failure"):
                    service.add(
                        1, "vfl", "2", event_key="atomic:must-rollback"
                    )
            self.assertEqual(before, connection.execute(
                """
                SELECT quantity FROM stickers
                WHERE user_id=1 AND album_id='vfl' AND sticker_code='2'
                """
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM historical_inventory_mutations
                WHERE event_key='atomic:must-rollback'
                """
            ).fetchone()[0])

    def test_feed_completion_and_trophy_cutovers_are_not_started(self):
        self.client.post(
            "/add/vfl/3", data={"_history_mutation_id": "no-feed-event"}
        )
        with self.connect() as connection:
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM feed_events"
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM trophy_unlock_history_context"
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM historical_album_records
                WHERE completed_at IS NOT NULL
                """
            ).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
