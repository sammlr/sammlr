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
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb008-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, load_migrations, migrate  # noqa: E402
from services.community import CommunityMutationCode, CommunityService  # noqa: E402
from services.smart_trade_requests import (  # noqa: E402
    SMART_REQUEST_MARKER,
    SmartTradeRequestCode,
    SmartTradeRequestService,
)
from services.trade_problems import (  # noqa: E402
    PartialReceiptInputDTO,
    TradeProblemCode,
    TradeProblemService,
)
from services.typed_notifications import (  # noqa: E402
    NOTIFICATION_TYPES,
    TypedNotificationService,
)


EXPECTED_TYPES = {
    "trade_request_created",
    "smart_trade_request_created",
    "trade_request_declined",
    "trade_shipped",
    "trade_rating_available",
    "friend_request",
    "trade_request_unfulfillable",
    "trade_problem_action_required",
    "trade_problem_terminal",
    "lifecycle_addresses_released", "lifecycle_direction_sent",
}


class CB008NotificationCatalogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb008-")
        self.db_path = Path(self.temp_dir.name) / "notifications.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            for table in (
                "sammlr_news", "feed_events", "trophy_unlock_history_context",
                "canonical_trophy_unlocks", "historical_album_progress_points",
                "historical_sticker_acquisitions", "historical_inventory_mutations",
                "historical_album_records", "trade_ratings",
                "trade_receipt_report_positions", "trade_receipt_reports",
                "trade_receipt_status", "trade_shipping_status",
                "trade_reservations", "trade_events", "trade_positions", "trades",
                "trade_requests", "notifications", "blocks", "friendships",
                "friendship_requests", "user_activity", "stickers",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.execute(
                "UPDATE users SET account_state='active', profile_privacy='public' "
                "WHERE id IN (1, 2, 3)"
            )
            for user_id in (1, 2, 3):
                connection.execute(
                    """
                    INSERT INTO user_albums
                        (user_id, album_id, visibility, trade_pool_enabled)
                    VALUES (?, 'vfl', 'public', 1)
                    ON CONFLICT(user_id, album_id) DO UPDATE SET
                        visibility='public', trade_pool_enabled=1
                    """,
                    (user_id,),
                )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, 'vfl', ?, 'owned', 2, 3)
                """,
                ((1, "1"), (2, "3")),
            )
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def rows(self, notification_type=None):
        with self.connection() as connection:
            if notification_type is None:
                return connection.execute(
                    "SELECT * FROM notifications ORDER BY id"
                ).fetchall()
            return connection.execute(
                "SELECT * FROM notifications WHERE notification_type=? ORDER BY id",
                (notification_type,),
            ).fetchall()

    def create_request(self, *, smart=False):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status, from_confirmed)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open', ?)
                """,
                (SMART_REQUEST_MARKER if smart else 0,),
            )
            return cursor.lastrowid

    def create_accepted_trade(self):
        request_id = self.create_request()
        self.login(2)
        self.assertEqual(302, self.client.post(f"/trade/{request_id}/accept").status_code)
        with self.connection() as connection:
            lifecycle_id = connection.execute(
                "SELECT id FROM trades WHERE legacy_trade_request_id=?",
                (request_id,),
            ).fetchone()[0]
        return request_id, lifecycle_id

    def ship(self, request_id, user_id):
        self.login(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{request_id}/ship").status_code)

    def receive(self, request_id, user_id):
        self.login(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{request_id}/receive").status_code)

    def incoming_position(self, request_id, receiver_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT position.* FROM trade_positions position
                JOIN trades trade ON trade.id=position.trade_id
                WHERE trade.legacy_trade_request_id=? AND position.to_user_id=?
                """,
                (request_id, receiver_id),
            ).fetchone()

    def report_problem(self, request_id, receiver_id=2):
        position = self.incoming_position(request_id, receiver_id)
        with self.connection() as connection:
            return TradeProblemService(connection).report(
                request_id,
                receiver_id,
                (PartialReceiptInputDTO(position["id"], 0, "missing"),),
            )

    def test_catalog_is_exact_and_no_cb008_migration_exists(self):
        self.assertEqual(EXPECTED_TYPES, set(NOTIFICATION_TYPES))
        self.assertEqual(18, current_version(self.connection()))
        self.assertEqual(28, load_migrations()[-1].version)
        with self.connection() as connection:
            for rejected in (
                "trade_accepted", "trade_received", "trade_completed",
                "friend_accepted", "trade_shipping_overdue",
                "trade_receipt_overdue", "problem_resolved",
            ):
                with self.assertRaises(ValueError):
                    TypedNotificationService(connection).create(
                        1, rejected, "x", "y", "trade", 1, 1
                    )

    def test_decline_notifies_only_original_sender_once(self):
        request_id = self.create_request()
        self.login(2)
        self.client.post(f"/trade/{request_id}/decline")
        self.client.post(f"/trade/{request_id}/decline")
        notes = self.rows("trade_request_declined")
        self.assertEqual(1, len(notes))
        self.assertEqual((1, request_id, request_id), (
            notes[0]["user_id"], notes[0]["target_id"], notes[0]["source_event_id"]
        ))

    def test_smart_obsolete_notifies_only_original_sender_once(self):
        request_id = self.create_request(smart=True)
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=2 AND album_id='vfl'"
            )
            first = SmartTradeRequestService(connection).inspect(request_id, 2)
            second = SmartTradeRequestService(connection).inspect(request_id, 2)
        self.assertEqual(SmartTradeRequestCode.OBSOLETE, first.code)
        self.assertEqual(SmartTradeRequestCode.OBSOLETE, second.code)
        notes = self.rows("trade_request_unfulfillable")
        self.assertEqual(1, len(notes))
        self.assertEqual((1, request_id), (notes[0]["user_id"], notes[0]["source_event_id"]))

    def test_manual_request_is_not_reinterpreted_as_unfulfillable(self):
        request_id = self.create_request()
        with self.connection() as connection:
            state = SmartTradeRequestService(connection).inspect(request_id, 1)
        self.assertEqual(SmartTradeRequestCode.NOT_SMART, state.code)
        self.assertEqual([], self.rows("trade_request_unfulfillable"))

    def test_shipping_notifies_only_counterpart_and_retry_deduplicates(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        self.ship(request_id, 1)
        self.ship(request_id, 1)
        notes = self.rows("trade_shipped")
        self.assertEqual(1, len(notes))
        self.assertEqual((2, lifecycle_id), (notes[0]["user_id"], notes[0]["target_id"]))
        self.assertEqual([], self.rows("trade_accepted"))

    def test_completion_notifies_only_counterpart_who_can_rate(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        self.ship(request_id, 1)
        self.ship(request_id, 2)
        self.receive(request_id, 2)
        self.receive(request_id, 1)
        self.receive(request_id, 1)
        notes = self.rows("trade_rating_available")
        self.assertEqual(1, len(notes))
        self.assertEqual((2, lifecycle_id, lifecycle_id), (
            notes[0]["user_id"], notes[0]["target_id"], notes[0]["source_event_id"]
        ))
        self.assertEqual([], self.rows("trade_received"))

    def test_problem_report_notifies_counterpart_once(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        self.ship(request_id, 1)
        first = self.report_problem(request_id)
        second = self.report_problem(request_id)
        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, first.code)
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, second.code)
        notes = self.rows("trade_problem_action_required")
        self.assertEqual(1, len(notes))
        self.assertEqual((1, lifecycle_id, first.report_id), (
            notes[0]["user_id"], notes[0]["target_id"], notes[0]["source_event_id"]
        ))

    def test_terminal_problem_and_rating_are_once_but_late_resolution_is_silent(self):
        request_id, _ = self.create_accepted_trade()
        self.ship(request_id, 1)
        report = self.report_problem(request_id)
        with self.connection() as connection:
            service = TradeProblemService(connection)
            first = service.close_with_problem(request_id, 2)
            retry = service.close_with_problem(request_id, 2)
            before_late_resolution = connection.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0]
            resolved = service.resolve(request_id, 2)
            after_late_resolution = connection.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0]
        self.assertEqual(TradeProblemCode.CLOSED_WITH_PROBLEM, first.code)
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, retry.code)
        self.assertEqual(TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE, resolved.code)
        self.assertEqual(before_late_resolution, after_late_resolution)
        terminal = self.rows("trade_problem_terminal")
        rating = self.rows("trade_rating_available")
        self.assertEqual(1, len(terminal))
        self.assertEqual(1, len(rating))
        self.assertEqual(1, terminal[0]["user_id"])
        self.assertEqual(report.report_id, terminal[0]["source_event_id"])
        self.assertEqual(1, rating[0]["user_id"])

    def test_notification_failure_rolls_back_problem_fact_and_event(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        self.ship(request_id, 1)
        position = self.incoming_position(request_id, 2)
        with patch.object(
            TypedNotificationService,
            "notify_problem_action_required",
            side_effect=RuntimeError("projection failed"),
        ):
            with self.connection() as connection:
                result = TradeProblemService(connection).report(
                    request_id,
                    2,
                    (PartialReceiptInputDTO(position["id"], 0, "missing"),),
                )
        self.assertEqual(TradeProblemCode.TRANSACTION_ERROR, result.code)
        with self.connection() as connection:
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM trade_receipt_reports WHERE trade_id=?",
                (lifecycle_id,),
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM trade_events WHERE trade_id=? AND event_type='problem_reported'",
                (lifecycle_id,),
            ).fetchone()[0])
        self.assertEqual([], self.rows("trade_problem_action_required"))

    def test_friend_request_is_once_and_acceptance_is_silent(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            sent = service.send_request(1, 2)
            retry = service.send_request(1, 2)
            accepted = service.accept_request(sent.friendship_request_id, 2)
        self.assertEqual(CommunityMutationCode.CREATED, sent.code)
        self.assertEqual(CommunityMutationCode.ALREADY_EXISTS, retry.code)
        self.assertEqual(CommunityMutationCode.ACCEPTED, accepted.code)
        notes = self.rows()
        self.assertEqual(1, len(notes))
        self.assertEqual((2, "friend_request", sent.friendship_request_id), (
            notes[0]["user_id"], notes[0]["notification_type"], notes[0]["source_event_id"]
        ))

    def test_source_ids_are_mandatory_and_feed_is_not_a_notification_source(self):
        with self.connection() as connection:
            with self.assertRaises(ValueError):
                TypedNotificationService(connection).create(
                    2, "trade_request_created", "x", "y", "trade_request", 1
                )
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM feed_events"
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
