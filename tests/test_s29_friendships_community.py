import atexit
from datetime import datetime, timedelta, timezone
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
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s29-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import (  # noqa: E402
    current_version,
    load_migrations,
    migrate,
    rollback,
)
from services.album_privacy import AlbumPrivacyService  # noqa: E402
from services.community import (  # noqa: E402
    CommunityMutationCode,
    CommunityService,
    UserActivityService,
)
from services.inventory import InventoryReadService  # noqa: E402
from services.smart_trade_requests import SMART_REQUEST_MARKER  # noqa: E402
from services.top_match_optimization import TopMatchOptimizationService  # noqa: E402
from services.trade_coverage import TradeCoverageService  # noqa: E402
from services.typed_notifications import TypedNotificationService  # noqa: E402


class FriendshipsCommunityTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s29-")
        self.test_db = Path(self.test_dir.name) / "community.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual(tuple(range(1, 10)), migrate(connection, 9))
            for table in (
                "user_activity", "blocks", "friendships",
                "friendship_requests", "trade_ratings",
                "trade_receipt_report_positions", "trade_receipt_reports",
                "trade_receipt_status", "trade_shipping_status",
                "trade_reservations", "trade_events", "trade_positions",
                "trades", "trade_requests", "notifications", "stickers",
                "user_albums",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.execute("UPDATE users SET username='valentin', name='Valentin' WHERE id=1")
            connection.execute("UPDATE users SET username='anna', name='Anna' WHERE id=2")
            connection.execute("UPDATE users SET username='mehmet', name='Mehmet' WHERE id=3")
            connection.execute("UPDATE users SET username='sofia', name='Sofia' WHERE id=4")
            connection.executemany(
                """INSERT INTO user_albums
                   (user_id, album_id, visibility, trade_pool_enabled)
                   VALUES (?, 'vfl', ?, 1)""",
                ((1, "private"), (2, "friends"), (3, "public"), (4, "public")),
            )
            connection.executemany(
                """INSERT INTO stickers
                   (user_id, album_id, sticker_code, status, duplicates, quantity)
                   VALUES (?, 'vfl', ?, 'owned', ?, ?)""",
                ((1, "1", 1, 2), (2, "2", 1, 2), (3, "3", 1, 2)),
            )
        webapp.DB = str(self.test_db)
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.test_db, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def test_v0009_migration_repeat_constraints_and_fail_closed_backout(self):
        migration_db = Path(self.test_dir.name) / "migration.db"
        shutil.copy2(REFERENCE_FIXTURE, migration_db)
        with self.connection(migration_db) as connection:
            self.assertEqual(tuple(range(1, 9)), migrate(connection, 8))
            self.assertEqual((9,), migrate(connection, 9))
            self.assertEqual(9, current_version(connection))
            self.assertEqual((), migrate(connection, 9))
            self.assertEqual(
                {"friendship_requests", "friendships", "blocks", "user_activity"},
                {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ) if row[0] in {
                        "friendship_requests", "friendships", "blocks", "user_activity"
                    }
                },
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """INSERT INTO friendship_requests
                       (requester_user_id, recipient_user_id, status)
                       VALUES (1, 2, 'removed')"""
                )
            self.assertEqual((9,), rollback(connection, 8))
            self.assertEqual((9,), migrate(connection, 9))
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (1, 2)"
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 8)
            self.assertEqual(9, current_version(connection))
        self.assertEqual(29, load_migrations()[-1].version)

    def test_request_notifies_recipient_but_accept_does_not_notify(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            sent = service.send_request(1, 2)
            self.assertEqual(CommunityMutationCode.CREATED, sent.code)
            self.assertFalse(AlbumPrivacyService(connection).can_view(1, 2, "vfl"))
            accepted = service.accept_request(sent.friendship_request_id, 2)
            self.assertEqual(CommunityMutationCode.ACCEPTED, accepted.code)
            self.assertTrue(service.are_friends(1, 2))
            self.assertTrue(service.are_friends(2, 1))
            self.assertTrue(AlbumPrivacyService(connection).can_view(1, 2, "vfl"))
            notifications = connection.execute(
                "SELECT * FROM notifications ORDER BY id"
            ).fetchall()
            self.assertEqual("friend_request", notifications[0]["notification_type"])
            self.assertEqual(sent.friendship_request_id, notifications[0]["source_event_id"])
            self.assertEqual(1, len(notifications))
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE notification_type='friend_accepted'"
            ).fetchone()[0])

    def test_cross_request_auto_accepts_without_acceptance_notifications(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            first = service.send_request(1, 2)
            crossed = service.send_request(2, 1)
            self.assertEqual(CommunityMutationCode.ACCEPTED, crossed.code)
            states = connection.execute(
                "SELECT status FROM friendship_requests ORDER BY id"
            ).fetchall()
            self.assertEqual(["accepted", "accepted"], [row[0] for row in states])
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM friendships").fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE notification_type='friend_request'"
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0])
            self.assertNotEqual(first.friendship_request_id, crossed.friendship_request_id)

    def test_decline_cancel_remove_and_permissions_are_strict(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            first = service.send_request(1, 2)
            rejected = service.accept_request(first.friendship_request_id, 3)
            self.assertFalse(rejected.changed)
            self.assertEqual(CommunityMutationCode.UNAUTHORIZED, rejected.code)
            self.assertEqual(
                CommunityMutationCode.DECLINED,
                service.decline_request(first.friendship_request_id, 2).code,
            )
            second = service.send_request(1, 2)
            self.assertEqual(
                CommunityMutationCode.CANCELLED,
                service.cancel_request(second.friendship_request_id, 1).code,
            )
            third = service.send_request(1, 2)
            service.accept_request(third.friendship_request_id, 2)
            self.assertEqual(
                CommunityMutationCode.REMOVED,
                service.remove_friendship(2, 1).code,
            )
            self.assertFalse(service.are_friends(1, 2))
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM friendships").fetchone()[0])

    def test_block_cancels_only_unaccepted_requests_preserves_running_trade_and_unblock_does_not_restore(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            request = service.send_request(1, 2)
            service.accept_request(request.friendship_request_id, 2)
            manual = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', 'open')"""
            ).lastrowid
            smart = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes,
                    status, from_confirmed)
                   VALUES ('vfl', 2, 1, '[\"2\"]', '[\"1\"]', 'open', ?)""",
                (SMART_REQUEST_MARKER,),
            ).lastrowid
            running = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', 'accepted')"""
            ).lastrowid
            connection.commit()
            result = service.block(1, 2)
            self.assertEqual(CommunityMutationCode.BLOCKED, result.code)
            statuses = dict(connection.execute(
                "SELECT id, status FROM trade_requests WHERE id IN (?, ?, ?)",
                (manual, smart, running),
            ).fetchall())
            self.assertEqual("cancelled", statuses[manual])
            self.assertEqual("cancelled", statuses[smart])
            self.assertEqual("accepted", statuses[running])
            self.assertFalse(service.are_friends(1, 2))
            self.assertEqual(CommunityMutationCode.UNBLOCKED, service.unblock(1, 2).code)
            self.assertFalse(service.are_friends(1, 2))

    def test_block_is_bidirectional_for_search_coverage_topmatch_and_manual_route(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            service.block(2, 1)
            self.assertEqual((), service.search(1, "an"))
            inventory = InventoryReadService(connection)
            coverage = TradeCoverageService(inventory)
            personal = coverage.personal_trade_coverage(1, 2, "vfl", ("1", "2"))
            self.assertEqual(0, personal.effectively_available_count)
            result = TopMatchOptimizationService(inventory, coverage).optimize(
                1, "vfl", ("1", "2"), (2,)
            )
            self.assertEqual((), result.packages)
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["2"]},
        )
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM trade_requests").fetchone()[0])

    def test_activity_classes_friends_only_and_rejected_action_does_not_touch(self):
        now = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)
        with self.connection() as connection:
            activity = UserActivityService(connection, lambda: now)
            activity.touch(2)
            connection.commit()
            self.assertIsNone(activity.label_for(2, 1))
            sent = CommunityService(connection, lambda: now).send_request(1, 2)
            CommunityService(connection, lambda: now).accept_request(sent.friendship_request_id, 2)
            self.assertEqual("Heute aktiv", activity.label_for(2, 1))
            labels = (
                (timedelta(days=3), "Diese Woche aktiv"),
                (timedelta(days=12), "Kürzlich aktiv"),
                (timedelta(days=40), "Länger nicht aktiv"),
            )
            for age, expected in labels:
                connection.execute(
                    "UPDATE user_activity SET last_active_at=? WHERE user_id=2",
                    ((now - age).isoformat(),),
                )
                self.assertEqual(expected, activity.label_for(2, 1))
            connection.commit()
            before = connection.execute(
                "SELECT last_active_at FROM user_activity WHERE user_id=2"
            ).fetchone()[0]
            denied = CommunityService(connection, lambda: now).remove_friendship(3, 2)
            self.assertFalse(denied.changed)
            after = connection.execute(
                "SELECT last_active_at FROM user_activity WHERE user_id=2"
            ).fetchone()[0]
            self.assertEqual(before, after)

    def test_search_prefix_limit_sort_and_existing_friend_marker(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            sent = service.send_request(1, 2)
            service.accept_request(sent.friendship_request_id, 2)
            results = service.search(1, "A")
            self.assertEqual(["anna"], [item.username for item in results])
            self.assertTrue(results[0].already_friends)
            self.assertLessEqual(len(service.search(1, "", 99)), 20)

    def test_profile_hides_friend_ui_while_album_and_block_policy_remain_active(self):
        with self.connection() as connection:
            service = CommunityService(connection)
            sent = service.send_request(1, 2)
            service.accept_request(sent.friendship_request_id, 2)
        profile = self.client.get("/profil/anna")
        html = profile.get_data(as_text=True)
        self.assertEqual(200, profile.status_code)
        self.assertNotIn("Ihr seid befreundet", html)
        self.assertNotIn("Wie gut kann dieser Nutzer mir helfen?", html)
        self.assertNotIn("TopMatch öffnen", html)
        album = self.client.get("/profil/anna/album/vfl")
        self.assertEqual(200, album.status_code)
        with self.connection() as connection:
            CommunityService(connection).block(1, 2)
        blocked = self.client.get("/profil/anna").get_data(as_text=True)
        self.assertNotIn("Ihr seid befreundet", blocked)
        self.assertNotIn("VfL Osnabrück", blocked)

    def test_login_and_get_do_not_create_activity(self):
        self.login_as(3)
        self.client.get("/profil")
        self.client.get("/profil/freunde?q=an")
        with self.connection() as connection:
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM user_activity WHERE user_id=3"
            ).fetchone())


if __name__ == "__main__":
    unittest.main()
