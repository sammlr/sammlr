import atexit
import hashlib
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s23-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import (  # noqa: E402
    current_version,
    migrate,
    rollback,
)
from services.notification_history import NotificationHistoryService  # noqa: E402
from services.typed_notifications import (  # noqa: E402
    NOTIFICATION_TYPES,
    TypedNotificationService,
    typed_notification_schema_available,
)


class TypedNotificationsTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s23-")
        self.test_db = Path(self.test_dir.name) / "s23.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual(tuple(range(1, 9)), migrate(connection, 8))
            self._clear_domain(connection)
            connection.executemany(
                "INSERT OR IGNORE INTO user_albums (user_id, album_id) VALUES (?, 'vfl')",
                ((1,), (2,), (3,)),
            )
        self.set_inventory(1, {"1": 3})
        self.set_inventory(2, {"3": 3})
        webapp.DB = str(self.test_db)
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

    @staticmethod
    def _clear_domain(connection):
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

    def rows(self, statement, parameters=()):
        with self.connection() as connection:
            return connection.execute(statement, parameters).fetchall()

    def count(self, where="1=1", parameters=()):
        return self.row(
            f"SELECT COUNT(*) AS count FROM notifications WHERE {where}",
            parameters,
        )["count"]

    def notification(self, notification_type, user_id=None):
        statement = "SELECT * FROM notifications WHERE notification_type=?"
        parameters = [notification_type]
        if user_id is not None:
            statement += " AND user_id=?"
            parameters.append(user_id)
        statement += " ORDER BY id DESC LIMIT 1"
        return self.row(statement, tuple(parameters))

    def create_manual_request(self):
        self.login_as(1)
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        return self.row("SELECT MAX(id) AS id FROM trade_requests")["id"]

    def accept(self, trade_request_id):
        self.login_as(2)
        response = self.client.post(f"/trade/{trade_request_id}/accept")
        self.assertEqual(302, response.status_code)
        lifecycle = self.row(
            "SELECT * FROM trades WHERE legacy_trade_request_id=?",
            (trade_request_id,),
        )
        self.assertIsNotNone(lifecycle)
        return lifecycle["id"]

    def create_accepted_trade(self):
        request_id = self.create_manual_request()
        lifecycle_id = self.accept(request_id)
        return request_id, lifecycle_id

    def test_v0006_adds_fields_and_preserves_existing_rows_as_legacy(self):
        migration_db = Path(self.test_dir.name) / "migration.db"
        shutil.copy2(REFERENCE_FIXTURE, migration_db)
        with self.connection(migration_db) as connection:
            existing = connection.execute(
                "SELECT id, title, body, is_read, created_at FROM notifications ORDER BY id"
            ).fetchall()
            self.assertEqual((1, 2, 3, 4, 5, 6), migrate(connection, 6))
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(notifications)"
                ).fetchall()
            }
            migrated = connection.execute(
                "SELECT * FROM notifications ORDER BY id"
            ).fetchall()
            self.assertTrue({
                "notification_type", "target_type", "target_id",
                "source_event_id", "dedupe_key",
            }.issubset(columns))
            self.assertEqual(
                [tuple(row) for row in existing],
                [
                    (row["id"], row["title"], row["body"], row["is_read"], row["created_at"])
                    for row in migrated
                ],
            )
            self.assertTrue(all(row["notification_type"] == "legacy" for row in migrated))
            self.assertTrue(all(row["target_type"] is None for row in migrated))
            self.assertEqual((), migrate(connection, 6))

    def test_v0006_backout_preserves_legacy_and_is_fail_closed_for_typed_data(self):
        legacy_db = Path(self.test_dir.name) / "legacy-backout.db"
        shutil.copy2(REFERENCE_FIXTURE, legacy_db)
        with self.connection(legacy_db) as connection:
            migrate(connection, 6)
            before = connection.execute(
                "SELECT id, user_id, title, body, is_read, created_at FROM notifications ORDER BY id"
            ).fetchall()
            self.assertEqual((6,), rollback(connection, 5))
            self.assertEqual(5, current_version(connection))
            self.assertFalse(typed_notification_schema_available(connection))
            after = connection.execute(
                "SELECT id, user_id, title, body, is_read, created_at FROM notifications ORDER BY id"
            ).fetchall()
            self.assertEqual([tuple(row) for row in before], [tuple(row) for row in after])

        with self.connection() as connection:
            TypedNotificationService(connection).create(
                2, "trade_request_created", "x", "y",
                "trade_request", 1, source_event_id=1,
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 5)
            self.assertEqual(8, current_version(connection))
            self.assertTrue(typed_notification_schema_available(connection))

    def test_manual_request_is_typed_for_recipient_and_targets_request(self):
        request_id = self.create_manual_request()
        notification = self.notification("trade_request_created")
        self.assertEqual((2, "trade_request", request_id, request_id), (
            notification["user_id"], notification["target_type"],
            notification["target_id"], notification["source_event_id"],
        ))
        self.assertEqual(
            f"2:trade_request_created:{request_id}",
            notification["dedupe_key"],
        )

    def test_smart_request_has_distinct_type_and_request_target(self):
        page = self.client.get("/album/vfl/smart-trades").get_data(as_text=True)
        result_id = re.search(
            r'name="result_id" value="([0-9a-f]+)"', page
        ).group(1)
        response = self.client.post(
            "/album/vfl/smart-trades/2/request",
            data={"result_id": result_id},
        )
        self.assertEqual(302, response.status_code)
        trade = self.row("SELECT * FROM trade_requests ORDER BY id DESC LIMIT 1")
        notification = self.notification("smart_trade_request_created")
        self.assertEqual((2, "trade_request", trade["id"]), (
            notification["user_id"],
            notification["target_type"],
            notification["target_id"],
        ))
        self.assertEqual(0, self.count("notification_type='trade_request_created'"))

    def test_acceptance_creates_no_notification(self):
        request_id = self.create_manual_request()
        self.accept(request_id)
        self.client.post(f"/trade/{request_id}/accept")
        self.assertEqual(0, self.count("notification_type='trade_accepted'"))

    def test_both_shipping_sides_are_separate_and_retry_is_deduplicated(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        self.login_as(1)
        self.client.post(f"/trade/{request_id}/ship")
        self.client.post(f"/trade/{request_id}/ship")
        self.login_as(2)
        self.client.post(f"/trade/{request_id}/ship")
        self.client.post(f"/trade/{request_id}/ship")

        rows = self.rows(
            "SELECT * FROM notifications WHERE notification_type='trade_shipped' ORDER BY user_id"
        )
        self.assertEqual(2, len(rows))
        self.assertEqual([(1, lifecycle_id), (2, lifecycle_id)], [
            (row["user_id"], row["target_id"]) for row in rows
        ])
        self.assertEqual(2, len({row["source_event_id"] for row in rows}))
        self.assertEqual(
            2,
            self.row("SELECT COUNT(*) AS count FROM trade_events WHERE event_type='shipment_confirmed'")["count"],
        )

    def test_receipt_notifies_only_counterpart_when_rating_first_becomes_available(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        self.login_as(1)
        self.client.post(f"/trade/{request_id}/ship")
        self.login_as(2)
        self.client.post(f"/trade/{request_id}/ship")
        self.client.post(f"/trade/{request_id}/receive")
        self.client.post(f"/trade/{request_id}/receive")
        self.login_as(1)
        self.client.post(f"/trade/{request_id}/receive")
        self.client.post(f"/trade/{request_id}/receive")

        self.assertEqual(0, self.count("notification_type='trade_received'"))
        rows = self.rows(
            "SELECT * FROM notifications WHERE notification_type='trade_rating_available'"
        )
        self.assertEqual(1, len(rows))
        self.assertEqual((2, "trade", lifecycle_id, lifecycle_id), (
            rows[0]["user_id"], rows[0]["target_type"],
            rows[0]["target_id"], rows[0]["source_event_id"],
        ))

    def test_overdue_state_creates_no_notifications(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        with self.connection() as connection:
            connection.execute(
                "UPDATE trade_reservations SET created_at='2026-07-01 10:00:00' WHERE trade_id=?",
                (lifecycle_id,),
            )
            connection.execute(
                """
                UPDATE trade_shipping_status
                SET partner_shipped=1,
                    partner_shipped_at='2026-07-01 10:00:00'
                WHERE trade_id=?
                """,
                (lifecycle_id,),
            )
        self.login_as(1)
        self.client.get("/trades")
        self.client.get(f"/trades/{request_id}")
        self.client.get("/notifications")
        self.assertEqual(0, self.count("notification_type LIKE '%overdue%'"))

    def test_read_entrypoints_never_write_notifications(self):
        request_id, lifecycle_id = self.create_accepted_trade()
        with self.connection() as connection:
            connection.execute(
                "UPDATE trade_reservations SET created_at='2026-07-01 10:00:00' WHERE trade_id=?",
                (lifecycle_id,),
            )
        self.login_as(1)
        self.client.get("/trades")
        self.client.get(f"/trades/{request_id}")
        self.client.get("/notifications")
        before = self.count()
        self.client.get("/trades")
        self.client.get(f"/trades/{request_id}")
        self.client.get("/notifications")
        self.assertEqual(before, self.count())
        types = {
            row["notification_type"]
            for row in self.rows("SELECT notification_type FROM notifications")
        }
        self.assertNotIn("smart_trade_request_expired", types)
        self.assertTrue(types.issubset(NOTIFICATION_TYPES | {"legacy"}))

    def test_parallel_creation_uses_unique_dedupe_key(self):
        barrier = threading.Barrier(3)
        results = []
        errors = []

        def worker():
            try:
                with self.connection() as connection:
                    barrier.wait()
                    result = TypedNotificationService(connection).create(
                        2,
                        "trade_request_created",
                        "Parallel",
                        "Parallel",
                        "trade_request",
                        77,
                        source_event_id=77,
                    )
                    results.append(result.created)
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        self.assertEqual([False, True], sorted(results))
        self.assertEqual(
            1,
            self.count("dedupe_key='2:trade_request_created:77'"),
        )

    def test_target_resolution_is_recipient_and_object_authorized(self):
        request_id = self.create_manual_request()
        with self.connection() as connection:
            service = TypedNotificationService(connection)
            dto = service.from_row(connection.execute(
                "SELECT * FROM notifications WHERE notification_type='trade_request_created'"
            ).fetchone())
            self.assertEqual(f"/trades/{request_id}", service.target_path_for(dto, 2))
            self.assertIsNone(service.target_path_for(dto, 1))
            self.assertIsNone(service.target_path_for(dto, 3))

        lifecycle_id = self.accept(request_id)
        self.login_as(1)
        self.client.post(f"/trade/{request_id}/ship")
        with self.connection() as connection:
            service = TypedNotificationService(connection)
            dto = service.from_row(connection.execute(
                "SELECT * FROM notifications WHERE notification_type='trade_shipped'"
            ).fetchone())
            self.assertEqual(f"/trades/{request_id}", service.target_path_for(dto, 2))
            self.assertEqual(lifecycle_id, dto.target.target_id)
            self.assertIsNone(service.target_path_for(dto, 1))

    def test_legacy_notification_remains_readable_without_semantic_reconstruction(self):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO notifications (user_id, title, body, is_read) "
                "VALUES (1, 'Legacy bleibt', 'Alter Hinweis', 0)"
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM notifications WHERE title='Legacy bleibt'"
            ).fetchone()
            unread = NotificationHistoryService(connection).page(1).items
        self.assertEqual("legacy", row["notification_type"])
        self.assertIsNone(row["target_type"])
        self.assertIsNone(row["target_id"])
        self.assertIsNone(row["source_event_id"])
        self.assertIsNone(row["dedupe_key"])
        self.assertIn("Legacy bleibt", [item.title for item in unread])
        body = self.client.post("/notifications").get_data(as_text=True)
        self.assertIn("Legacy bleibt", body)

    def test_only_frozen_cb008_catalog_is_supported(self):
        self.assertEqual({
            "trade_request_created", "smart_trade_request_created",
            "trade_request_declined", "trade_shipped",
            "trade_rating_available", "friend_request",
            "trade_request_unfulfillable", "trade_problem_action_required",
            "trade_problem_terminal",
            "lifecycle_addresses_released", "lifecycle_direction_sent", "lifecycle_receipt_update",
        }, set(NOTIFICATION_TYPES))
        with self.connection() as connection:
            for rejected_type in (
                "trade_accepted", "trade_received", "trade_completed",
                "friend_accepted", "trade_shipping_overdue",
                "trade_receipt_overdue", "problem_reported",
            ):
                with self.assertRaises(ValueError):
                    TypedNotificationService(connection).create(
                        1, rejected_type, "x", "y", "trade", 1,
                        source_event_id=1,
                    )


if __name__ == "__main__":
    unittest.main()
