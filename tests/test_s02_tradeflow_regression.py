import atexit
import hashlib
import json
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


# webapp initializes its configured database while being imported. Bootstrap
# that import against a disposable S00 copy, never against sammlr.db.
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s02-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


if os.environ.get("SAMMLR_S02_MUTATE_COMPLETION") == "1":
    _reference_complete_trade = webapp.complete_trade

    def _mutated_complete_trade(connection, trade):
        # S02 mutation proof only: double-book inside this test process.
        # The application file remains untouched.
        _reference_complete_trade(connection, trade)
        _reference_complete_trade(connection, trade)

    webapp.complete_trade = _mutated_complete_trade


class TradeflowRegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s02-test-")
        self.test_db = Path(self.test_dir.name) / "tradeflow.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S02 test.",
        )
        self.test_dir.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def query_one(self, statement, parameters=()):
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(statement, parameters).fetchone()

    def execute(self, statement, parameters=()):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(statement, parameters)
            connection.commit()

    def trade(self, trade_id):
        return self.query_one(
            "SELECT * FROM trade_requests WHERE id=?",
            (trade_id,),
        )

    def trade_count(self):
        return self.query_one(
            "SELECT COUNT(*) AS count FROM trade_requests"
        )["count"]

    def inventory(self):
        result = {}
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT user_id, sticker_code, quantity, duplicates
                FROM stickers
                WHERE album_id='vfl'
                  AND user_id IN (1, 2)
                  AND sticker_code IN ('1', '3')
                ORDER BY user_id, sticker_code
                """
            ).fetchall()
        for row in rows:
            result[(row["user_id"], row["sticker_code"])] = (
                row["quantity"],
                row["duplicates"],
            )
        return result

    def assert_completed_inventory(self):
        self.assertEqual(
            {
                (1, "1"): (2, 1),
                (1, "3"): (1, 0),
                (2, "1"): (1, 0),
                (2, "3"): (1, 0),
            },
            self.inventory(),
        )

    def create_request(self):
        self.login_as(1)
        count_before = self.trade_count()
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(count_before + 1, self.trade_count())
        trade_id = self.query_one(
            "SELECT MAX(id) AS id FROM trade_requests"
        )["id"]
        self.assertGreater(trade_id, 1)
        return trade_id

    def accept_request(self, trade_id):
        self.login_as(2)
        response = self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(302, response.status_code)

    def create_accepted_trade(self):
        trade_id = self.create_request()
        self.accept_request(trade_id)
        self.assertEqual("accepted", self.trade(trade_id)["status"])
        return trade_id

    def complete_trade_happy_path(self):
        trade_id = self.create_accepted_trade()
        self.login_as(1)
        self.client.post(f"/trade/{trade_id}/confirm")
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/confirm")
        return trade_id

    def test_paper_list_deal_composition_uses_missing_and_duplicate_copies(self):
        response = self.client.get("/album/vfl/liste")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn('data-list-mode="get" data-code="3"', html)
        self.assertEqual(
            2,
            html.count('data-list-mode="give" data-code="1"'),
        )

    def test_paper_list_transfer_books_get_and_give_for_current_user(self):
        before_trade_count = self.trade_count()

        response = self.client.post(
            "/album/vfl/liste/trade",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual((2, 1), self.inventory()[(1, "1")])
        self.assertEqual((1, 0), self.inventory()[(1, "3")])
        self.assertEqual((2, 1), self.inventory()[(2, "3")])
        self.assertEqual(before_trade_count, self.trade_count())
        with self.client.session_transaction() as session:
            self.assertEqual("transfer", session["last_action"]["action"])
            self.assertEqual(["1"], session["last_action"]["give_codes"])
            self.assertEqual(["3"], session["last_action"]["get_codes"])

        refreshed_html = self.client.get("/album/vfl/liste").get_data(as_text=True)
        self.assertNotIn('data-list-mode="get" data-code="3"', refreshed_html)
        self.assertEqual(
            1,
            refreshed_html.count('data-list-mode="give" data-code="1"'),
        )
        self.assertIn('<a class="sticker-list-back" href="/album/vfl"', refreshed_html)
        self.assertIn('aria-label="← Zurück zum Album"', refreshed_html)

    def test_paper_list_transfer_rejects_more_than_duplicate_supply(self):
        before = self.inventory()

        response = self.client.post(
            "/album/vfl/liste/trade",
            data={
                "give_codes": ["1", "1", "1"],
                "get_codes": ["3"],
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual(before, self.inventory())
        with self.client.session_transaction() as session:
            self.assertNotIn("last_action", session)

    def test_trade_request_creates_open_manual_package_without_booking(self):
        before = self.inventory()
        notifications_before = self.query_one(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_id=2"
        )["count"]

        trade_id = self.create_request()
        trade = self.trade(trade_id)

        self.assertEqual("vfl", trade["album_id"])
        self.assertEqual(1, trade["from_user_id"])
        self.assertEqual(2, trade["to_user_id"])
        self.assertEqual(["1"], json.loads(trade["give_codes"]))
        self.assertEqual(["3"], json.loads(trade["get_codes"]))
        self.assertEqual("open", trade["status"])
        self.assertEqual(0, trade["from_confirmed"])
        self.assertEqual(0, trade["to_confirmed"])
        self.assertEqual(before, self.inventory())
        notifications_after = self.query_one(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_id=2"
        )["count"]
        self.assertEqual(notifications_before, notifications_after)

    def test_invalid_trade_request_is_rejected_without_state_change(self):
        before = self.inventory()
        before_count = self.trade_count()

        invalid_code_response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["not-a-code"], "get_codes": ["3"]},
        )
        unavailable_response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["2"], "get_codes": ["3"]},
        )
        missing_side_response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": []},
        )

        self.assertEqual(302, invalid_code_response.status_code)
        self.assertEqual(302, unavailable_response.status_code)
        self.assertEqual(302, missing_side_response.status_code)
        self.assertEqual(before_count, self.trade_count())
        self.assertEqual(before, self.inventory())

    def test_only_receiver_can_accept_and_accept_resets_confirmations(self):
        trade_id = self.create_request()
        before = self.inventory()

        self.login_as(1)
        self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual("open", self.trade(trade_id)["status"])

        self.accept_request(trade_id)
        trade = self.trade(trade_id)
        self.assertEqual("accepted", trade["status"])
        self.assertEqual(0, trade["from_confirmed"])
        self.assertEqual(0, trade["to_confirmed"])
        self.assertEqual(before, self.inventory())

    def test_receiver_can_decline_without_inventory_booking(self):
        trade_id = self.create_request()
        before = self.inventory()

        self.login_as(2)
        response = self.client.post(f"/trade/{trade_id}/decline")

        self.assertEqual(302, response.status_code)
        self.assertEqual("declined", self.trade(trade_id)["status"])
        self.assertEqual(before, self.inventory())

    def test_first_confirmation_marks_one_side_without_booking(self):
        trade_id = self.create_accepted_trade()
        before = self.inventory()

        self.login_as(1)
        response = self.client.post(f"/trade/{trade_id}/confirm")

        trade = self.trade(trade_id)
        self.assertEqual(302, response.status_code)
        self.assertEqual("accepted", trade["status"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(0, trade["to_confirmed"])
        self.assertEqual(before, self.inventory())

    def test_duplicate_first_confirmation_does_not_book_inventory(self):
        trade_id = self.create_accepted_trade()
        before = self.inventory()
        self.login_as(1)

        self.client.post(f"/trade/{trade_id}/confirm")
        self.client.post(f"/trade/{trade_id}/confirm")

        trade = self.trade(trade_id)
        self.assertEqual("accepted", trade["status"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(0, trade["to_confirmed"])
        self.assertEqual(before, self.inventory())

    def test_second_confirmation_books_both_sides_and_completes(self):
        trade_id = self.complete_trade_happy_path()
        trade = self.trade(trade_id)

        self.assertEqual("completed", trade["status"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(1, trade["to_confirmed"])
        self.assert_completed_inventory()

    def test_repeated_completion_books_inventory_exactly_once(self):
        trade_id = self.complete_trade_happy_path()
        completed_inventory = self.inventory()
        self.assert_completed_inventory()

        self.login_as(1)
        first_repeat = self.client.post(f"/trade/{trade_id}/confirm")
        self.login_as(2)
        second_repeat = self.client.post(f"/trade/{trade_id}/confirm")

        self.assertEqual(302, first_repeat.status_code)
        self.assertEqual(302, second_repeat.status_code)
        self.assertEqual("completed", self.trade(trade_id)["status"])
        self.assertEqual(completed_inventory, self.inventory())

    def test_failed_trade_keeps_inventory_unchanged(self):
        trade_id = self.create_accepted_trade()
        before = self.inventory()
        self.login_as(1)
        self.client.post(f"/trade/{trade_id}/confirm")

        self.login_as(2)
        response = self.client.post(f"/trade/{trade_id}/fail")

        trade = self.trade(trade_id)
        self.assertEqual(302, response.status_code)
        self.assertEqual("failed", trade["status"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(0, trade["to_confirmed"])
        self.assertEqual(before, self.inventory())

    def test_unrelated_user_cannot_view_accept_confirm_or_fail_trade(self):
        trade_id = self.create_request()
        before = self.inventory()
        self.login_as(3)

        detail_response = self.client.get(f"/trade/{trade_id}")
        accept_response = self.client.post(f"/trade/{trade_id}/accept")

        self.assertEqual(302, detail_response.status_code)
        self.assertEqual(302, accept_response.status_code)
        self.assertEqual("open", self.trade(trade_id)["status"])

        self.accept_request(trade_id)
        self.login_as(3)
        confirm_response = self.client.post(f"/trade/{trade_id}/confirm")
        fail_response = self.client.post(f"/trade/{trade_id}/fail")

        trade = self.trade(trade_id)
        self.assertEqual(302, confirm_response.status_code)
        self.assertEqual(302, fail_response.status_code)
        self.assertEqual("accepted", trade["status"])
        self.assertEqual(0, trade["from_confirmed"])
        self.assertEqual(0, trade["to_confirmed"])
        self.assertEqual(before, self.inventory())

    def test_unknown_trade_id_causes_no_trade_or_inventory_change(self):
        before_count = self.trade_count()
        before_inventory = self.inventory()

        self.login_as(2)
        accept_response = self.client.post("/trade/9999/accept")
        decline_response = self.client.post("/trade/9999/decline")
        confirm_response = self.client.post("/trade/9999/confirm")
        fail_response = self.client.post("/trade/9999/fail")

        for response in (
            accept_response,
            decline_response,
            confirm_response,
            fail_response,
        ):
            self.assertEqual(302, response.status_code)
        self.assertEqual(before_count, self.trade_count())
        self.assertEqual(before_inventory, self.inventory())

    def test_history_contains_completed_trade_and_excludes_failed_trade(self):
        failed_id = self.create_accepted_trade()
        self.login_as(2)
        self.client.post(f"/trade/{failed_id}/fail")
        completed_id = self.complete_trade_happy_path()

        self.login_as(1)
        response = self.client.get("/profil/trade-archiv")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertEqual("completed", self.trade(completed_id)["status"])
        self.assertEqual("failed", self.trade(failed_id)["status"])
        self.assertIn("<strong>2 Trades</strong>", html)
        self.assertEqual(2, html.count("fixture_user_2"))
        self.assertIn("Zeitpunkt nicht verfügbar", html)
        self.assertNotIn("15.01.2026", html)

    def test_legacy_cancelled_trade_stays_separate_from_active_and_history(self):
        self.execute(
            """
            INSERT INTO trade_requests (
                id, album_id, from_user_id, to_user_id,
                give_codes, get_codes, status, created_at,
                from_confirmed, to_confirmed
            )
            VALUES (
                20, 'vfl', 1, 2, '["1"]', '["3"]', 'cancelled',
                '2026-02-20 10:00:00', 0, 0
            )
            """
        )

        requests_html = self.client.get(
            "/trades?tab=requests"
        ).get_data(as_text=True)
        history_html = self.client.get(
            "/profil/trade-archiv"
        ).get_data(as_text=True)

        self.assertEqual("cancelled", self.trade(20)["status"])
        self.assertNotIn("/trades/20", requests_html)
        self.assertIn("<strong>1 Trade</strong>", history_html)


if __name__ == "__main__":
    unittest.main()
