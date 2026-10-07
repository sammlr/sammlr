import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
REPORT = (
    PROJECT_ROOT / "Dokumentation" / "Product Bible" / "roadmap"
    / "sprint-reports" / "S33-report.md"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def database_dump(path):
    with sqlite3.connect(path) as connection:
        return "\n".join(connection.iterdump())


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s33-bootstrap-")
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


class HttpIntegrityHardeningTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s33-")
        self.db_path = Path(self.temp_dir.name) / "s33.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(tuple(range(1, 12)), migrate(connection, 11))
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def login_as(self, user_id):
        with self.connection() as connection:
            auth_version = connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (user_id,)
            ).fetchone()[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id
            login_session["auth_version"] = auth_version

    def test_all_historical_mutating_gets_are_405_and_persist_nothing(self):
        before = database_dump(self.db_path)
        paths = (
            "/debug-seed-now",
            "/logout",
            "/favorit/toggle/vfl",
            "/favorit/setzen/vfl",
            "/alben/hinzufuegen/em24",
            "/add/vfl/3",
            "/remove/vfl/1",
            "/undo",
            "/notifications/1/open",
            "/notifications/1/read",
            "/trades/1/accept",
            "/trades/1/decline",
            "/trades/1/confirm",
            "/trades/1/cancel",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(405, self.client.get(path).status_code)
        self.assertEqual(before, database_dump(self.db_path))
        with self.client.session_transaction() as login_session:
            self.assertEqual(1, login_session["user_id"])

    def test_post_forms_replace_historical_mutating_links(self):
        favorite = self.client.get("/favorit?auswahl=1").get_data(as_text=True)
        albums = self.client.get("/alben/hinzufuegen").get_data(as_text=True)
        sticker = self.client.get("/sticker/vfl/1").get_data(as_text=True)
        account = self.client.get("/account").get_data(as_text=True)
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO notifications
                    (user_id, title, body, is_read, notification_type,
                     target_type, target_id, source_event_id, dedupe_key)
                VALUES (2, 'S33 Ziel', 'S33 Ziel', 0,
                        'trade_request_created', 'trade_request', 1,
                        33001, 's33-notification-form')
                """
            )
            connection.commit()
        self.login_as(2)
        notifications = self.client.post("/notifications").get_data(as_text=True)

        self.assertIn('method="POST" action="/favorit/toggle/vfl"', favorite)
        self.assertNotIn('href="/favorit/toggle/', favorite)
        self.assertIn('method="POST" action="/alben/hinzufuegen/em24"', albums)
        self.assertIn('method="POST" action="/add/vfl/1"', sticker)
        self.assertIn('method="POST" action="/remove/vfl/1"', sticker)
        self.assertIn('method="POST" action="/logout"', account)
        self.assertIn('method="POST" action="/notifications/', notifications)
        self.assertIn('/open"', notifications)
        self.assertNotIn('/read?page=', notifications)
        for html in (favorite, albums, sticker, account, notifications):
            self.assertIn('name="_csrf_token"', html)

    def test_inventory_post_uses_csrf_and_keeps_existing_behavior(self):
        with self.connection() as connection:
            before = connection.execute(
                "SELECT quantity, duplicates FROM stickers "
                "WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone()
        rejected = self.client.post(
            "/add/vfl/1", csrf_protect=False
        )
        self.assertEqual(403, rejected.status_code)
        with self.connection() as connection:
            unchanged = connection.execute(
                "SELECT quantity, duplicates FROM stickers "
                "WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone()
        self.assertEqual(tuple(before), tuple(unchanged))

        accepted = self.client.post("/add/vfl/1", data={"filter": "all"})
        self.assertEqual(302, accepted.status_code)
        with self.connection() as connection:
            changed = connection.execute(
                "SELECT quantity, duplicates FROM stickers "
                "WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone()
        self.assertEqual((before["quantity"] + 1, before["duplicates"] + 1), tuple(changed))

    def test_notification_post_is_scoped_and_retry_idempotent(self):
        with self.connection() as connection:
            notification_id = connection.execute(
                "SELECT id FROM notifications WHERE user_id=2 AND is_read=0 LIMIT 1"
            ).fetchone()[0]
        before = database_dump(self.db_path)
        foreign = self.client.post(f"/notifications/{notification_id}/read")
        self.assertEqual(302, foreign.status_code)
        self.assertEqual(before, database_dump(self.db_path))

        self.login_as(2)
        first = self.client.post(f"/notifications/{notification_id}/read")
        second = self.client.post(f"/notifications/{notification_id}/read")
        self.assertEqual(302, first.status_code)
        self.assertEqual(302, second.status_code)
        with self.connection() as connection:
            self.assertEqual(1, connection.execute(
                "SELECT is_read FROM notifications WHERE id=?", (notification_id,)
            ).fetchone()[0])

    def test_trophy_gets_are_persistently_read_only(self):
        before = database_dump(self.db_path)
        self.assertEqual(200, self.client.get("/album/vfl/trophaeen").status_code)
        self.assertEqual(200, self.client.get("/trophaeen").status_code)
        self.assertEqual(before, database_dump(self.db_path))

    def test_existing_inventory_mutation_does_not_revive_legacy_trophy_writer(self):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM unlocked_trophies "
                "WHERE user_id=1 AND album_id='vfl' AND trophy_name='Erster Sticker'"
            )
            connection.commit()
        self.client.post("/add/vfl/3")
        with self.connection() as connection:
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM unlocked_trophies "
                "WHERE user_id=1 AND album_id='vfl' AND trophy_name='Erster Sticker'"
                ).fetchone())

    def test_debug_routes_are_testing_only_and_seed_is_post_csrf(self):
        self.assertEqual(200, self.client.get("/debug-db").status_code)
        self.assertEqual(405, self.client.get("/debug-seed-now").status_code)
        self.assertEqual(
            403,
            self.client.post("/debug-seed-now", csrf_protect=False).status_code,
        )
        seed_copy = Path(self.temp_dir.name) / "debug-seed.db"
        shutil.copy2(self.db_path, seed_copy)
        with patch.object(webapp, "SEED_DB", str(seed_copy)):
            response = self.client.post("/debug-seed-now")
        self.assertEqual(302, response.status_code)
        self.assertTrue(response.headers["Location"].startswith("/debug-db"))

    def test_debug_routes_are_not_registered_in_production(self):
        production_db = Path(self.temp_dir.name) / "production.db"
        shutil.copy2(REFERENCE_FIXTURE, production_db)
        with sqlite3.connect(production_db) as connection:
            migrate(connection, 20)
        script = """
import sys
import os
from pathlib import Path
sys.path.insert(0, 'App')
import services.runtime_operations as runtime_operations
runtime_operations.PRODUCTION_DATABASE_PATH = Path(os.environ['DATABASE_PATH'])
import webapp
client = webapp.app.test_client()
print(client.get('/debug-db').status_code)
print(client.get('/debug-seed-now').status_code)
"""
        environment = os.environ.copy()
        environment.update({
            "SAMMLR_ENV": "production",
            "SAMMLR_SECRET_KEY": "s33-production-test-secret",
            "DATABASE_PATH": str(production_db),
            "PORT": "8000",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        status_lines = [
            line for line in result.stdout.strip().splitlines()
            if line.isdigit()
        ]
        self.assertEqual(["404", "404"], status_lines)

    def test_existing_post_domains_remain_post_only_and_csrf_protected(self):
        paths = (
            "/album/vfl/privacy",
            "/trades/1/rating",
            "/profil/freunde/anfragen/2",
            "/profil/fixture_user_2/block",
            "/trade/1/accept",
            "/trade/1/ship",
            "/trade/1/receive",
        )
        before = database_dump(self.db_path)
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(405, self.client.get(path).status_code)
                self.assertEqual(
                    403,
                    self.client.post(path, csrf_protect=False).status_code,
                )
        self.assertEqual(before, database_dump(self.db_path))

    def test_main_get_smoke_changes_no_persistent_state(self):
        before = database_dump(self.db_path)
        for path in (
            "/sammlung", "/album/vfl", "/album/vfl/liste",
            "/profil", "/profil/freunde", "/statistik",
            "/trophaeen", "/album/vfl/trophaeen",
        ):
            with self.subTest(path=path):
                self.assertEqual(200, self.client.get(path).status_code)
        self.assertEqual(before, database_dump(self.db_path))

    def test_v0011_forward_repeat_and_data_preserving_backout(self):
        self.assertEqual(24, load_migrations()[-1].version)
        with self.connection() as connection:
            self.assertEqual(11, current_version(connection))
            core_before = tuple(connection.execute(
                "SELECT user_id, album_id, sticker_code, quantity, duplicates "
                "FROM stickers ORDER BY id"
            ).fetchall())
            self.assertEqual((), migrate(connection, 11))
            objects = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE name LIKE 's33_%' OR name='idx_s33_stickers_identity'"
                )
            }
            self.assertEqual(11, len(objects))
            self.assertEqual((11,), rollback(connection, 10))
            self.assertEqual(10, current_version(connection))
            self.assertEqual(core_before, tuple(connection.execute(
                "SELECT user_id, album_id, sticker_code, quantity, duplicates "
                "FROM stickers ORDER BY id"
            ).fetchall()))
            self.assertFalse(connection.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE name LIKE 's33_%' OR name='idx_s33_stickers_identity'"
            ).fetchone())
            self.assertEqual((11,), migrate(connection, 11))

    def test_v0011_rejects_only_documented_invalid_states(self):
        with self.connection() as connection:
            invalid_statements = (
                (
                    "INSERT INTO stickers "
                    "(user_id, album_id, sticker_code, status, quantity, duplicates) "
                    "VALUES (1, 'vfl', 'S33-X', 'owned', 0, 0)",
                    (),
                ),
                (
                    "UPDATE stickers SET duplicates=99 WHERE id=(SELECT MIN(id) FROM stickers)",
                    (),
                ),
                (
                    "INSERT INTO user_albums (user_id, album_id) VALUES (99999, 'vfl')",
                    (),
                ),
                (
                    "UPDATE notifications SET is_read=2 WHERE id=(SELECT MIN(id) FROM notifications)",
                    (),
                ),
                (
                    "UPDATE trade_requests SET status='invented' "
                    "WHERE id=(SELECT MIN(id) FROM trade_requests)",
                    (),
                ),
                (
                    "UPDATE trade_requests SET to_user_id=from_user_id "
                    "WHERE id=(SELECT MIN(id) FROM trade_requests)",
                    (),
                ),
                (
                    "INSERT INTO unlocked_trophies (user_id, album_id, trophy_name) "
                    "VALUES (99999, 'vfl', 'Ungültig')",
                    (),
                ),
            )
            for statement, parameters in invalid_statements:
                with self.subTest(statement=statement):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(statement, parameters)
                    connection.rollback()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO stickers "
                    "(user_id, album_id, sticker_code, status, quantity, duplicates) "
                    "SELECT user_id, album_id, sticker_code, status, quantity, duplicates "
                    "FROM stickers LIMIT 1"
                )

    def test_report_contains_complete_exception_and_constraint_inventory(self):
        text = REPORT.read_text(encoding="utf-8")
        for value in (
            "CSRF-Token-Erzeugung", "session.pop", "Lazy-Fristnotification",
            "idx_s33_stickers_identity", "s33_stickers_validate_insert",
            "/debug-seed-now", "/notifications/<id>/open", "/trophaeen",
        ):
            self.assertIn(value, text)


if __name__ == "__main__":
    unittest.main()
