import atexit
import hashlib
import json
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s20-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402


class TradeCompletionConsistencyTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s20-")
        self.test_db = Path(self.test_dir.name) / "completion.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5), migrate(connection, target_version=5))
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(2)

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

    def create_accepted_trade(self):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open')
                """
            )
            trade_id = cursor.lastrowid
        self.login_as(2)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/accept").status_code)
        return trade_id

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/ship")

    def receive_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/receive")

    def complete_normal_trade(self):
        trade_id = self.create_accepted_trade()
        self.assertEqual(302, self.ship_as(trade_id, 1).status_code)
        self.assertEqual(302, self.ship_as(trade_id, 2).status_code)
        self.assertEqual(302, self.receive_as(trade_id, 1).status_code)
        self.assertEqual(302, self.receive_as(trade_id, 2).status_code)
        return trade_id

    def lifecycle_row(self, trade_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT r.status, r.from_confirmed, r.to_confirmed,
                       t.id AS lifecycle_trade_id, t.lifecycle_state,
                       t.completed_at
                FROM trade_requests r
                JOIN trades t ON t.legacy_trade_request_id=r.id
                WHERE r.id=?
                """,
                (trade_id,),
            ).fetchone()

    def inventory_snapshot(self):
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT user_id, album_id, sticker_code, quantity, duplicates
                FROM stickers ORDER BY user_id, album_id, sticker_code
                """
            ).fetchall()
            return tuple(tuple(row) for row in rows)

    def side_effect_snapshot(self, trade_id):
        with self.connection() as connection:
            lifecycle = connection.execute(
                "SELECT id, completed_at FROM trades WHERE legacy_trade_request_id=?",
                (trade_id,),
            ).fetchone()
            return {
                "inventory": self.inventory_snapshot(),
                "completed_at": lifecycle["completed_at"],
                "completed_events": connection.execute(
                    "SELECT COUNT(*) FROM trade_events WHERE trade_id=? AND event_type='completed'",
                    (lifecycle["id"],),
                ).fetchone()[0],
                "notifications": connection.execute(
                    "SELECT COUNT(*) FROM notifications WHERE title='Tausch abgeschlossen'"
                ).fetchone()[0],
                "trophies": connection.execute(
                    "SELECT COUNT(*) FROM unlocked_trophies"
                ).fetchone()[0],
            }

    def position_for_receiver(self, trade_id, user_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT p.id, p.quantity
                FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=?
                """,
                (trade_id, user_id),
            ).fetchone()

    def complete_problem_trade(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        self.login_as(2)
        position = self.position_for_receiver(trade_id, 2)
        self.client.post(
            f"/trade/{trade_id}/problem",
            data={
                f"received_{position['id']}": "0",
                f"problem_{position['id']}": "missing",
            },
        )
        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        return trade_id

    def test_normal_bilateral_receipt_completes_legacy_and_lifecycle(self):
        trade_id = self.complete_normal_trade()
        state = self.lifecycle_row(trade_id)
        self.assertEqual("completed", state["status"])
        self.assertEqual("completed", state["lifecycle_state"])
        self.assertTrue(state["completed_at"])

    def test_one_received_side_keeps_trade_open(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        state = self.lifecycle_row(trade_id)
        self.assertEqual("accepted", state["status"])
        self.assertEqual("partially_received", state["lifecycle_state"])
        self.assertIsNone(state["completed_at"])

    def test_open_problem_prevents_completion(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        self.login_as(2)
        position = self.position_for_receiver(trade_id, 2)
        self.client.post(
            f"/trade/{trade_id}/problem",
            data={f"received_{position['id']}": "0", f"problem_{position['id']}": "missing"},
        )
        state = self.lifecycle_row(trade_id)
        self.assertEqual("accepted", state["status"])
        self.assertEqual("problem_open", state["lifecycle_state"])

    def test_resolved_problem_and_both_receipts_complete_trade(self):
        state = self.lifecycle_row(self.complete_problem_trade())
        self.assertEqual(("completed", "completed"), (state["status"], state["lifecycle_state"]))

    def test_completed_detail_has_no_mutating_trade_actions(self):
        trade_id = self.complete_normal_trade()
        html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Trade abgeschlossen", html)
        for action in ("/ship", "/receive", "/problem\"", "/problem/resolve", "/confirm", "/fail"):
            self.assertNotIn(f'action="/trade/{trade_id}{action}', html)
        self.assertNotIn(f'href="/trades/{trade_id}/problem"', html)

    def test_completed_trade_is_absent_from_running_agreements(self):
        trade_id = self.complete_normal_trade()
        self.login_as(2)
        html = self.client.get("/trades?tab=agreements").get_data(as_text=True)
        self.assertNotIn(f'href="/trades/{trade_id}?origin=trades"', html)

    def test_completed_timeline_has_no_pending_required_step(self):
        trade_id = self.complete_normal_trade()
        html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        timeline = re.search(r'<section class="card trade-timeline".*?</section>', html, re.DOTALL)
        self.assertIsNotNone(timeline)
        self.assertNotIn('trade-timeline-item pending', timeline.group(0))
        self.assertRegex(
            timeline.group(0),
            re.compile(r'Trade abgeschlossen.*trade-timeline-time', re.DOTALL),
        )

    def test_completion_timestamp_is_consistent_in_detail_timeline_and_archive(self):
        trade_id = self.complete_normal_trade()
        state = self.lifecycle_row(trade_id)
        formatted = webapp.format_sammlr_timestamp(state["completed_at"])
        date_label, time_label = formatted.split("|")
        detail = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        archive = self.client.get("/profil/trade-archiv").get_data(as_text=True)
        self.assertGreaterEqual(detail.count(date_label), 2)
        self.assertIn(time_label, detail)
        self.assertIn(date_label, archive)

    def test_profile_archive_uses_same_completed_state_and_links_readonly_detail(self):
        trade_id = self.complete_normal_trade()
        archive = self.client.get("/profil/trade-archiv").get_data(as_text=True)
        self.assertIn(f'href="/trades/{trade_id}"', archive)
        self.assertRegex(archive, r"<strong>\d+ Trades?</strong>")

    def test_global_and_album_trade_boards_exclude_completed_trade(self):
        trade_id = self.complete_normal_trade()
        global_html = self.client.get("/trades?tab=agreements").get_data(as_text=True)
        album_html = self.client.get("/album/vfl/trades?tab=agreements").get_data(as_text=True)
        self.assertNotIn(f"/trades/{trade_id}?", global_html)
        self.assertNotIn(f"/trades/{trade_id}?", album_html)

    def test_direct_receipt_retry_does_not_double_book(self):
        trade_id = self.complete_normal_trade()
        before = self.side_effect_snapshot(trade_id)
        self.client.post(f"/trade/{trade_id}/ship")
        self.receive_as(trade_id, 2)
        self.client.post(f"/trade/{trade_id}/problem", data={})
        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        self.client.post(f"/trade/{trade_id}/accept")
        self.client.post(f"/trade/{trade_id}/decline")
        self.client.post(f"/trade/{trade_id}/confirm")
        self.client.post(f"/trade/{trade_id}/fail")
        self.assertEqual(before, self.side_effect_snapshot(trade_id))

    def test_completion_trophy_count_is_stable_on_all_retries(self):
        trade_id = self.complete_normal_trade()
        before = self.side_effect_snapshot(trade_id)
        self.client.post(f"/trade/{trade_id}/receive")
        self.client.post(f"/trade/{trade_id}/confirm")
        self.client.post(f"/trade/{trade_id}/fail")
        self.assertEqual(before["trophies"], self.side_effect_snapshot(trade_id)["trophies"])

    def test_completion_creates_no_generic_completion_notification(self):
        trade_id = self.complete_normal_trade()
        self.client.post(f"/trade/{trade_id}/receive")
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT user_id, COUNT(*) AS amount FROM notifications
                WHERE title='Tausch abgeschlossen'
                GROUP BY user_id
                """
            ).fetchall()
        self.assertEqual([], rows)

    def test_completed_event_and_timestamp_exist_exactly_once(self):
        trade_id = self.complete_normal_trade()
        before = self.side_effect_snapshot(trade_id)
        self.receive_as(trade_id, 1)
        after = self.side_effect_snapshot(trade_id)
        self.assertEqual(1, after["completed_events"])
        self.assertEqual(before["completed_at"], after["completed_at"])

    def test_legacy_generic_completion_cannot_rebook_lifecycle_trade(self):
        trade_id = self.complete_normal_trade()
        before = self.side_effect_snapshot(trade_id)
        self.client.post(f"/trade/{trade_id}/confirm")
        self.assertEqual(before, self.side_effect_snapshot(trade_id))

    def test_unrelated_user_cannot_trigger_any_completion_action(self):
        trade_id = self.complete_normal_trade()
        before = self.side_effect_snapshot(trade_id)
        self.login_as(3)
        self.client.post(f"/trade/{trade_id}/receive")
        self.client.post(f"/trade/{trade_id}/confirm")
        self.client.post(f"/trade/{trade_id}/fail")
        self.client.post(f"/trade/{trade_id}/problem", data={})
        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        self.assertEqual(before, self.side_effect_snapshot(trade_id))

    def test_completed_legacy_trade_remains_readable_and_readonly(self):
        with self.connection() as connection:
            trade = connection.execute(
                "SELECT id, from_user_id FROM trade_requests WHERE status='completed' ORDER BY id LIMIT 1"
            ).fetchone()
        self.login_as(trade["from_user_id"])
        html = self.client.get(f"/trades/{trade['id']}").get_data(as_text=True)
        self.assertIn("Abgeschlossen", html)
        self.assertNotIn(f'action="/trade/{trade["id"]}/confirm"', html)

    def test_resolved_problem_history_survives_completion(self):
        trade_id = self.complete_problem_trade()
        html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Problemhistorie", html)
        self.assertIn("Problem aufgelöst", html)
        self.assertIn("später nachgeliefert 1", html)
        timeline = re.search(r'<section class="card trade-timeline".*?</section>', html, re.DOTALL).group(0)
        self.assertLess(timeline.index("Problem bei deiner Lieferung gemeldet"), timeline.index("Problem gelöst"))
        self.assertLess(timeline.index("Problem gelöst"), timeline.index("Trade abgeschlossen"))

    def test_rendering_all_completion_views_changes_no_inventory(self):
        trade_id = self.complete_normal_trade()
        before = self.inventory_snapshot()
        self.client.get(f"/trades/{trade_id}")
        self.client.get("/trades?tab=agreements")
        self.client.get("/album/vfl/trades?tab=agreements")
        self.client.get("/profil/trade-archiv")
        self.assertEqual(before, self.inventory_snapshot())

    def test_receipt_before_own_shipping_reaches_same_final_state(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.receive_as(trade_id, 2)
        self.assertEqual("partially_received", self.lifecycle_row(trade_id)["lifecycle_state"])
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        state = self.lifecycle_row(trade_id)
        self.assertEqual(("completed", "completed"), (state["status"], state["lifecycle_state"]))


if __name__ == "__main__":
    unittest.main()
