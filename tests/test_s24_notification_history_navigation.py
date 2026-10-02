import atexit
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s24-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.notification_history import (  # noqa: E402
    NOTIFICATION_PAGE_SIZE,
    NotificationHistoryService,
    NotificationOpenCode,
)
from services.typed_notifications import TypedNotificationService  # noqa: E402


class NotificationHistoryNavigationTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s24-")
        self.test_db = Path(self.test_dir.name) / "s24.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5, 6), migrate(connection, 6))
            connection.execute("DELETE FROM notifications")
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            if user_id is not None:
                session["user_id"] = user_id

    def add_legacy(self, user_id, title, *, is_read=0, created_at=None):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO notifications
                    (user_id, title, body, is_read, created_at)
                VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                """,
                (user_id, title, f"Text {title}", is_read, created_at),
            )
            return cursor.lastrowid

    def add_typed(
        self,
        user_id,
        notification_type,
        target_type,
        target_id,
        source_event_id,
        title="Typed",
        is_read=0,
        created_at=None,
    ):
        dedupe = f"{user_id}:{notification_type}:{source_event_id}"
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO notifications
                    (user_id, title, body, is_read, created_at,
                     notification_type, target_type, target_id,
                     source_event_id, dedupe_key)
                VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP),
                        ?, ?, ?, ?, ?)
                """,
                (
                    user_id, title, f"Text {title}", is_read, created_at,
                    notification_type, target_type, target_id,
                    source_event_id, dedupe,
                ),
            )
            return cursor.lastrowid

    def read_state(self, notification_id):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT is_read FROM notifications WHERE id=?",
                (notification_id,),
            ).fetchone()
            return row["is_read"]

    def notification_count(self):
        with self.connection() as connection:
            return connection.execute(
                "SELECT COUNT(*) AS count FROM notifications"
            ).fetchone()["count"]

    def create_manual_request(self):
        self.login_as(1)
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            return connection.execute(
                "SELECT MAX(id) AS id FROM trade_requests"
            ).fetchone()["id"]

    def test_empty_history_and_history_get_do_not_mark_read(self):
        response = self.client.get("/notifications")
        self.assertEqual(200, response.status_code)
        self.assertIn("Inbox wird geöffnet", response.get_data(as_text=True))

        response = self.client.post("/notifications")
        self.assertIn("Noch keine Benachrichtigungen", response.get_data(as_text=True))

        unread_id = self.add_legacy(1, "Bleibt ungelesen")
        read_id = self.add_legacy(1, "Bleibt gelesen", is_read=1)
        response = self.client.get("/notifications")
        html = response.get_data(as_text=True)
        self.assertNotIn("Bleibt ungelesen", html)
        self.assertEqual(0, self.read_state(unread_id))
        self.assertEqual(1, self.read_state(read_id))

    def test_less_than_and_exactly_twenty_five_use_one_page(self):
        self.assertEqual(25, NOTIFICATION_PAGE_SIZE)
        for index in range(24):
            self.add_legacy(1, f"N{index:02d}")
        html = self.client.post("/notifications").get_data(as_text=True)
        self.assertEqual(24, html.count('data-notification-id="'))
        self.assertIn("Seite 1 von 1", html)
        self.add_legacy(1, "N24")
        html = self.client.post("/notifications").get_data(as_text=True)
        self.assertEqual(25, html.count('data-notification-id="'))
        self.assertIn("Seite 1 von 1", html)

    def test_more_than_twenty_five_paginates_newest_first(self):
        ids = []
        for index in range(30):
            ids.append(self.add_legacy(
                1,
                f"N{index:02d}",
                created_at=f"2026-08-{index // 24 + 1:02d} {index % 24:02d}:00:00",
            ))
        first = self.client.post("/notifications?page=1").get_data(as_text=True)
        second = self.client.post("/notifications?page=2").get_data(as_text=True)
        first_ids = [int(value) for value in re.findall(
            r'data-notification-id="(\d+)"', first
        )]
        second_ids = [int(value) for value in re.findall(
            r'data-notification-id="(\d+)"', second
        )]
        self.assertEqual(list(reversed(ids))[:25], first_ids)
        self.assertEqual(list(reversed(ids))[25:], second_ids)
        self.assertIn('method="POST" action="/notifications?page=2"', first)
        self.assertIn('method="POST" action="/notifications?page=1"', second)

    def test_mixed_legacy_and_typed_share_one_history(self):
        legacy = self.add_legacy(1, "Legacy", created_at="2026-08-01 10:00:00")
        typed = self.add_typed(
            1, "trade_request_created", "trade_request", 1, 901,
            title="Typisiert", created_at="2026-08-02 10:00:00",
        )
        with self.connection() as connection:
            page = NotificationHistoryService(connection).page(1)
        self.assertEqual((typed, legacy), tuple(item.id for item in page.items))
        self.assertEqual((False, True), tuple(item.is_legacy for item in page.items))

    def test_badge_zero_one_ninety_nine_and_hundred(self):
        for amount, expected in ((0, None), (1, "1"), (99, "99"), (100, "99+")):
            with self.subTest(amount=amount):
                with self.connection() as connection:
                    connection.execute("DELETE FROM notifications")
                    connection.executemany(
                        "INSERT INTO notifications (user_id, title, body, is_read) VALUES (1, ?, '', 0)",
                        ((f"N{index}",) for index in range(amount)),
                    )
                html = self.client.get("/").get_data(as_text=True)
                match = re.search(
                    r'<span class="notification-badge"[^>]*>([^<]+)</span>', html
                )
                if expected is None:
                    self.assertIsNone(match)
                else:
                    self.assertEqual(expected, match.group(1))

    def test_badge_counts_legacy_and_typed_but_not_read(self):
        self.add_legacy(1, "Legacy ungelesen")
        self.add_legacy(1, "Legacy gelesen", is_read=1)
        self.add_typed(1, "trade_request_created", "trade_request", 1, 902)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('>2</span>', html)

    def test_request_notification_click_reads_and_opens_with_origin(self):
        request_id = self.create_manual_request()
        self.login_as(2)
        with self.connection() as connection:
            notification = connection.execute(
                "SELECT * FROM notifications WHERE notification_type='trade_request_created'"
            ).fetchone()
        response = self.client.post(f"/notifications/{notification['id']}/open")
        self.assertEqual(302, response.status_code)
        self.assertEqual(
            f"/trades/{request_id}?origin=notifications",
            response.headers["Location"],
        )
        self.assertEqual(1, self.read_state(notification["id"]))
        detail = self.client.get(response.headers["Location"]).get_data(as_text=True)
        self.assertIn(
            '<a class="sticker-list-back" href="/notifications">← zurück zu Benachrichtigungen</a>',
            detail,
        )

    def test_lifecycle_notification_click_uses_canonical_trade_target(self):
        request_id = self.create_manual_request()
        self.login_as(2)
        self.client.post(f"/trade/{request_id}/accept")
        self.login_as(1)
        self.client.post(f"/trade/{request_id}/ship")
        self.login_as(2)
        with self.connection() as connection:
            notification = connection.execute(
                "SELECT * FROM notifications WHERE notification_type='trade_shipped'"
            ).fetchone()
            self.assertEqual("trade", notification["target_type"])
        response = self.client.post(f"/notifications/{notification['id']}/open")
        self.assertEqual(
            f"/trades/{request_id}?origin=notifications",
            response.headers["Location"],
        )

    def test_existing_origin_contexts_remain_unchanged(self):
        home = self.client.get("/trades/1?origin=home").get_data(as_text=True)
        trades = self.client.get("/trades/1?origin=trades").get_data(as_text=True)
        album = self.client.get("/trades/1?origin=album_trades").get_data(as_text=True)
        self.assertIn('href="/">← zurück zu Home</a>', home)
        self.assertIn('href="/trades?tab=requests">← zurück zu Tauschbörse</a>', trades)
        self.assertIn('href="/album/vfl/trades?tab=requests">← zurück zu Album-Tauschbörse</a>', album)

    def test_unknown_target_stays_visible_not_clickable_and_can_be_read(self):
        notification_id = self.add_typed(
            1, "trade_accepted", "trade", 999999, 903,
            title="Ziel weg",
        )
        html = self.client.post("/notifications").get_data(as_text=True)
        self.assertIn("Ziel weg", html)
        self.assertIn("Ziel nicht mehr verfügbar", html)
        self.assertNotIn(f'/notifications/{notification_id}/open', html)
        response = self.client.post(f"/notifications/{notification_id}/read")
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, self.read_state(notification_id))

    def test_unauthorized_target_discloses_no_target_and_page_marks_delivered_read(self):
        notification_id = self.add_typed(
            3, "trade_request_created", "trade_request", 1, 904,
            title="Neutraler Hinweis",
        )
        self.login_as(3)
        html = self.client.post("/notifications").get_data(as_text=True)
        self.assertIn("Neutraler Hinweis", html)
        self.assertIn("Ziel nicht mehr verfügbar", html)
        self.assertNotIn("fixture_user_1", html)
        self.assertNotIn("fixture_user_2", html)
        response = self.client.post(f"/notifications/{notification_id}/open")
        self.assertEqual("/notifications?message=Ziel%20nicht%20mehr%20verf%C3%BCgbar", response.headers["Location"])
        self.assertEqual(1, self.read_state(notification_id))

    def test_click_retry_is_idempotent_and_changes_no_domain_state(self):
        request_id = self.create_manual_request()
        self.login_as(2)
        with self.connection() as connection:
            notification = connection.execute(
                "SELECT * FROM notifications WHERE notification_type='trade_request_created'"
            ).fetchone()
            trade_before = tuple(connection.execute(
                "SELECT * FROM trade_requests WHERE id=?", (request_id,)
            ).fetchone())
        first = self.client.post(f"/notifications/{notification['id']}/open")
        second = self.client.post(f"/notifications/{notification['id']}/open")
        self.assertEqual(first.headers["Location"], second.headers["Location"])
        self.assertEqual(1, self.read_state(notification["id"]))
        with self.connection() as connection:
            trade_after = tuple(connection.execute(
                "SELECT * FROM trade_requests WHERE id=?", (request_id,)
            ).fetchone())
        self.assertEqual(trade_before, trade_after)

    def test_foreign_notification_cannot_be_read_or_opened(self):
        notification_id = self.add_legacy(2, "Fremd")
        self.client.post(f"/notifications/{notification_id}/read")
        self.assertEqual(0, self.read_state(notification_id))
        response = self.client.post(f"/notifications/{notification_id}/open")
        self.assertTrue(response.headers["Location"].startswith("/notifications?message="))
        self.assertEqual(0, self.read_state(notification_id))

    def test_s23_dedupe_contract_is_unchanged(self):
        with self.connection() as connection:
            service = TypedNotificationService(connection)
            first = service.create(
                1, "trade_request_created", "Einmal", "Einmal",
                "trade_request", 1, source_event_id=905,
            )
            second = service.create(
                1, "trade_request_created", "Einmal", "Einmal",
                "trade_request", 1, source_event_id=905,
            )
            connection.commit()
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(1, self.notification_count())

    def test_service_dtos_are_immutable_and_no_migration_is_added(self):
        notification_id = self.add_legacy(1, "DTO")
        with self.connection() as connection:
            page = NotificationHistoryService(connection).page(1)
            result = NotificationHistoryService(connection).open_target(
                notification_id, 1
            )
            versions = tuple(row[0] for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall())
        with self.assertRaises(Exception):
            page.page = 2
        self.assertEqual(NotificationOpenCode.TARGET_UNAVAILABLE, result.code)
        self.assertEqual((1, 2, 3, 4, 5, 6), versions)


if __name__ == "__main__":
    unittest.main()
