import atexit
from concurrent.futures import ThreadPoolExecutor
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb003-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.historical_collection import HistoricalCollectionService  # noqa: E402
from services.history_cutover import (  # noqa: E402
    CANONICAL_UTC,
    HistoricalInventoryWriteService,
)
from services.trade_problems import (  # noqa: E402
    PartialReceiptInputDTO,
    TradeProblemCode,
    TradeProblemService,
    TradeProblemType,
)


class ExactlyOnceAlbumCompletionTestCase(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb003-")
        self.db_path = Path(self.temp_dir.name) / "completion.db"
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

    def completion(self, user_id=1, album_id="vfl"):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT h.* FROM historical_album_records h
                JOIN user_albums ua ON ua.id=h.user_album_id
                WHERE ua.user_id=? AND ua.album_id=?
                """,
                (user_id, album_id),
            ).fetchone()

    def completion_count(self, user_id=1, album_id="vfl"):
        return self.scalar(
            """
            SELECT COUNT(*) FROM historical_album_records h
            JOIN user_albums ua ON ua.id=h.user_album_id
            WHERE ua.user_id=? AND ua.album_id=? AND h.completed_at IS NOT NULL
            """,
            (user_id, album_id),
        )

    def seed_owned(self, user_id, codes, album_id="vfl", quantities=None):
        quantities = quantities or {}
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        user_id,
                        album_id,
                        str(code),
                        "duplicate" if quantities.get(str(code), 1) > 1 else "owned",
                        max(quantities.get(str(code), 1) - 1, 0),
                        quantities.get(str(code), 1),
                    )
                    for code in codes
                ],
            )

    def quantity(self, user_id, code, album_id="vfl"):
        return self.scalar(
            """
            SELECT COALESCE(MAX(quantity), 0) FROM stickers
            WHERE user_id=? AND album_id=? AND sticker_code=?
            """,
            (user_id, album_id, str(code)),
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

    def incoming_position(self, trade_request_id, user_id):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT p.* FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=?
                """,
                (trade_request_id, user_id),
            ).fetchone()

    def prepare_trade_that_completes_user_two(self):
        self.seed_owned(1, (1,), quantities={"1": 2})
        self.seed_owned(2, range(2, 251), quantities={"3": 2})
        trade_id = self.create_open_trade()
        self.login_as(2)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/accept").status_code)
        self.login_as(1)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/ship").status_code)
        return trade_id

    def test_last_sticker_retry_reduction_and_recompletion_keep_first_fact(self):
        self.seed_owned(1, range(1, 250))
        first_timestamp = "2026-08-16T12:00:00.000000Z"
        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            first = writer.add(
                1, "vfl", "250", event_key="manual:last:250",
                occurred_at=first_timestamp,
            )
            replay = writer.add(
                1, "vfl", "250", event_key="manual:last:250",
                occurred_at=first_timestamp,
            )
            connection.commit()
        self.assertEqual((0, 1), (first.previous_quantity, first.quantity))
        self.assertEqual((0, 1), (replay.previous_quantity, replay.quantity))
        completion = self.completion()
        self.assertEqual(first_timestamp, completion["completed_at"])
        self.assertRegex(completion["completed_at"], CANONICAL_UTC)
        self.assertEqual("album-completion:1", completion["completion_event_key"])
        self.assertEqual("inventory_transition", completion["completion_source_type"])
        self.assertEqual("manual:last:250", completion["completion_source_key"])

        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            writer.remove(1, "vfl", "250", event_key="manual:remove:250")
            connection.commit()
        self.assertEqual(0, self.quantity(1, 250))
        self.assertEqual(first_timestamp, self.completion()["completed_at"])

        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "250", event_key="manual:recomplete:250",
                occurred_at="2026-08-17T12:00:00.000000Z",
            )
            connection.commit()
        self.assertEqual(1, self.quantity(1, 250))
        self.assertEqual(1, self.completion_count())
        self.assertEqual(first_timestamp, self.completion()["completed_at"])
        self.assertEqual("manual:last:250", self.completion()["completion_source_key"])

    def test_pre_cutover_complete_duplicate_does_not_invent_completion(self):
        self.seed_owned(1, range(1, 251))
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "1", event_key="precutover:duplicate"
            )
            connection.commit()
        self.assertEqual(2, self.quantity(1, 1))
        self.assertEqual(0, self.completion_count())

    def test_reduction_does_not_create_completion(self):
        self.seed_owned(1, range(1, 251))
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).remove(
                1, "vfl", "250", event_key="precutover:reduction"
            )
            connection.commit()
        self.assertEqual(0, self.quantity(1, 250))
        self.assertEqual(0, self.completion_count())

    def test_pre_cutover_unstarted_album_can_complete_without_invented_start(self):
        self.seed_owned(1, range(1, 250))
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "250", event_key="precutover:last"
            )
            connection.commit()
        completion = self.completion()
        self.assertIsNone(completion["started_at"])
        self.assertIsNone(completion["start_event_key"])
        self.assertIsNotNone(completion["completed_at"])

    def test_single_add_route_completes_once(self):
        self.seed_owned(1, range(1, 250))
        response = self.client.post(
            "/add/vfl/250", data={"_history_mutation_id": "single-complete"}
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, self.completion_count())

    def test_inline_quantity_route_completes_once(self):
        self.seed_owned(1, range(1, 250))
        response = self.client.post(
            "/album/vfl/sticker/250/quantity",
            data={"delta": "1", "_history_mutation_id": "inline-complete"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, self.completion_count())

    def test_detail_set_route_completes_once(self):
        self.seed_owned(1, range(1, 250))
        response = self.client.post(
            "/sticker/vfl/250",
            data={"quantity": "1", "_history_mutation_id": "detail-complete"},
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, self.completion_count())

    def test_offline_trade_completes_once(self):
        self.seed_owned(1, range(1, 250), quantities={"1": 2})
        response = self.client.post(
            "/album/vfl/liste/trade",
            data={
                "give_codes": ["1"],
                "get_codes": ["250"],
                "_history_mutation_id": "offline-complete",
            },
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, self.completion_count())

    def test_batch_completes_once(self):
        self.seed_owned(1, range(1, 249))
        response = self.client.post(
            "/bulk_add/vfl",
            data={
                "codes": ["249", "250"],
                "_history_mutation_id": "batch-complete",
            },
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, self.completion_count())

    def test_undo_that_increases_inventory_completes_once(self):
        self.seed_owned(1, range(1, 251))
        self.client.post(
            "/remove/vfl/250",
            data={"_history_mutation_id": "undo-remove"},
        )
        response = self.client.post(
            "/undo", data={"_history_mutation_id": "undo-complete"}
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, self.completion_count())

    def test_lifecycle_receipt_completes_exactly_once(self):
        trade_id = self.prepare_trade_that_completes_user_two()
        self.login_as(2)
        first = self.client.post(f"/trade/{trade_id}/receive")
        second = self.client.post(f"/trade/{trade_id}/receive")
        self.assertEqual((302, 302), (first.status_code, second.status_code))
        self.assertEqual(1, self.quantity(2, 1))
        self.assertEqual(1, self.completion_count(2))
        self.assertIn(
            "trade-receipt:", self.completion(2)["completion_source_key"]
        )

    def test_problem_full_receipt_completes_once(self):
        trade_id = self.prepare_trade_that_completes_user_two()
        position = self.incoming_position(trade_id, 2)
        with self.connect() as connection:
            result = TradeProblemService(connection).report(
                trade_id,
                2,
                (PartialReceiptInputDTO(position["id"], 1, None),),
            )
        self.assertEqual(TradeProblemCode.FULLY_RECEIVED, result.code)
        self.assertEqual(1, self.completion_count(2))

    def test_partial_receipt_then_resolution_completes_once(self):
        trade_id = self.prepare_trade_that_completes_user_two()
        position = self.incoming_position(trade_id, 2)
        with self.connect() as connection:
            result = TradeProblemService(connection).report(
                trade_id,
                2,
                (
                    PartialReceiptInputDTO(
                        position["id"], 0, TradeProblemType.MISSING
                    ),
                ),
            )
        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, result.code)
        self.assertEqual(0, self.completion_count(2))
        with self.connect() as connection:
            result = TradeProblemService(connection).resolve(trade_id, 2)
        self.assertEqual(TradeProblemCode.PROBLEM_RESOLVED, result.code)
        self.assertEqual(1, self.completion_count(2))

    def test_completion_failure_rolls_back_inventory_mutation_and_history(self):
        self.seed_owned(1, range(1, 250))
        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            with patch(
                "services.history_cutover.FirstAlbumCompletionService."
                "evaluate_first_album_completion",
                side_effect=RuntimeError("forced completion failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced completion failure"):
                    writer.add(1, "vfl", "250", event_key="atomic:last")
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM stickers
                WHERE user_id=1 AND album_id='vfl' AND sticker_code='250'
                """
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM historical_inventory_mutations
                WHERE event_key='atomic:last'
                """
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM historical_album_records
                WHERE completed_at IS NOT NULL
                """
            ).fetchone()[0])

    def test_concurrent_completion_candidates_create_at_most_one_fact(self):
        self.seed_owned(1, range(1, 251))
        user_album_id = self.scalar(
            "SELECT id FROM user_albums WHERE user_id=1 AND album_id='vfl'"
        )

        def attempt(number):
            with self.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                result = HistoricalCollectionService(
                    connection
                ).record_first_album_completion(
                    user_album_id,
                    completed_at=f"2026-08-16T12:00:0{number}.000000Z",
                    event_key=f"concurrent:{number}",
                    source_type="inventory_transition",
                    source_key=f"mutation:{number}",
                )
                connection.commit()
                return result.created

        with ThreadPoolExecutor(max_workers=2) as executor:
            created = list(executor.map(attempt, (1, 2)))
        self.assertEqual(1, sum(created))
        self.assertEqual(1, self.completion_count())

    def test_gets_and_startup_do_not_backfill_pre_cutover_complete_album(self):
        self.seed_owned(1, range(1, 251))
        for path in (
            "/album/vfl",
            "/sammlung",
            "/profil/1",
            "/statistik",
            "/album/vfl/trophaeen",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertLess(response.status_code, 500)
                self.assertEqual(0, self.completion_count())

    def test_completion_has_no_cb005_cb007_or_notification_side_effect(self):
        self.seed_owned(1, range(1, 250))
        before = {
            table: self.scalar(f"SELECT COUNT(*) FROM {table}")
            for table in (
                "unlocked_trophies",
                "trophy_unlock_history_context",
                "feed_events",
                "notifications",
            )
        }
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "250", event_key="side-effects:last"
            )
            connection.commit()
        after = {
            table: self.scalar(f"SELECT COUNT(*) FROM {table}")
            for table in before
        }
        self.assertEqual(before, after)
        self.assertEqual(1, self.completion_count())


if __name__ == "__main__":
    unittest.main()
