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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s15-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate, rollback  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_shipping import (  # noqa: E402
    TradeShippingCode,
    TradeShippingResultDTO,
    TradeShippingService,
    shipping_status_for_trade,
)


class TradeShippingTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s15-")
        self.test_db = Path(self.test_dir.name) / "shipping.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3), migrate(connection, target_version=3))
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

    def shipping_status(self, trade_id):
        with self.connection() as connection:
            return shipping_status_for_trade(connection, trade_id)

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/ship")

    def inventory(self, user_id, code):
        row = self.row(
            """
            SELECT quantity, duplicates FROM stickers
            WHERE user_id=? AND album_id='vfl' AND sticker_code=?
            """,
            (user_id, code),
        )
        return tuple(row) if row else None

    def availability(self, user_id, code):
        with self.connection() as connection:
            return InventoryReadService(connection).album(
                user_id, "vfl"
            ).availability(code)

    def test_accepted_trade_starts_with_neither_side_shipped(self):
        trade_id = self.create_accepted_trade()
        status = self.shipping_status(trade_id)
        self.assertFalse(status.requester_shipped)
        self.assertFalse(status.partner_shipped)
        self.assertIsNone(status.requester_shipped_at)
        self.assertIsNone(status.partner_shipped_at)

    def test_requester_ships_only_own_outgoing_positions(self):
        trade_id = self.create_accepted_trade()
        response = self.ship_as(trade_id, 1)
        status = self.shipping_status(trade_id)

        self.assertEqual(302, response.status_code)
        self.assertTrue(status.requester_shipped)
        self.assertFalse(status.partner_shipped)
        self.assertEqual((2, 1), self.inventory(1, "1"))
        self.assertEqual((2, 1), self.inventory(2, "3"))

    def test_partner_ships_only_own_outgoing_positions(self):
        trade_id = self.create_accepted_trade()
        response = self.ship_as(trade_id, 2)
        status = self.shipping_status(trade_id)

        self.assertEqual(302, response.status_code)
        self.assertFalse(status.requester_shipped)
        self.assertTrue(status.partner_shipped)
        self.assertEqual((3, 2), self.inventory(1, "1"))
        self.assertEqual((1, 0), self.inventory(2, "3"))

    def test_both_sides_ship_independently_without_completing_trade(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        halfway = self.shipping_status(trade_id)
        self.assertTrue(halfway.requester_shipped)
        self.assertFalse(halfway.partner_shipped)

        self.ship_as(trade_id, 2)
        complete_shipping = self.shipping_status(trade_id)
        legacy = self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))
        lifecycle = self.row(
            "SELECT lifecycle_state FROM trades WHERE legacy_trade_request_id=?",
            (trade_id,),
        )
        self.assertTrue(complete_shipping.both_shipped)
        self.assertEqual("accepted", legacy["status"])
        self.assertEqual("shipped", lifecycle["lifecycle_state"])

    def test_requester_cannot_confirm_partner_shipping(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 1)
        status = self.shipping_status(trade_id)
        self.assertTrue(status.requester_shipped)
        self.assertFalse(status.partner_shipped)
        self.assertIsNone(status.partner_shipped_at)

    def test_unrelated_user_cannot_confirm_shipping(self):
        trade_id = self.create_accepted_trade()
        with self.connection() as connection:
            result = TradeShippingService(connection).ship(trade_id, 3)
        self.assertEqual(TradeShippingCode.UNAUTHORIZED, result.code)
        self.assertFalse(self.shipping_status(trade_id).any_shipped)
        self.assertEqual((3, 2), self.inventory(1, "1"))
        self.assertEqual((2, 1), self.inventory(2, "3"))

    def test_open_trade_cannot_be_shipped(self):
        trade_id = self.create_open_trade()
        with self.connection() as connection:
            result = TradeShippingService(connection).ship(trade_id, 1)
        self.assertEqual(TradeShippingCode.INVALID_TRADE_STATE, result.code)
        self.assertIsNone(self.shipping_status(trade_id))

    def test_missing_active_reservation_blocks_shipping_atomically(self):
        trade_id = self.create_accepted_trade()
        with self.connection() as connection:
            connection.execute(
                """
                DELETE FROM trade_reservations
                WHERE user_id=1 AND trade_id=(
                    SELECT id FROM trades WHERE legacy_trade_request_id=?
                )
                """,
                (trade_id,),
            )
        with self.connection() as connection:
            result = TradeShippingService(connection).ship(trade_id, 1)
        self.assertEqual(TradeShippingCode.MISSING_RESERVATIONS, result.code)
        self.assertFalse(self.shipping_status(trade_id).requester_shipped)
        self.assertEqual((3, 2), self.inventory(1, "1"))

    def test_repeated_shipping_is_idempotent(self):
        trade_id = self.create_accepted_trade()
        with self.connection() as connection:
            first = TradeShippingService(connection).ship(trade_id, 1)
        inventory_after_first = self.inventory(1, "1")
        with self.connection() as connection:
            second = TradeShippingService(connection).ship(trade_id, 1)

        self.assertEqual(TradeShippingCode.SHIPPED, first.code)
        self.assertEqual(TradeShippingCode.ALREADY_SHIPPED, second.code)
        self.assertTrue(second.idempotent)
        self.assertEqual(inventory_after_first, self.inventory(1, "1"))
        self.assertEqual(first.shipped_at, second.shipped_at)

    def test_shipping_timestamp_is_stored_exactly_once_per_side(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        first = self.shipping_status(trade_id)
        self.ship_as(trade_id, 1)
        repeated = self.shipping_status(trade_id)
        self.ship_as(trade_id, 2)
        both = self.shipping_status(trade_id)

        self.assertTrue(first.requester_shipped_at)
        self.assertEqual(first.requester_shipped_at, repeated.requester_shipped_at)
        self.assertEqual(first.requester_shipped_at, both.requester_shipped_at)
        self.assertTrue(both.partner_shipped_at)

    def test_incoming_transit_rises_only_for_receiver(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)

        receiver = self.availability(2, "1")
        sender = self.availability(1, "1")
        unrelated = self.availability(3, "1")
        self.assertEqual(1, receiver.incoming_transit)
        self.assertEqual(0, sender.incoming_transit)
        self.assertEqual(0, unrelated.incoming_transit)

    def test_incoming_transit_is_not_physical_assigned_available_or_progress(self):
        trade_id = self.create_accepted_trade()
        with self.connection() as connection:
            before_album = InventoryReadService(connection).album(2, "vfl")
            before_progress = before_album.progress(webapp.all_codes("vfl"), 250)
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            after_album = InventoryReadService(connection).album(2, "vfl")
            after_progress = after_album.progress(webapp.all_codes("vfl"), 250)
            transit = after_album.availability("1")

        self.assertEqual((0, 0, 0, 1), (
            transit.physical,
            transit.assigned,
            transit.available,
            transit.incoming_transit,
        ))
        self.assertEqual(before_progress.collected, after_progress.collected)
        self.assertEqual(before_progress.percent, after_progress.percent)

    def test_sender_available_stays_correct_and_nonnegative_after_shipping(self):
        trade_id = self.create_accepted_trade()
        before = self.availability(1, "1")
        self.ship_as(trade_id, 1)
        after = self.availability(1, "1")

        self.assertEqual((3, 1, 1, 1), (
            before.physical, before.assigned, before.reserved, before.available
        ))
        self.assertEqual((2, 1, 0, 1), (
            after.physical, after.assigned, after.reserved, after.available
        ))
        self.assertGreaterEqual(after.available, 0)
        self.assertTrue(after.balance_is_valid)

    def test_transit_is_not_double_counted_on_repeated_shipping(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        first = self.availability(2, "1").incoming_transit
        self.ship_as(trade_id, 1)
        second = self.availability(2, "1").incoming_transit
        self.assertEqual((1, 1), (first, second))

    def test_reservations_remain_traceable_after_one_side_ships(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT r.user_id, r.state, r.release_reason,
                       r.created_at, r.released_at
                FROM trade_reservations r
                JOIN trades t ON t.id=r.trade_id
                WHERE t.legacy_trade_request_id=?
                ORDER BY r.user_id
                """,
                (trade_id,),
            ).fetchall()
        self.assertEqual(
            [(1, "released", "shipped"), (2, "active", None)],
            [(row["user_id"], row["state"], row["release_reason"]) for row in rows],
        )
        self.assertTrue(rows[0]["created_at"])
        self.assertTrue(rows[0]["released_at"])

    def test_deal_view_shows_simple_side_specific_shipping_status(self):
        trade_id = self.create_accepted_trade()
        self.login_as(1)
        pending = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Eigener Versand noch offen", pending)
        self.assertIn("Gegenseite hat noch nicht versendet", pending)
        self.assertIn("Eigenen Versand bestätigen", pending)

        self.ship_as(trade_id, 2)
        self.login_as(1)
        incoming = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Gegenseite hat versendet", incoming)
        self.assertIn("Erwartete Sticker sind unterwegs", incoming)
        self.assertNotIn("Tracking", incoming)

    def test_legacy_completion_cannot_double_book_s15_shipping(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        after_shipping = self.inventory(1, "1")
        self.login_as(1)
        response = self.client.post(f"/trade/{trade_id}/confirm")

        self.assertEqual(302, response.status_code)
        self.assertEqual(after_shipping, self.inventory(1, "1"))
        self.assertEqual(
            "accepted",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )

    def test_shipped_trade_cannot_enter_legacy_failure_without_resolution(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        after_shipping = self.inventory(1, "1")
        self.login_as(2)
        response = self.client.post(f"/trade/{trade_id}/fail")

        self.assertEqual(302, response.status_code)
        self.assertEqual("accepted", self.row(
            "SELECT status FROM trade_requests WHERE id=?", (trade_id,)
        )["status"])
        self.assertEqual(after_shipping, self.inventory(1, "1"))
        self.assertTrue(self.shipping_status(trade_id).requester_shipped)

    def test_shipping_does_not_create_notifications_or_trophies(self):
        trade_id = self.create_accepted_trade()
        notifications_before = self.count("notifications")
        trophies_before = self.count("unlocked_trophies")
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)

        self.assertEqual(notifications_before, self.count("notifications"))
        self.assertEqual(trophies_before, self.count("unlocked_trophies"))

    def test_all_shipping_result_codes_are_stable_ui_neutral_strings(self):
        self.assertEqual(
            {
                "SHIPPED",
                "ALREADY_SHIPPED",
                "INVALID_TRADE_STATE",
                "UNAUTHORIZED",
                "MISSING_RESERVATIONS",
                "TRANSACTION_ERROR",
            },
            {code.value for code in TradeShippingCode},
        )
        self.assertTrue(issubclass(TradeShippingCode, str))
        trade_id = self.create_accepted_trade()
        with self.connection() as connection:
            result = TradeShippingService(connection).ship(trade_id, 1)
        self.assertIsInstance(result, TradeShippingResultDTO)

    def test_migration_forward_repeat_and_empty_backout(self):
        empty_path = Path(self.test_dir.name) / "empty.db"
        with self.connection(empty_path) as connection:
            self.assertEqual((1, 2, 3), migrate(connection, target_version=3))
            self.assertEqual((), migrate(connection, target_version=3))
            self.assertEqual((3,), rollback(connection, target_version=2))
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        self.assertNotIn("trade_shipping_status", tables)
        self.assertIn("trade_reservations", tables)

    def test_shipping_backout_fails_closed_after_first_shipment(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, target_version=2)
            version = connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0]
            status = connection.execute(
                "SELECT requester_shipped FROM trade_shipping_status"
            ).fetchone()[0]
        self.assertEqual(3, version)
        self.assertEqual(1, status)

    def test_completed_legacy_trade_remains_readable_after_v0003(self):
        trade = self.row("SELECT * FROM trade_requests WHERE id=1")
        self.assertEqual("completed", trade["status"])
        self.assertEqual('["2"]', trade["give_codes"])
        self.assertEqual('["4"]', trade["get_codes"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(1, trade["to_confirmed"])

    def test_canonical_databases_remain_unchanged(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
