import atexit
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s22-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.smart_trade_requests import (  # noqa: E402
    SMART_ACCEPTED_EVENT,
    SMART_REQUEST_MARKER,
    SmartTradeRequestCode,
    SmartTradeRequestService,
)


class SmartTradeRequestTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s22-")
        self.test_db = Path(self.test_dir.name) / "s22.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            migrate(connection, target_version=5)
            connection.execute("DELETE FROM trade_receipt_report_positions")
            connection.execute("DELETE FROM trade_receipt_reports")
            connection.execute("DELETE FROM trade_receipt_status")
            connection.execute("DELETE FROM trade_shipping_status")
            connection.execute("DELETE FROM trade_reservations")
            connection.execute("DELETE FROM trade_events")
            connection.execute("DELETE FROM trade_positions")
            connection.execute("DELETE FROM trades")
            connection.execute("DELETE FROM trade_requests")
            connection.execute("DELETE FROM notifications")
            connection.execute("DELETE FROM stickers")
            connection.executemany(
                "INSERT OR IGNORE INTO user_albums (user_id, album_id) VALUES (?, 'vfl')",
                ((1,), (2,), (3,)),
            )
        self.set_inventory(1, {"1": 2})
        self.set_inventory(2, {"3": 2})
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def set_inventory(self, user_id, quantities):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id='vfl'",
                (user_id,),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, 'vfl', ?, 'owned', ?, ?)
                """,
                (
                    (user_id, code, max(quantity - 1, 0), quantity)
                    for code, quantity in quantities.items()
                ),
            )

    def row(self, statement, parameters=()):
        with self.connection() as connection:
            return connection.execute(statement, parameters).fetchone()

    def count(self, table, where="1=1", parameters=()):
        return self.row(
            f"SELECT COUNT(*) AS count FROM {table} WHERE {where}", parameters
        )["count"]

    def create_smart(self, give=("1",), get=("3",), now_provider=None):
        with self.connection() as connection:
            return SmartTradeRequestService(
                connection, now_provider=now_provider
            ).create("vfl", 1, 2, give, get)

    def direct_smart(self, give, get, created_at=None):
        created_at = created_at or (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).strftime("%Y-%m-%d %H:%M:%S")
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status, from_confirmed, created_at)
                VALUES ('vfl', 1, 2, ?, ?, 'open', ?, ?)
                """,
                (
                    __import__("json").dumps(list(give)),
                    __import__("json").dumps(list(get)),
                    SMART_REQUEST_MARKER,
                    created_at,
                ),
            )
            return cursor.lastrowid

    def result_id_from_page(self, body):
        match = re.search(r'name="result_id" value="([0-9a-f]+)"', body)
        self.assertIsNotNone(match, body)
        return match.group(1)

    def test_create_marks_smart_request_without_reservation_or_inventory_mutation(self):
        before = self.row(
            "SELECT quantity, duplicates FROM stickers WHERE user_id=1 AND sticker_code='1'"
        )
        result = self.create_smart()
        trade = self.row("SELECT * FROM trade_requests WHERE id=?", (result.trade_request_id,))
        after = self.row(
            "SELECT quantity, duplicates FROM stickers WHERE user_id=1 AND sticker_code='1'"
        )

        self.assertEqual(SmartTradeRequestCode.CREATED, result.code)
        self.assertEqual(("open", SMART_REQUEST_MARKER), (
            trade["status"], trade["from_confirmed"]
        ))
        self.assertEqual(tuple(before), tuple(after))
        self.assertEqual(0, self.count("trade_reservations"))

    def test_global_limit_counts_only_open_smart_requests(self):
        with self.connection() as connection:
            for partner in (2, 2, 2):
                connection.execute(
                    """
                    INSERT INTO trade_requests
                        (album_id, from_user_id, to_user_id, give_codes, get_codes,
                         status, from_confirmed)
                    VALUES ('vfl', 1, ?, '["1"]', '["3"]', 'open', ?)
                    """,
                    (partner, SMART_REQUEST_MARKER),
                )
            connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open')
                """
            )
        result = self.create_smart()
        self.assertEqual(SmartTradeRequestCode.LIMIT_REACHED, result.code)
        self.assertEqual(4, self.count("trade_requests"))

    def test_manual_requests_do_not_count_toward_limit(self):
        with self.connection() as connection:
            for _ in range(4):
                connection.execute(
                    """
                    INSERT INTO trade_requests
                        (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                    VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open')
                    """
                )
        self.assertEqual(SmartTradeRequestCode.CREATED, self.create_smart().code)

    def test_expiry_boundary_is_exactly_48_hours(self):
        trade_id = self.direct_smart(
            ("1",), ("3",), "2026-08-07 10:00:00"
        )
        before = datetime(2026, 8, 9, 9, 59, 59, tzinfo=timezone.utc)
        at_boundary = datetime(2026, 8, 9, 10, 0, 0, tzinfo=timezone.utc)
        with self.connection() as connection:
            state = SmartTradeRequestService(
                connection, now_provider=lambda: before
            ).inspect(trade_id, 1)
        self.assertEqual(SmartTradeRequestCode.READY, state.code)
        with self.connection() as connection:
            state = SmartTradeRequestService(
                connection, now_provider=lambda: at_boundary
            ).inspect(trade_id, 1)
        self.assertEqual(SmartTradeRequestCode.EXPIRED, state.code)
        self.assertEqual(
            "expired",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )

    def test_partial_package_change_stays_open_and_is_never_rewritten(self):
        self.set_inventory(1, {"1": 2, "2": 2})
        self.set_inventory(2, {"3": 2, "4": 2})
        trade_id = self.direct_smart(("1", "2"), ("3", "4"))
        self.set_inventory(1, {"1": 2})
        self.set_inventory(2, {"3": 2})
        with self.connection() as connection:
            state = SmartTradeRequestService(connection).inspect(trade_id, 1)
        trade = self.row("SELECT * FROM trade_requests WHERE id=?", (trade_id,))
        self.assertEqual(SmartTradeRequestCode.PACKAGE_CHANGED, state.code)
        self.assertEqual("open", trade["status"])
        self.assertEqual('["1", "2"]', trade["give_codes"])
        self.assertEqual('["3", "4"]', trade["get_codes"])

    def test_no_bilateral_remainder_marks_request_obsolete(self):
        trade_id = self.direct_smart(("1",), ("3",))
        self.set_inventory(2, {})
        with self.connection() as connection:
            state = SmartTradeRequestService(connection).inspect(trade_id, 1)
        self.assertEqual(SmartTradeRequestCode.OBSOLETE, state.code)
        self.assertEqual(
            "obsolete",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )

    def test_smart_page_is_read_only_and_exclusion_is_not_persisted(self):
        response = self.client.get("/album/vfl/smart-trades?exclude_partner_id=3")
        body = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("nicht editierbar", body)
        self.assertNotIn('name="give_codes"', body)
        self.assertNotIn('name="get_codes"', body)
        with self.connection() as connection:
            columns = [row["name"] for row in connection.execute(
                "PRAGMA table_info(trade_requests)"
            ).fetchall()]
        self.assertNotIn("excluded_partner_id", columns)

    def test_route_happy_path_creates_request_then_existing_acceptance_reserves(self):
        page = self.client.get("/album/vfl/smart-trades").get_data(as_text=True)
        result_id = self.result_id_from_page(page)
        response = self.client.post(
            "/album/vfl/smart-trades/2/request",
            data={"result_id": result_id},
        )
        self.assertEqual(302, response.status_code)
        trade = self.row("SELECT * FROM trade_requests ORDER BY id DESC LIMIT 1")
        self.assertEqual(SMART_REQUEST_MARKER, trade["from_confirmed"])
        self.login_as(2)
        accepted = self.client.post(f"/trade/{trade['id']}/accept")
        self.assertEqual(302, accepted.status_code)
        self.assertEqual(
            "accepted",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade["id"],))["status"],
        )
        self.assertEqual(2, self.count("trade_reservations"))
        self.assertEqual(
            1,
            self.count("trade_events", "event_type=?", (SMART_ACCEPTED_EVENT,)),
        )

    def test_opening_changed_package_blocks_accept_action(self):
        self.set_inventory(1, {"1": 2, "2": 2})
        self.set_inventory(2, {"3": 2, "4": 2})
        trade_id = self.direct_smart(("1", "2"), ("3", "4"))
        self.set_inventory(1, {"1": 2})
        self.set_inventory(2, {"3": 2})
        self.login_as(2)
        body = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Paket nicht mehr vollständig verfügbar", body)
        self.assertIn("Beim Absender nicht mehr frei: 2 (1x)", body)
        self.assertIn("Beim Empfänger nicht mehr frei: 4 (1x)", body)
        self.assertIn("Smart-Paket nicht annehmbar", body)
        self.assertNotIn("Transfer durchführen", body)

    def test_acceptance_rechecks_and_creates_no_reservation_for_changed_package(self):
        trade_id = self.direct_smart(("1",), ("3",))
        self.set_inventory(2, {})
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(
            "obsolete",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )
        self.assertEqual(0, self.count("trade_reservations"))

    def test_decline_checks_expiry_and_preserves_expired_status(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=49)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        trade_id = self.direct_smart(("1",), ("3",), old)
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/decline")
        self.assertEqual(
            "expired",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )
        self.assertEqual(
            0,
            self.count("notifications", "title='Tauschanfrage abgelehnt'"),
        )

    def test_opening_is_an_expiry_trigger(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=49)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        trade_id = self.direct_smart(("1",), ("3",), old)
        body = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Smart-Anfrage abgelaufen", body)
        self.assertEqual(
            "expired",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )

    def test_accepting_is_an_expiry_trigger_and_never_reserves(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=49)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        trade_id = self.direct_smart(("1",), ("3",), old)
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(
            "expired",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )
        self.assertEqual(0, self.count("trade_reservations"))

    def test_unauthorized_user_cannot_open_or_accept_smart_request(self):
        trade_id = self.direct_smart(("1",), ("3",))
        self.login_as(3)
        response = self.client.get(f"/trades/{trade_id}")
        self.assertEqual(302, response.status_code)
        self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(
            "open",
            self.row("SELECT status FROM trade_requests WHERE id=?", (trade_id,))["status"],
        )
        self.assertEqual(0, self.count("trade_reservations"))

    def test_stale_s21_result_is_rejected_without_trade_creation(self):
        response = self.client.post(
            "/album/vfl/smart-trades/2/request",
            data={"result_id": "stale-result"},
        )
        self.assertEqual(302, response.status_code)
        self.assertIn("neu%20berechnen", response.headers["Location"])
        self.assertEqual(0, self.count("trade_requests"))

    def test_manual_request_remains_editable_and_uses_existing_flow(self):
        page = self.client.get("/album/vfl/trade/2").get_data(as_text=True)
        self.assertIn("input.name = 'give_codes'", page)
        self.assertIn("input.name = 'get_codes'", page)
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        trade = self.row("SELECT * FROM trade_requests ORDER BY id DESC LIMIT 1")
        self.assertEqual(0, trade["from_confirmed"])
        self.assertEqual("open", trade["status"])


if __name__ == "__main__":
    unittest.main()
