import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s16-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import (  # noqa: E402
    current_version,
    migrate,
    rollback,
)
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_receipt import (  # noqa: E402
    TradeReceiptCode,
    TradeReceiptResultDTO,
    TradeReceiptService,
    receipt_status_for_trade,
)


class TradeReceiptTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.fixture_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.production_hash_before == sha256(PRODUCTION_DB)
        assert cls.fixture_hash_before == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s16-")
        self.test_db = Path(self.test_dir.name) / "receipt.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual(
                (1, 2, 3, 4), migrate(connection, target_version=4)
            )
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(2)

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.test_db, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def row(self, statement, parameters=()):
        with self.connection() as connection:
            return connection.execute(statement, parameters).fetchone()

    def count(self, table, where="1=1", parameters=()):
        return self.row(
            f"SELECT COUNT(*) AS count FROM {table} WHERE {where}", parameters
        )["count"]

    def create_open_trade(self):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open')
                """
            )
            return cursor.lastrowid

    def create_accepted_trade(self):
        trade_id = self.create_open_trade()
        self.login_as(2)
        response = self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(302, response.status_code)
        return trade_id

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/ship")

    def receive_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/receive")

    def receipt_status(self, trade_id):
        with self.connection() as connection:
            return receipt_status_for_trade(connection, trade_id)

    def inventory(self, user_id, code):
        row = self.row(
            """
            SELECT quantity, duplicates FROM stickers
            WHERE user_id=? AND album_id='vfl' AND sticker_code=?
            """,
            (user_id, code),
        )
        return tuple(row) if row else (0, 0)

    def album(self, user_id):
        with self.connection() as connection:
            return InventoryReadService(connection).album(user_id, "vfl")

    def lifecycle_state(self, trade_id):
        return self.row(
            "SELECT lifecycle_state FROM trades WHERE legacy_trade_request_id=?",
            (trade_id,),
        )["lifecycle_state"]

    def legacy_status(self, trade_id):
        return self.row(
            "SELECT status FROM trade_requests WHERE id=?", (trade_id,)
        )["status"]

    def test_partner_receives_requester_shipment(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        before = self.inventory(2, "1")
        response = self.receive_as(trade_id, 2)
        status = self.receipt_status(trade_id)

        self.assertEqual(302, response.status_code)
        self.assertEqual((before[0] + 1, before[1]), self.inventory(2, "1"))
        self.assertTrue(status.partner_received)
        self.assertFalse(status.requester_received)

    def test_requester_receives_partner_shipment(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 2)
        before = self.inventory(1, "3")
        self.receive_as(trade_id, 1)
        status = self.receipt_status(trade_id)

        self.assertEqual((before[0] + 1, max(before[0], 0)), self.inventory(1, "3"))
        self.assertTrue(status.requester_received)
        self.assertFalse(status.partner_received)

    def test_first_receipt_books_only_one_side_and_keeps_trade_open(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        requester_before = self.inventory(1, "3")
        self.receive_as(trade_id, 2)

        self.assertEqual("accepted", self.legacy_status(trade_id))
        self.assertEqual("partially_received", self.lifecycle_state(trade_id))
        self.assertEqual(requester_before, self.inventory(1, "3"))
        self.assertEqual((1, 0), self.inventory(2, "1"))

    def test_second_receipt_completes_trade_and_lifecycle(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 2)
        self.receive_as(trade_id, 1)

        status = self.receipt_status(trade_id)
        lifecycle = self.row(
            """
            SELECT lifecycle_state, completed_at FROM trades
            WHERE legacy_trade_request_id=?
            """,
            (trade_id,),
        )
        self.assertTrue(status.both_received)
        self.assertEqual("completed", self.legacy_status(trade_id))
        self.assertEqual("completed", lifecycle["lifecycle_state"])
        self.assertTrue(lifecycle["completed_at"])

    def test_incoming_transit_disappears_only_for_received_side(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.assertEqual(1, self.album(2).availability("1").incoming_transit)
        self.assertEqual(1, self.album(1).availability("3").incoming_transit)

        self.receive_as(trade_id, 2)

        self.assertEqual(0, self.album(2).availability("1").incoming_transit)
        self.assertEqual(1, self.album(1).availability("3").incoming_transit)

    def test_receipt_updates_physical_progress_and_available(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        before_album = self.album(2)
        before_progress = before_album.progress(webapp.all_codes("vfl"), 250)

        self.receive_as(trade_id, 2)

        after_album = self.album(2)
        after = after_album.availability("1")
        after_progress = after_album.progress(webapp.all_codes("vfl"), 250)
        self.assertEqual((1, 1, 0, 0), (
            after.physical, after.assigned, after.available, after.incoming_transit
        ))
        self.assertEqual(before_progress.collected + 1, after_progress.collected)
        self.assertGreaterEqual(after.available, 0)
        self.assertLessEqual(after.available, after.physical)
        self.assertTrue(after.balance_is_valid)

    def test_repeated_receipt_is_idempotent_without_double_booking(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            first = TradeReceiptService(connection).receive(trade_id, 2)
        inventory_after_first = self.inventory(2, "1")
        with self.connection() as connection:
            second = TradeReceiptService(connection).receive(trade_id, 2)

        self.assertEqual(TradeReceiptCode.RECEIVED, first.code)
        self.assertEqual(TradeReceiptCode.ALREADY_RECEIVED, second.code)
        self.assertIsInstance(second, TradeReceiptResultDTO)
        self.assertTrue(second.idempotent)
        self.assertEqual(first.received_at, second.received_at)
        self.assertEqual(inventory_after_first, self.inventory(2, "1"))
        self.assertEqual(
            1,
            self.count(
                "trade_events",
                "trade_id=? AND event_type='receipt_confirmed'",
                (first.lifecycle_trade_id,),
            ),
        )

    def test_legacy_completion_trophy_writer_stays_off_without_notifications(self):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code<>'1'"
            )
            for code in range(4, 85):
                connection.execute(
                    """
                    INSERT INTO stickers
                        (user_id, album_id, sticker_code, status, duplicates, quantity)
                    VALUES (1, 'vfl', ?, 'owned', 0, 1)
                    """,
                    (str(code),),
                )

        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 2)
        notifications_before = self.count("notifications")

        self.receive_as(trade_id, 1)
        notifications_after = self.count("notifications")
        trophy_after = self.count(
            "unlocked_trophies",
            "user_id=1 AND album_id='vfl' AND trophy_name='Kader & Staff'",
        )
        self.receive_as(trade_id, 1)

        self.assertEqual(notifications_before, notifications_after)
        self.assertEqual(notifications_after, self.count("notifications"))
        self.assertEqual(0, trophy_after)
        self.assertEqual(
            0,
            self.count(
                "unlocked_trophies",
                "user_id=1 AND album_id='vfl' AND trophy_name='Kader & Staff'",
            ),
        )

    def test_unrelated_user_cannot_confirm_receipt(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            result = TradeReceiptService(connection).receive(trade_id, 3)

        self.assertEqual(TradeReceiptCode.UNAUTHORIZED, result.code)
        self.assertFalse(self.receipt_status(trade_id).any_received)
        self.assertEqual((0, 0), self.inventory(2, "1"))

    def test_receipt_before_other_shipping_is_rejected_atomically(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 2)
        with self.connection() as connection:
            result = TradeReceiptService(connection).receive(trade_id, 2)

        self.assertEqual(TradeReceiptCode.NOT_SHIPPED, result.code)
        self.assertFalse(self.receipt_status(trade_id).any_received)
        self.assertEqual((0, 0), self.inventory(2, "1"))

    def test_invalid_lifecycle_is_rejected_atomically(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE trades SET lifecycle_state='accepted'
                WHERE legacy_trade_request_id=?
                """,
                (trade_id,),
            )
        with self.connection() as connection:
            result = TradeReceiptService(connection).receive(trade_id, 2)

        self.assertEqual(TradeReceiptCode.INVALID_TRADE_STATE, result.code)
        self.assertFalse(self.receipt_status(trade_id).any_received)
        self.assertEqual((0, 0), self.inventory(2, "1"))

    def test_receipt_then_remaining_shipping_preserves_partial_receipt_state(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.receive_as(trade_id, 2)
        self.assertEqual("partially_received", self.lifecycle_state(trade_id))

        self.ship_as(trade_id, 2)

        self.assertEqual("partially_received", self.lifecycle_state(trade_id))
        self.assertEqual("accepted", self.legacy_status(trade_id))

    def test_deal_view_offers_receipt_only_after_other_side_shipped(self):
        trade_id = self.create_accepted_trade()
        self.login_as(2)
        before = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertNotIn("Empfang bestätigen", before)

        self.ship_as(trade_id, 1)
        self.login_as(2)
        ready = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Empfang bestätigen", ready)
        self.receive_as(trade_id, 2)
        received = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Empfang bestätigt", received)

    def test_v0004_migration_forward_repeat_and_empty_backout(self):
        empty_path = Path(self.test_dir.name) / "empty.db"
        with self.connection(empty_path) as connection:
            self.assertEqual(
                (1, 2, 3, 4), migrate(connection, target_version=4)
            )
            self.assertEqual((), migrate(connection, target_version=4))
            self.assertEqual(4, current_version(connection))
            self.assertEqual((4,), rollback(connection, target_version=3))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertNotIn("trade_receipt_status", tables)
        self.assertIn("trade_shipping_status", tables)

    def test_v0004_initializes_existing_v0003_lifecycle_trade(self):
        migrated_path = Path(self.test_dir.name) / "existing-v0003.db"
        shutil.copy2(REFERENCE_FIXTURE, migrated_path)
        with self.connection(migrated_path) as connection:
            self.assertEqual(
                (1, 2, 3), migrate(connection, target_version=3)
            )
            lifecycle_trade_id = connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id,
                     partner_user_id, lifecycle_state)
                VALUES (1, 1, 2, 'shipped')
                """
            ).lastrowid
            connection.execute(
                """
                INSERT INTO trade_shipping_status
                    (trade_id, requester_shipped, requester_shipped_at,
                     partner_shipped, partner_shipped_at)
                VALUES (?, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
                """,
                (lifecycle_trade_id,),
            )

            self.assertEqual((4,), migrate(connection, target_version=4))
            receipt = connection.execute(
                "SELECT * FROM trade_receipt_status WHERE trade_id=?",
                (lifecycle_trade_id,),
            ).fetchone()

        self.assertEqual(0, receipt["requester_received"])
        self.assertEqual(0, receipt["partner_received"])
        self.assertIsNone(receipt["requester_received_at"])
        self.assertIsNone(receipt["partner_received_at"])

    def test_completed_legacy_trade_remains_readable_after_v0004(self):
        trade = self.row("SELECT * FROM trade_requests WHERE id=1")
        self.assertEqual("completed", trade["status"])
        self.assertEqual('["2"]', trade["give_codes"])
        self.assertEqual('["4"]', trade["get_codes"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(1, trade["to_confirmed"])
        self.assertIsNone(self.receipt_status(1))

    def test_canonical_databases_remain_unchanged(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
