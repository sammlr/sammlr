import atexit
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
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# webapp initializes its configured database while being imported. Bootstrap
# that import against a disposable S00 copy, never against sammlr.db.
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s03-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class SideEffectSecurityGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s03-test-")
        self.test_db = Path(self.test_dir.name) / "side-effects.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S03 test.",
        )
        self.assertEqual(
            self.reference_hash_before,
            sha256(REFERENCE_FIXTURE),
            "The canonical S00 fixture changed during an isolated S03 test.",
        )
        self.test_dir.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            if user_id is not None:
                session["user_id"] = user_id

    def query_one(self, statement, parameters=()):
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(statement, parameters).fetchone()

    def query_all(self, statement, parameters=()):
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(statement, parameters).fetchall()

    def notification_count(self, user_id, title):
        return self.query_one(
            """
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE user_id=? AND title=?
            """,
            (user_id, title),
        )["count"]

    def create_request(self):
        self.login_as(1)
        count_before = self.query_one(
            "SELECT COUNT(*) AS count FROM trade_requests"
        )["count"]
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(
            count_before + 1,
            self.query_one(
                "SELECT COUNT(*) AS count FROM trade_requests"
            )["count"],
        )
        return self.query_one(
            "SELECT MAX(id) AS id FROM trade_requests"
        )["id"]

    def accept_request(self, trade_id):
        self.login_as(2)
        response = self.client.post(f"/trade/{trade_id}/accept")
        self.assertEqual(302, response.status_code)

    def test_each_test_starts_from_unchanged_s00_fixture(self):
        self.assertNotEqual(REFERENCE_FIXTURE, self.test_db)
        self.assertEqual(
            self.reference_hash_before,
            sha256(self.test_db),
        )
        self.assertEqual(
            1,
            self.query_one(
                "SELECT COUNT(*) AS count FROM trade_requests"
            )["count"],
        )
        self.assertEqual(
            1,
            self.query_one(
                "SELECT COUNT(*) AS count FROM unlocked_trophies"
            )["count"],
        )

    def test_legacy_album_trophy_writer_is_disabled(self):
        before = self.query_one(
            "SELECT COUNT(*) AS count FROM unlocked_trophies"
        )["count"]
        first_visible = webapp.record_trophy_unlocks(
            "vfl",
            ["S03 Visible", "S03 Visible", ""],
            user_id=1,
            silent_reached=["S03 Silent", "S03 Silent"],
        )
        second_visible = webapp.record_trophy_unlocks(
            "vfl",
            ["S03 Visible"],
            user_id=1,
            silent_reached=["S03 Silent"],
        )

        rows = self.query_all(
            """
            SELECT trophy_name
            FROM unlocked_trophies
            WHERE user_id=1
              AND album_id='vfl'
              AND trophy_name IN ('S03 Visible', 'S03 Silent')
            ORDER BY trophy_name
            """
        )
        self.assertEqual([], first_visible)
        self.assertEqual([], second_visible)
        self.assertEqual([], [row["trophy_name"] for row in rows])
        self.assertEqual(before, self.query_one(
            "SELECT COUNT(*) AS count FROM unlocked_trophies"
        )["count"])

    def test_global_trophy_legacy_path_is_absent(self):
        self.assertFalse(hasattr(webapp, "check_global_trophy_unlocks"))

    def test_popup_queue_deduplicates_titles_and_is_consumed_once(self):
        with webapp.app.test_request_context("/"):
            webapp.queue_trophy_popup(
                webapp.GLOBAL_SCOPE,
                ["S03 Popup", "S03 Popup", ""],
            )
            pending = webapp.session["pending_trophy_popups"]
            first_html = webapp.consume_trophy_popup_html()
            second_html = webapp.consume_trophy_popup_html()

        self.assertEqual(1, len(pending))
        self.assertEqual(["S03 Popup"], pending[0]["titles"])
        self.assertEqual(1, first_html.count("S03 Popup"))
        self.assertEqual("", second_html)

    def test_notification_adapter_is_unread_limited_and_user_scoped(self):
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            for index in range(3):
                connection.execute(
                    "INSERT INTO notifications (user_id, title, body, is_read) "
                    "VALUES (?, ?, ?, 0)",
                    (1, f"S03 Nachricht {index}", f"Synthetischer Inhalt {index}"),
                )
            connection.execute(
                "INSERT INTO notifications (user_id, title, body, is_read) "
                "VALUES (?, ?, ?, 0)",
                (2, "S03 Andere Person", "Nicht für Nutzer 1"),
            )
            connection.execute(
                """
                UPDATE notifications
                SET created_at=?
                WHERE user_id=1 AND title=?
                """,
                ("2026-07-29 10:00:00", "S03 Nachricht 0"),
            )
            connection.execute(
                """
                UPDATE notifications
                SET created_at=?
                WHERE user_id=1 AND title=?
                """,
                ("2026-07-29 11:00:00", "S03 Nachricht 1"),
            )
            connection.execute(
                """
                UPDATE notifications
                SET created_at=?
                WHERE user_id=1 AND title=?
                """,
                ("2026-07-29 12:00:00", "S03 Nachricht 2"),
            )
            connection.commit()
            unread = connection.execute(
                "SELECT * FROM notifications WHERE user_id=? AND is_read=0 "
                "ORDER BY created_at DESC LIMIT ?",
                (1, 2),
            ).fetchall()

        self.assertEqual(
            ["S03 Nachricht 2", "S03 Nachricht 1"],
            [row["title"] for row in unread],
        )
        self.assertTrue(all(row["user_id"] == 1 for row in unread))
        self.assertTrue(all(row["is_read"] == 0 for row in unread))

    def test_untyped_legacy_path_creates_no_new_request_or_acceptance_notification(self):
        trade_id = self.create_request()
        self.assertEqual(
            0,
            self.notification_count(2, "Neue Tauschanfrage"),
        )

        self.accept_request(trade_id)
        self.client.post(f"/trade/{trade_id}/accept")

        self.assertEqual(
            0,
            self.notification_count(1, "Tauschanfrage angenommen"),
        )

    def test_repeated_completion_creates_no_generic_completion_notification(self):
        trade_id = self.create_request()
        self.accept_request(trade_id)

        self.login_as(1)
        self.client.post(f"/trade/{trade_id}/confirm")
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/confirm")
        self.client.post(f"/trade/{trade_id}/confirm")
        self.login_as(1)
        self.client.post(f"/trade/{trade_id}/confirm")

        self.assertEqual(
            0,
            self.notification_count(1, "Tausch abgeschlossen"),
        )
        self.assertEqual(
            0,
            self.notification_count(2, "Tausch abgeschlossen"),
        )
        self.assertEqual(
            "completed",
            self.query_one(
                "SELECT status FROM trade_requests WHERE id=?",
                (trade_id,),
            )["status"],
        )

    def test_notification_read_route_is_scoped_to_current_user(self):
        self.assertEqual(
            0,
            self.query_one(
                "SELECT is_read FROM notifications WHERE id=2"
            )["is_read"],
        )

        self.login_as(1)
        self.client.post("/notifications/2/read")
        self.assertEqual(
            0,
            self.query_one(
                "SELECT is_read FROM notifications WHERE id=2"
            )["is_read"],
        )

        self.login_as(2)
        self.client.post("/notifications/2/read")
        self.assertEqual(
            1,
            self.query_one(
                "SELECT is_read FROM notifications WHERE id=2"
            )["is_read"],
        )

    def test_anonymous_domain_get_routes_redirect_to_login(self):
        self.login_as(None)
        routes = (
            "/",
            "/album/vfl",
            "/album/vfl/liste",
            "/trades",
            "/trade/1",
            "/trophaeen",
            "/profil",
        )

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(302, response.status_code)
                self.assertEqual("/login", response.headers["Location"])

    def test_anonymous_write_routes_redirect_without_side_effects(self):
        before_hash = sha256(self.test_db)
        self.login_as(None)
        requests = (
            ("post", "/add/vfl/1", None),
            ("post", "/remove/vfl/1", None),
            (
                "post",
                "/album/vfl/sticker/1/quantity",
                {"delta": "1"},
            ),
            (
                "post",
                "/album/vfl/liste/trade",
                {"give_codes": ["1"], "get_codes": ["3"]},
            ),
            (
                "post",
                "/album/vfl/trade/2/request",
                {"give_codes": ["1"], "get_codes": ["3"]},
            ),
            ("post", "/trade/1/confirm", None),
            ("post", "/notifications/2/read", None),
        )

        for method, route, data in requests:
            with self.subTest(method=method, route=route):
                response = self.client.open(route, method=method, data=data)
                self.assertEqual(302, response.status_code)
                self.assertEqual("/login", response.headers["Location"])

        self.assertEqual(before_hash, sha256(self.test_db))

    def test_public_login_and_register_routes_remain_available(self):
        self.login_as(None)

        login_response = self.client.get("/login")
        register_response = self.client.get("/register")

        self.assertEqual(200, login_response.status_code)
        self.assertEqual(200, register_response.status_code)
        self.assertIn("Einloggen", login_response.get_data(as_text=True))
        self.assertIn("Registrieren", register_response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
