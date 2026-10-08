import atexit
from datetime import datetime, timezone
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
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb009-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.notification_history import (  # noqa: E402
    NOTIFICATION_PAGE_SIZE,
    NotificationHistoryService,
)
from services.typed_notifications import NOTIFICATION_TYPES  # noqa: E402


FROZEN_CB008_TYPES = {
    "trade_request_created", "smart_trade_request_created",
    "trade_request_declined", "trade_shipped", "trade_rating_available",
    "friend_request", "trade_request_unfulfillable",
    "trade_problem_action_required", "trade_problem_terminal",
}
FIXED_NOW = datetime(2026, 8, 19, 16, 0, 0, tzinfo=timezone.utc)


class CB009InboxReadRetentionTestCase(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb009-")
        self.db_path = Path(self.temp_dir.name) / "inbox.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            connection.execute("DELETE FROM notifications")
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            if user_id is not None:
                session["user_id"] = user_id

    def add_notification(
        self, user_id, title, *, is_read=0,
        created_at="2026-08-19 15:00:00", typed=False,
    ):
        with self.connection() as connection:
            if typed:
                cursor = connection.execute(
                    """
                    INSERT INTO notifications
                        (user_id, title, body, is_read, created_at,
                         notification_type, target_type, target_id,
                         source_event_id, dedupe_key)
                    VALUES (?, ?, '', ?, ?, 'trade_request_created',
                            'trade_request', 999999, ?, ?)
                    """,
                    (
                        user_id, title, is_read, created_at,
                        900000 + connection.execute(
                            "SELECT COUNT(*) FROM notifications"
                        ).fetchone()[0],
                        f"cb009:{user_id}:{title}",
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO notifications
                        (user_id, title, body, is_read, created_at)
                    VALUES (?, ?, '', ?, ?)
                    """,
                    (user_id, title, is_read, created_at),
                )
            return cursor.lastrowid

    def rows(self):
        with self.connection() as connection:
            return connection.execute(
                "SELECT id, user_id, title, is_read, created_at "
                "FROM notifications ORDER BY id"
            ).fetchall()

    def test_get_is_non_destructive_and_only_exposes_csrf_post_gate(self):
        notification_id = self.add_notification(1, "Noch ungelesen")
        before = [tuple(row) for row in self.rows()]

        response = self.client.get("/notifications?page=2")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertEqual(before, [tuple(row) for row in self.rows()])
        self.assertNotIn("Noch ungelesen", html)
        self.assertIn('method="POST" action="/notifications?page=2"', html)
        self.assertIn('name="_csrf_token"', html)
        self.assertEqual(0, next(
            row["is_read"] for row in self.rows() if row["id"] == notification_id
        ))

    def test_inbox_mutation_rejects_missing_csrf_without_changes(self):
        notification_id = self.add_notification(1, "Protected")

        response = self.client.post("/notifications", csrf_protect=False)

        self.assertEqual(403, response.status_code)
        self.assertEqual(0, next(
            row["is_read"] for row in self.rows() if row["id"] == notification_id
        ))

    def test_open_marks_only_delivered_page_and_recalculates_global_badge(self):
        own_ids = [
            self.add_notification(
                1, f"Own {index:02d}",
                created_at=f"2026-08-19 15:{index:02d}:00",
            )
            for index in range(30)
        ]
        foreign_id = self.add_notification(2, "Foreign")

        first = self.client.post("/notifications?page=1").get_data(as_text=True)
        with self.connection() as connection:
            state = dict(connection.execute(
                "SELECT id, is_read FROM notifications WHERE user_id=1"
            ).fetchall())
            foreign_state = connection.execute(
                "SELECT is_read FROM notifications WHERE id=?", (foreign_id,)
            ).fetchone()[0]

        delivered = set(list(reversed(own_ids))[:NOTIFICATION_PAGE_SIZE])
        self.assertEqual(delivered, {row_id for row_id, read in state.items() if read})
        self.assertEqual(0, foreign_state)
        self.assertIn('aria-label="5 ungelesene Benachrichtigungen">5</span>', first)
        self.assertNotIn("Als gelesen", first)
        self.assertIn('method="POST" action="/notifications?page=2"', first)

        second = self.client.post("/notifications?page=2").get_data(as_text=True)
        with self.connection() as connection:
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=1 AND is_read=0"
            ).fetchone()[0])
        self.assertNotIn("notification-badge", second)

    def test_retention_is_strictly_after_thirty_days_for_legacy_and_typed(self):
        old_legacy = self.add_notification(
            1, "Old legacy", is_read=1, created_at="2026-07-20 15:59:59"
        )
        old_typed = self.add_notification(
            1, "Old typed", is_read=1,
            created_at="2026-07-01 00:00:00", typed=True,
        )
        at_boundary = self.add_notification(
            1, "Boundary", is_read=1, created_at="2026-07-20 16:00:00"
        )
        inside = self.add_notification(
            1, "Inside", is_read=1, created_at="2026-07-20 16:00:01"
        )
        old_unread = self.add_notification(
            1, "Old unread", created_at="2025-01-01 00:00:00"
        )
        foreign_old = self.add_notification(
            2, "Foreign old", is_read=1, created_at="2025-01-01 00:00:00"
        )

        with self.connection() as connection:
            result = NotificationHistoryService(
                connection, now_provider=lambda: FIXED_NOW
            ).open_page(1)
        remaining = {row["id"]: row for row in self.rows()}

        self.assertEqual(2, result.retention_deleted)
        self.assertNotIn(old_legacy, remaining)
        self.assertNotIn(old_typed, remaining)
        self.assertIn(at_boundary, remaining)
        self.assertIn(inside, remaining)
        self.assertIn(old_unread, remaining)
        self.assertEqual(1, remaining[old_unread]["is_read"])
        self.assertIn(foreign_old, remaining)

        with self.connection() as connection:
            retry = NotificationHistoryService(
                connection, now_provider=lambda: FIXED_NOW
            ).open_page(1)
        self.assertEqual(1, retry.retention_deleted)
        self.assertNotIn(old_unread, {row["id"] for row in self.rows()})

    def test_retry_and_new_notification_after_open_are_safe(self):
        first_id = self.add_notification(1, "First")
        with self.connection() as connection:
            service = NotificationHistoryService(
                connection, now_provider=lambda: FIXED_NOW
            )
            first = service.open_page(1)
            retry = service.open_page(1)
        self.assertEqual(1, first.read_state_changed)
        self.assertEqual(0, retry.read_state_changed)

        new_id = self.add_notification(1, "Arrived later")
        state = {row["id"]: row["is_read"] for row in self.rows()}
        self.assertEqual(1, state[first_id])
        self.assertEqual(0, state[new_id])

    def test_no_migration_or_cb008_catalog_and_domain_sources_unchanged(self):
        self.add_notification(1, "Inbox only")
        with self.connection() as connection:
            before = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("feed_events", "user_activity", "trade_events")
            }
        self.client.post("/notifications")
        with self.connection() as connection:
            after = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("feed_events", "user_activity", "trade_events")
            }
            versions = tuple(row[0] for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ))

        self.assertEqual(before, after)
        self.assertEqual(tuple(range(1, 19)), versions)
        self.assertEqual(27, max(migration.version for migration in load_migrations()))
        self.assertEqual(FROZEN_CB008_TYPES | {"lifecycle_addresses_released"}, set(NOTIFICATION_TYPES))


if __name__ == "__main__":
    unittest.main()
