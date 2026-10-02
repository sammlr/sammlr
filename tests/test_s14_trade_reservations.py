import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s14-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate, rollback  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.inventory_write import InventoryWriteService  # noqa: E402
from services.trade_reservations import (  # noqa: E402
    TradeAcceptanceCode,
    TradeAcceptanceResultDTO,
    TradeReservationService,
)


class TradeReservationTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s14-")
        self.test_db = Path(self.test_dir.name) / "reservations.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2), migrate(connection, target_version=2))
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

    def create_open_trade(self, give_codes='["1"]', get_codes='["3"]'):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, ?, ?, 'open')
                """,
                (give_codes, get_codes),
            )
            return cursor.lastrowid

    def row(self, statement, parameters=()):
        with self.connection() as connection:
            return connection.execute(statement, parameters).fetchone()

    def count(self, table, where="1=1", parameters=()):
        return self.row(
            f"SELECT COUNT(*) AS count FROM {table} WHERE {where}", parameters
        )["count"]

    def reservations(self, trade_request_id=None):
        statement = """
            SELECT r.*, t.legacy_trade_request_id
            FROM trade_reservations r
            JOIN trades t ON t.id=r.trade_id
        """
        parameters = ()
        if trade_request_id is not None:
            statement += " WHERE t.legacy_trade_request_id=?"
            parameters = (trade_request_id,)
        statement += " ORDER BY r.user_id, r.sticker_code"
        with self.connection() as connection:
            return connection.execute(statement, parameters).fetchall()

    def acceptance_notification_count(self):
        return self.count(
            "notifications",
            "user_id=1 AND title='Tauschanfrage angenommen'",
        )

    def test_request_alone_creates_no_reservation(self):
        self.login_as(1)
        before = self.count("trade_requests")
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(before + 1, self.count("trade_requests"))
        self.assertEqual(0, self.count("trade_reservations"))
        self.assertEqual(0, self.count("trades"))

    def test_valid_acceptance_reserves_every_outgoing_position(self):
        trade_id = self.create_open_trade('["1", "1"]', '["3"]')
        response = self.client.post(f"/trade/{trade_id}/accept")

        self.assertEqual(302, response.status_code)
        trade = self.row("SELECT * FROM trade_requests WHERE id=?", (trade_id,))
        reservations = self.reservations(trade_id)
        self.assertEqual("accepted", trade["status"])
        self.assertEqual(
            [(1, "vfl", "1", 2, "active"), (2, "vfl", "3", 1, "active")],
            [
                (row["user_id"], row["album_id"], row["sticker_code"], row["quantity"], row["state"])
                for row in reservations
            ],
        )
        self.assertEqual(2, self.count("trade_positions"))
        self.assertEqual(1, self.count("trades", "legacy_trade_request_id=?", (trade_id,)))

    def test_reservation_reduces_available_and_reservable_only(self):
        trade_id = self.create_open_trade()
        with self.connection() as connection:
            before_1 = InventoryReadService(connection).album(1, "vfl").availability("1")
            before_2 = InventoryReadService(connection).album(2, "vfl").availability("3")
        self.client.post(f"/trade/{trade_id}/accept")
        with self.connection() as connection:
            after_1 = InventoryReadService(connection).album(1, "vfl").availability("1")
            after_2 = InventoryReadService(connection).album(2, "vfl").availability("3")

        self.assertEqual((3, 1, 0, 2), (
            before_1.physical, before_1.assigned, before_1.reserved, before_1.available
        ))
        self.assertEqual((3, 1, 1, 1), (
            after_1.physical, after_1.assigned, after_1.reserved, after_1.available
        ))
        self.assertEqual((2, 1, 1, 0), (
            after_2.physical, after_2.assigned, after_2.reserved, after_2.reservable
        ))

    def test_physical_assigned_and_album_progress_do_not_change_on_acceptance(self):
        trade_id = self.create_open_trade()
        with self.connection() as connection:
            service = InventoryReadService(connection)
            album_before = service.album(1, "vfl")
            availability_before = album_before.availability("1")
            progress_before = album_before.progress(webapp.all_codes("vfl"), 250)
            sticker_before = tuple(connection.execute(
                "SELECT quantity, duplicates FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone())
        self.client.post(f"/trade/{trade_id}/accept")
        with self.connection() as connection:
            album_after = InventoryReadService(connection).album(1, "vfl")
            availability_after = album_after.availability("1")
            progress_after = album_after.progress(webapp.all_codes("vfl"), 250)
            sticker_after = tuple(connection.execute(
                "SELECT quantity, duplicates FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone())

        self.assertEqual(sticker_before, sticker_after)
        self.assertEqual(availability_before.physical, availability_after.physical)
        self.assertEqual(availability_before.assigned, availability_after.assigned)
        self.assertEqual(progress_before.collected, progress_after.collected)
        self.assertEqual(progress_before.percent, progress_after.percent)

    def test_matching_does_not_offer_reserved_copy_again(self):
        trade_id = self.create_open_trade()
        with self.connection() as connection:
            service = InventoryReadService(connection)
            before = webapp.availability_trade_candidates(
                "vfl", service.album(1, "vfl"), service.album(2, "vfl")
            )
        self.client.post(f"/trade/{trade_id}/accept")
        with self.connection() as connection:
            service = InventoryReadService(connection)
            after = webapp.availability_trade_candidates(
                "vfl", service.album(1, "vfl"), service.album(2, "vfl")
            )

        self.assertEqual(1, before[0]["3"])
        self.assertEqual(2, before[1]["1"])
        self.assertNotIn("3", after[0])
        self.assertEqual(1, after[1]["1"])

    def test_insufficient_inventory_rolls_back_entire_acceptance(self):
        trade_id = self.create_open_trade()
        with self.connection() as connection:
            connection.execute(
                "UPDATE stickers SET quantity=1, duplicates=0 WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'"
            )
        response = self.client.post(f"/trade/{trade_id}/accept")

        self.assertEqual(302, response.status_code)
        self.assertEqual(
            "open",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )
        self.assertEqual(0, len(self.reservations(trade_id)))
        self.assertEqual(0, self.count("trades", "legacy_trade_request_id=?", (trade_id,)))
        self.assertEqual(0, self.acceptance_notification_count())

    def test_conflict_on_one_position_leaves_no_partial_reservation(self):
        trade_id = self.create_open_trade('["1"]', '["3", "3"]')
        self.client.post(f"/trade/{trade_id}/accept")

        self.assertEqual(0, len(self.reservations(trade_id)))
        self.assertEqual(0, self.count("trade_positions", "trade_id IN (SELECT id FROM trades WHERE legacy_trade_request_id=?)", (trade_id,)))
        self.assertEqual(
            "open",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )

    def test_repeated_acceptance_is_idempotent_and_does_not_notify(self):
        trade_id = self.create_open_trade()
        first = self.client.post(f"/trade/{trade_id}/accept")
        second = self.client.post(f"/trade/{trade_id}/accept")

        self.assertEqual((302, 302), (first.status_code, second.status_code))
        self.assertEqual(2, len(self.reservations(trade_id)))
        self.assertEqual(2, self.count("trade_positions"))
        self.assertEqual(0, self.acceptance_notification_count())

    def test_competing_acceptances_cannot_reserve_same_copy(self):
        first_trade = self.create_open_trade()
        second_trade = self.create_open_trade()
        barrier = threading.Barrier(3)
        results = []
        errors = []

        def accept(trade_id):
            try:
                with self.connection() as connection:
                    barrier.wait()
                    results.append(
                        TradeReservationService(connection).accept(trade_id, 2).code
                    )
            except Exception as error:  # pragma: no cover - asserted below
                errors.append(error)

        threads = [
            threading.Thread(target=accept, args=(first_trade,)),
            threading.Thread(target=accept, args=(second_trade,)),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        self.assertCountEqual(
            [TradeAcceptanceCode.ACCEPTED, TradeAcceptanceCode.INSUFFICIENT_AVAILABLE],
            results,
        )
        self.assertEqual(1, self.count("trade_requests", "id IN (?, ?) AND status='accepted'", (first_trade, second_trade)))
        self.assertEqual(2, self.count("trade_reservations", "state='active'"))

    def test_unauthorized_user_creates_no_reservation(self):
        trade_id = self.create_open_trade()
        self.login_as(1)
        response = self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(302, response.status_code)
        self.assertEqual(0, len(self.reservations(trade_id)))
        self.assertEqual("open", self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"])

    def test_invalid_trade_state_creates_no_reservation(self):
        with self.connection() as connection:
            result = TradeReservationService(connection).accept(1, 2)
        self.assertIsInstance(result, TradeAcceptanceResultDTO)
        self.assertEqual(TradeAcceptanceCode.INVALID_TRADE_STATE, result.code)
        self.assertEqual(0, self.count("trade_reservations"))

    def test_allowed_failure_releases_reservations_exactly_once(self):
        trade_id = self.create_open_trade()
        self.client.post(f"/trade/{trade_id}/accept")
        self.login_as(1)
        first = self.client.post(f"/trade/{trade_id}/fail")
        second = self.client.post(f"/trade/{trade_id}/fail")

        self.assertEqual((302, 302), (first.status_code, second.status_code))
        rows = self.reservations(trade_id)
        self.assertEqual({"released"}, {row["state"] for row in rows})
        self.assertTrue(all(row["released_at"] for row in rows))
        self.assertEqual({"failed"}, {row["release_reason"] for row in rows})
        self.assertEqual("failed", self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"])

    def test_existing_completion_consumes_and_releases_reservations_once(self):
        trade_id = self.create_open_trade()
        self.client.post(f"/trade/{trade_id}/accept")
        self.login_as(1)
        first_confirmation = self.client.post(f"/trade/{trade_id}/confirm")
        self.login_as(2)
        completion = self.client.post(f"/trade/{trade_id}/confirm")
        repeated = self.client.post(f"/trade/{trade_id}/confirm")

        self.assertEqual(
            (302, 302, 302),
            (first_confirmation.status_code, completion.status_code, repeated.status_code),
        )
        self.assertEqual(
            "completed",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )
        rows = self.reservations(trade_id)
        self.assertEqual({"released"}, {row["state"] for row in rows})
        self.assertEqual({"completed"}, {row["release_reason"] for row in rows})
        inventory = {
            (row["user_id"], row["sticker_code"]): (row["quantity"], row["duplicates"])
            for row in (
                self.row(
                    "SELECT user_id, sticker_code, quantity, duplicates FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
                ),
                self.row(
                    "SELECT user_id, sticker_code, quantity, duplicates FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='3'"
                ),
                self.row(
                    "SELECT user_id, sticker_code, quantity, duplicates FROM stickers WHERE user_id=2 AND album_id='vfl' AND sticker_code='1'"
                ),
                self.row(
                    "SELECT user_id, sticker_code, quantity, duplicates FROM stickers WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'"
                ),
            )
        }
        self.assertEqual(
            {
                (1, "1"): (2, 1),
                (1, "3"): (1, 0),
                (2, "1"): (1, 0),
                (2, "3"): (1, 0),
            },
            inventory,
        )

    def test_inventory_guard_protects_active_reserved_surplus(self):
        trade_id = self.create_open_trade()
        self.client.post(f"/trade/{trade_id}/accept")
        with self.connection() as connection:
            blocked = InventoryWriteService(connection).remove(1, "vfl", "1", 2)
            stored = tuple(connection.execute(
                "SELECT quantity, duplicates FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone())
        self.assertFalse(blocked.allowed)
        self.assertEqual("BELOW_BOUND_STOCK", blocked.error_code)
        self.assertEqual((3, 2), stored)

    def test_transaction_error_rolls_back_reservations_status_and_side_effect(self):
        trade_id = self.create_open_trade()

        def failing_side_effect(connection, trade):
            connection.execute(
                "INSERT INTO notifications (user_id, title, body) VALUES (1, 'temporary', 'rollback')"
            )
            raise RuntimeError("deliberate S14 rollback proof")

        with self.connection() as connection:
            result = TradeReservationService(connection).accept(
                trade_id, 2, on_accepted=failing_side_effect
            )

        self.assertEqual(TradeAcceptanceCode.TRANSACTION_ERROR, result.code)
        self.assertEqual("open", self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"])
        self.assertEqual(0, len(self.reservations(trade_id)))
        self.assertEqual(0, self.count("notifications", "title='temporary'"))

    def test_all_stable_acceptance_codes_are_ui_neutral_strings(self):
        self.assertEqual(
            {
                "ACCEPTED",
                "ALREADY_ACCEPTED",
                "INSUFFICIENT_AVAILABLE",
                "INVALID_TRADE_STATE",
                "UNAUTHORIZED",
                "TRANSACTION_ERROR",
            },
            {code.value for code in TradeAcceptanceCode},
        )
        self.assertTrue(issubclass(TradeAcceptanceCode, str))

    def test_migration_forward_repeat_and_backout_on_empty_database(self):
        empty_path = Path(self.test_dir.name) / "empty.db"
        with self.connection(empty_path) as connection:
            self.assertEqual((1, 2), migrate(connection, target_version=2))
            self.assertEqual((), migrate(connection, target_version=2))
            self.assertEqual((2,), rollback(connection, target_version=1))
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        self.assertNotIn("trade_reservations", tables)
        self.assertIn("trades", tables)

    def test_fixture_backout_preserves_legacy_completed_trade(self):
        with self.connection() as connection:
            before = tuple(connection.execute("SELECT * FROM trade_requests WHERE id=1").fetchone())
            self.assertEqual((2,), rollback(connection, target_version=1))
            after = tuple(connection.execute("SELECT * FROM trade_requests WHERE id=1").fetchone())
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        self.assertEqual(before, after)
        self.assertEqual("completed", after[6])
        self.assertEqual('["2"]', after[4])
        self.assertEqual('["4"]', after[5])
        self.assertNotIn("trade_reservations", tables)

    def test_backout_fails_closed_when_reservation_history_exists(self):
        trade_id = self.create_open_trade()
        self.client.post(f"/trade/{trade_id}/accept")
        with self.connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, target_version=1)
            version = connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0]
            reservation_count = connection.execute(
                "SELECT COUNT(*) FROM trade_reservations"
            ).fetchone()[0]
        self.assertEqual(2, version)
        self.assertEqual(2, reservation_count)

    def test_acceptance_creates_no_notification_and_trophies_stay_unchanged(self):
        trade_id = self.create_open_trade()
        trophy_count = self.count("unlocked_trophies")
        self.client.post(f"/trade/{trade_id}/accept")
        self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(0, self.acceptance_notification_count())
        self.assertEqual(trophy_count, self.count("unlocked_trophies"))

    def test_canonical_databases_remain_unchanged(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
