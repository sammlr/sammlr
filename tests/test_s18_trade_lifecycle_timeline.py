import atexit
from datetime import datetime, timezone
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
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s18-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.trade_receipt import TradeReceiptStatusDTO  # noqa: E402
from services.trade_shipping import TradeShippingStatusDTO  # noqa: E402


class TradeLifecycleTimelinePresentationTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s18-")
        self.test_db = Path(self.test_dir.name) / "timeline.db"
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

    def create_accepted_trade(self, give_codes=None, get_codes=None):
        give_codes = give_codes or ["1"]
        get_codes = get_codes or ["3"]
        with self.connection() as connection:
            connection.execute(
                "UPDATE stickers SET quantity=10, duplicates=9 "
                "WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            )
            connection.execute(
                "UPDATE stickers SET quantity=10, duplicates=9 "
                "WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'"
            )
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status, created_at)
                VALUES ('vfl', 1, 2, ?, ?, 'open', '2026-07-31 10:00:00')
                """,
                (json.dumps(give_codes), json.dumps(get_codes)),
            )
            trade_id = cursor.lastrowid
        self.login_as(2)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/accept").status_code)
        with self.connection() as connection:
            lifecycle_id = connection.execute(
                "SELECT id FROM trades WHERE legacy_trade_request_id=?", (trade_id,)
            ).fetchone()["id"]
            connection.execute(
                "UPDATE trade_reservations SET created_at='2026-07-31 11:00:00' "
                "WHERE trade_id=?",
                (lifecycle_id,),
            )
        return trade_id

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/ship").status_code)

    def receive_as(self, trade_id, user_id):
        self.login_as(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/receive").status_code)

    def detail(self, trade_id, user_id=2):
        self.login_as(user_id)
        response = self.client.get(f"/trades/{trade_id}")
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def test_timestamp_uses_berlin_summer_and_winter_time(self):
        self.assertEqual(
            "03.08.2026|20:18",
            webapp.format_sammlr_timestamp("2026-08-03 18:18:00"),
        )
        self.assertEqual(
            "03.01.2026|19:18",
            webapp.format_sammlr_timestamp("2026-01-03 18:18:00"),
        )

    def test_five_business_days_skip_weekend_without_persisting_deadline(self):
        due = webapp.add_business_days("2026-07-31 11:00:00")
        self.assertEqual("2026-08-07 11:00:00+00:00", str(due))

    def test_status_labels_and_chips_use_one_vocabulary(self):
        shipping = TradeShippingStatusDTO(1, 1, 1, 2, False, None, False, None)
        receipt = TradeReceiptStatusDTO(1, 1, 1, 2, False, None, False, None)
        self.assertEqual("Reserviert", webapp.trade_shipping_status_label(shipping, receipt))
        self.assertIn('trade-status-chip reserved', webapp.trade_status_chip("Reserviert"))
        self.assertIn('trade-status-chip shipping', webapp.trade_status_chip("Versand läuft"))
        self.assertIn('trade-status-chip problem', webapp.trade_status_chip("Problem offen"))
        self.assertIn('trade-status-chip partial', webapp.trade_status_chip("Teilweise erhalten"))
        self.assertIn('trade-status-chip completed', webapp.trade_status_chip("Abgeschlossen"))

    def test_open_request_detail_has_minimal_pending_timeline(self):
        with self.connection() as connection:
            trade_id = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status, created_at)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open',
                        '2026-08-03 18:18:00')
                """
            ).lastrowid
        html = self.detail(trade_id)
        self.assertIn("Trade Timeline", html)
        self.assertIn("Anfrage gesendet", html)
        self.assertIn("Anfrage angenommen", html)
        self.assertIn("Sticker reserviert", html)
        self.assertIn("03.08.2026", html)
        self.assertIn("20:18", html)
        self.assertIn('trade-status-chip open', html)

    def test_accepted_trade_shows_acceptance_reservation_and_both_shipping_sides(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        with self.connection() as connection:
            lifecycle_id = connection.execute(
                "SELECT id FROM trades WHERE legacy_trade_request_id=?", (trade_id,)
            ).fetchone()["id"]
            connection.execute(
                "UPDATE trade_shipping_status "
                "SET requester_shipped_at='2026-08-03 18:18:00' WHERE trade_id=?",
                (lifecycle_id,),
            )
        html = self.detail(trade_id, 2)
        self.assertIn("Anfrage angenommen", html)
        self.assertIn("Sticker reserviert", html)
        self.assertIn("Gegenseite versendet", html)
        self.assertIn("Eigener Versand bestätigt", html)
        self.assertIn("03.08.2026", html)
        self.assertIn("20:18", html)
        self.assertIn('trade-status-chip shipping', html)

    def test_partial_receipt_uses_partial_status_and_relation_specific_timeline(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 2)
        html = self.detail(trade_id, 2)
        self.assertIn('trade-status-chip partial', html)
        self.assertIn("Eigener Empfang bestätigt", html)
        self.assertIn("Gegenseite bestätigt", html)
        self.assertRegex(
            html,
            r'(?s)trade-timeline-item done[^>]*>.*?Eigener Empfang bestätigt',
        )

    def test_open_and_resolved_problem_are_integrated_in_timeline(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.login_as(2)
        with self.connection() as connection:
            position = connection.execute(
                """
                SELECT p.id FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=2
                """,
                (trade_id,),
            ).fetchone()
        self.client.post(
            f"/trade/{trade_id}/problem",
            data={f"received_{position['id']}": "0", f"problem_{position['id']}": "missing"},
        )
        open_html = self.detail(trade_id, 2)
        self.assertIn("Problem bei deiner Lieferung gemeldet", open_html)
        self.assertIn("Problem offen", open_html)
        self.assertIn('trade-status-chip problem', open_html)

        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        resolved_html = self.detail(trade_id, 2)
        self.assertIn("Problem gelöst", resolved_html)
        self.assertNotIn('trade-status-chip problem', resolved_html)

    def test_completed_timeline_and_archive_use_completed_timestamp(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        self.receive_as(trade_id, 2)
        with self.connection() as connection:
            connection.execute(
                "UPDATE trades SET completed_at='2026-08-03 18:18:00' "
                "WHERE legacy_trade_request_id=?",
                (trade_id,),
            )
        html = self.detail(trade_id, 2)
        self.assertIn("Trade abgeschlossen", html)
        self.assertIn('trade-status-chip completed', html)
        self.assertIn("03.08.2026", html)
        self.assertIn("20:18", html)
        archive = webapp.profile_trade_archive_html(2)
        self.assertIn("03.08.2026", archive)
        self.assertNotIn("31.07.2026", archive)

    def test_shipping_overdue_notice_uses_existing_acceptance_timestamp(self):
        shipping = TradeShippingStatusDTO(1, 1, 1, 2, False, None, False, None)
        receipt = TradeReceiptStatusDTO(1, 1, 1, 2, False, None, False, None)
        html = webapp.trade_attention_html(
            1,
            {"accepted_at": "2026-07-24 10:00:00"},
            shipping,
            receipt,
            now=datetime(2026, 8, 4, 12, tzinfo=timezone.utc),
        )
        self.assertIn("Versand steht noch aus", html)
        self.assertIn("Fällig seit", html)

    def test_receipt_attention_appears_at_fourteen_days_without_state_change(self):
        shipping = TradeShippingStatusDTO(
            1, 1, 1, 2, True, "2026-08-01 10:00:00",
            True, "2026-07-20 10:00:00",
        )
        receipt = TradeReceiptStatusDTO(1, 1, 1, 2, False, None, False, None)
        notice = webapp.trade_attention_html(
            1, None, shipping, receipt,
            now=datetime(2026, 8, 4, 12, tzinfo=timezone.utc),
        )
        self.assertIn("Empfang steht noch aus", notice)
        self.assertIn("Versendet vor 15 Tagen", notice)
        self.assertEqual(
            "",
            webapp.trade_attention_html(
                1, None,
                TradeShippingStatusDTO(
                    1, 1, 1, 2, True, "2026-08-01 10:00:00",
                    True, "2026-07-25 10:00:00",
                ),
                receipt,
                now=datetime(2026, 8, 4, 12, tzinfo=timezone.utc),
            ),
        )

    def test_trade_boards_show_unified_chip_and_due_attention(self):
        trade_id = self.create_accepted_trade()
        with self.connection() as connection:
            lifecycle_id = connection.execute(
                "SELECT id FROM trades WHERE legacy_trade_request_id=?", (trade_id,)
            ).fetchone()["id"]
            connection.execute(
                "UPDATE trade_reservations SET created_at='2026-07-20 10:00:00' "
                "WHERE trade_id=?",
                (lifecycle_id,),
            )
        self.login_as(1)
        global_board = self.client.get("/trades?tab=agreements").get_data(as_text=True)
        album_board = self.client.get("/album/vfl/trades?tab=agreements").get_data(as_text=True)
        for html in (global_board, album_board):
            self.assertIn('trade-status-chip reserved', html)
            self.assertIn("Versand steht noch aus", html)

    def test_legacy_completed_trade_remains_readable_without_fake_completion_time(self):
        html = self.detail(1, 2)
        self.assertIn("Trade Timeline", html)
        self.assertIn("Trade abgeschlossen", html)
        self.assertIn("Zeitpunkt nicht verfügbar", html)
        self.assertIn('trade-status-chip completed', html)

    def test_timeline_is_read_only_and_canonical_databases_remain_unchanged(self):
        before = sha256(self.test_db)
        trade_id = self.create_accepted_trade()
        after_setup = sha256(self.test_db)
        self.detail(trade_id)
        self.detail(trade_id, 1)
        self.assertEqual(after_setup, sha256(self.test_db))
        self.assertNotEqual(before, after_setup)
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
