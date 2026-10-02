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
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"
STYLESHEET = APP_DIR / "static" / "style.css"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s06-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class GlobalHeaderShellTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s06-test-")
        self.test_db = Path(self.test_dir.name) / "header.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S06 test.",
        )
        self.assertEqual(
            self.reference_hash_before,
            sha256(REFERENCE_FIXTURE),
            "The canonical S00 fixture changed during an isolated S06 test.",
        )
        self.test_dir.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            if user_id is not None:
                session["user_id"] = user_id

    def execute(self, statement, parameters=()):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(statement, parameters)
            connection.commit()

    def create_notification(self, user_id, title, body, is_read=0):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(
                """
                INSERT INTO notifications (user_id, title, body, is_read)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, title, body, is_read),
            )
            connection.commit()

    def header(self, html):
        match = re.search(
            r'<header class="app-header">(.*?)</header>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "Der globale App-Header fehlt.")
        return match.group(1)

    def test_main_areas_share_profile_and_notification_header_access(self):
        for route in ("/", "/sammlung", "/trades"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(200, response.status_code)
                header = self.header(response.get_data(as_text=True))
                self.assertIn('class="app-header-brand" href="/"', header)
                self.assertIn('method="POST" action="/notifications"', header)
                self.assertIn('href="/profil"', header)
                self.assertEqual(1, header.count('class="app-header-actions"'))

    def test_header_targets_open_existing_profile_and_notification_pages(self):
        profile = self.client.get("/profil")
        notifications = self.client.get("/notifications")

        self.assertEqual(200, profile.status_code)
        self.assertIn('aria-label="Sammlervitrine"', profile.get_data(as_text=True))
        self.assertEqual(200, notifications.status_code)
        self.assertIn("Benachrichtigungen", notifications.get_data(as_text=True))

    def test_deep_trade_workflow_keeps_header_and_existing_back_path(self):
        response = self.client.get("/album/vfl/trades")
        html = response.get_data(as_text=True)
        header = self.header(html)

        self.assertEqual(200, response.status_code)
        self.assertIn('method="POST" action="/notifications"', header)
        self.assertIn('href="/profil"', header)
        self.assertIn('href="/album/vfl">← Zurück</a>', html)
        self.assertIn('class="trade-tabs"', html)

    def test_avatar_uses_initial_fallback_without_profile_image_data(self):
        html = self.client.get("/").get_data(as_text=True)
        header = self.header(html)

        self.assertIn('<span class="app-header-avatar" aria-hidden="true">F</span>', header)
        profile_link = re.search(
            r'<a class="app-header-action app-header-profile".*?</a>',
            header,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(profile_link)
        self.assertNotIn("<img", profile_link.group(0))

        self.execute("UPDATE users SET name=NULL, username='' WHERE id=1")
        fallback_header = self.header(self.client.get("/").get_data(as_text=True))
        self.assertIn('<span class="app-header-avatar" aria-hidden="true">S</span>', fallback_header)

    def test_notification_header_is_a_shell_without_badge(self):
        header = self.header(self.client.get("/").get_data(as_text=True))

        self.assertIn('class="app-header-bell app-header-bell-svg"', header)
        self.assertNotIn("badge", header.lower())
        self.assertNotIn("notification-count", header.lower())

    def test_notification_page_has_honest_empty_state(self):
        self.execute("DELETE FROM notifications WHERE user_id=1")

        response = self.client.post("/notifications")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Noch keine Benachrichtigungen.", html)
        self.assertIn("Neue und gelesene Hinweise", html)

    def test_notification_page_shows_current_users_read_and_unread_inventory(self):
        self.execute("DELETE FROM notifications")
        self.create_notification(1, "S06 sichtbar", "Für Person 1")
        self.create_notification(1, "S06 gelesen", "Nicht mehr aktuell", is_read=1)
        self.create_notification(2, "S06 fremd", "Für Person 2")

        html = self.client.post("/notifications").get_data(as_text=True)

        self.assertIn("S06 sichtbar", html)
        self.assertIn("Für Person 1", html)
        self.assertIn("S06 gelesen", html)
        self.assertNotIn("S06 fremd", html)

    def test_notification_shell_read_does_not_change_persistent_data(self):
        before_hash = sha256(self.test_db)

        response = self.client.get("/notifications")

        self.assertEqual(200, response.status_code)
        self.assertEqual(before_hash, sha256(self.test_db))

    def test_login_and_register_headers_do_not_expose_private_actions(self):
        self.login_as(None)

        for route in ("/login", "/register"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(200, response.status_code)
                header = self.header(response.get_data(as_text=True))
                self.assertNotIn('href="/profil"', header)
                self.assertNotIn('href="/notifications"', header)

    def test_anonymous_header_targets_require_login(self):
        self.login_as(None)

        for route in ("/profil", "/notifications"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(302, response.status_code)
                self.assertEqual("/login", response.headers["Location"])

    def test_mobile_header_css_keeps_actions_and_brand_in_one_shell(self):
        css = STYLESHEET.read_text(encoding="utf-8")

        self.assertRegex(
            css,
            r"\.app-header-actions\s*\{[^}]*display:flex",
        )
        self.assertRegex(
            css,
            r"\.app-header-action\s*\{[^}]*width:44px;[^}]*height:44px",
        )
        mobile_header = re.search(
            r"@media\s*\(max-width:520px\)\s*\{\s*"
            r"\.app-header\s*\{([^}]*)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(mobile_header)
        self.assertIn("padding:12px 14px", mobile_header.group(1))
        self.assertIn("gap:10px", mobile_header.group(1))


if __name__ == "__main__":
    unittest.main()
