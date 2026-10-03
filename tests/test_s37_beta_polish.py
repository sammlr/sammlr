import hashlib
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
STYLE = APP_DIR / "static" / "style.css"

sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BetaPolishTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        cls.css = STYLE.read_text(encoding="utf-8")
        webapp.app.config.update(
            TESTING=True,
            CSRF_ENABLED=False,
            TESTING_AUTH_VERSION_COMPAT=False,
        )

    @classmethod
    def tearDownClass(cls):
        webapp.app.config["CSRF_ENABLED"] = True
        webapp.app.config["TESTING_AUTH_VERSION_COMPAT"] = True
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s37-")
        self.db_path = Path(self.temp_dir.name) / "s37.db"
        shutil.copy2(FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 18)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def login_as(self, user_id):
        with self.connect() as connection:
            version = connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (user_id,)
            ).fetchone()[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id
            login_session["auth_version"] = version

    @staticmethod
    def navigation(html):
        match = re.search(r'<nav class="bottom-nav">(.*?)</nav>', html, re.DOTALL)
        return match.group(1) if match else ""

    def create_open_trade(self):
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', 'open')"""
            )
            return cursor.lastrowid

    def assert_three_target_navigation(self, html):
        nav = self.navigation(html)
        links = re.findall(r'href="([^"]+)"', nav)
        self.assertEqual(["/sammlung", "/", "/tauschen"], links)
        self.assertNotIn('/profil', nav)
        self.assertNotIn('/notifications', nav)

    def test_product_and_workflow_pages_keep_header_and_three_target_navigation(self):
        trade_id = self.create_open_trade()
        routes = (
            "/", "/sammlung", "/alben/hinzufuegen", "/album/vfl",
            "/album/vfl/statistik", "/sticker/vfl/1",
            "/trades", f"/trades/{trade_id}", "/notifications", "/profil",
            "/profil/freunde", "/profil/name", "/profil/username",
            "/profil/password", "/profil/datenexport",
        )
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(200, response.status_code, route)
            html = response.get_data(as_text=True)
            self.assertIn('class="app-header"', html, route)
            self.assertIn('method="POST" action="/notifications"', html, route)
            if route == "/profil":
                self.assertIn('class="app-header-action app-header-settings" href="/account"', html)
                self.assertNotIn('class="app-header-action app-header-profile"', html)
            else:
                self.assertIn('href="/profil"', html, route)
            self.assert_three_target_navigation(html)

        list_html = self.client.get("/album/vfl/liste").get_data(as_text=True)
        self.assertNotIn('class="app-header"', list_html)
        self.assertIn('class="sticker-list-logo"', list_html)
        self.assertIn('href="/album/vfl"', list_html)
        self.assert_three_target_navigation(list_html)

    def test_contextual_back_routes_remain_local_to_the_workflow(self):
        trade_id = self.create_open_trade()
        cases = {
            "/alben/hinzufuegen": 'href="/sammlung"',
            "/album/vfl/liste": 'href="/album/vfl"',
            "/album/vfl/statistik": 'href="/album/vfl"',
            "/sticker/vfl/1": 'href="/album/vfl"',
            f"/trades/{trade_id}?origin=trades": 'href="/trades?tab=requests"',
            "/profil/name": 'href="/profil"',
            "/profil/datenexport": 'href="/profil"',
        }
        for route, expected_link in cases.items():
            response = self.client.get(route)
            self.assertEqual(200, response.status_code, route)
            self.assertIn(expected_link, response.get_data(as_text=True), route)

    def test_empty_collection_and_empty_search_offer_clear_states(self):
        with self.connect() as connection:
            connection.execute("DELETE FROM user_albums WHERE user_id=1")
        collection = self.client.get("/sammlung").get_data(as_text=True)
        self.assertIn("Noch keine Alben.", collection)
        self.assertIn('href="/alben/hinzufuegen"', collection)

        search = self.client.get(
            "/profil/freunde?q=s37-no-such-collector"
        ).get_data(as_text=True)
        self.assertIn("Keine Suchergebnisse.", search)

    def test_redirect_feedback_is_visible_on_destination_pages(self):
        notification_html = self.client.get(
            "/notifications?message=Ziel%20nicht%20mehr%20verf%C3%BCgbar"
        ).get_data(as_text=True)
        self.assertIn("Ziel nicht mehr verfügbar", notification_html)
        self.assertIn("sammlr-feedback error", notification_html)

        friends_html = self.client.get(
            "/profil/freunde?message=Freundschaftsanfrage%20gesendet"
        ).get_data(as_text=True)
        self.assertIn("Freundschaftsanfrage gesendet", friends_html)
        self.assertIn("sammlr-feedback success", friends_html)

    def test_post_loading_guard_and_responsive_accessibility_contract(self):
        album_html = self.client.get("/album/vfl").get_data(as_text=True)
        self.assertIn("document.querySelectorAll('form')", album_html)
        self.assertIn("toUpperCase() !== 'POST'", album_html)
        self.assertIn("form.setAttribute('aria-busy', 'true')", album_html)
        self.assertIn("window.setTimeout(function()", album_html)
        self.assertIn("control.disabled = true", album_html)
        self.assertIn('form[aria-busy="true"]', self.css)
        self.assertIn("@media (max-width:430px)", self.css)
        self.assertIn("@media (max-width:390px)", self.css)
        self.assertIn("env(safe-area-inset-bottom)", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("min-width:44px", self.css)
        self.assertIn("min-height:44px", self.css)

    def test_read_only_polish_routes_do_not_change_inventory(self):
        with self.connect() as connection:
            before = connection.execute(
                "SELECT user_id, album_id, sticker_code, quantity FROM stickers ORDER BY id"
            ).fetchall()
        for route in (
            "/sammlung", "/alben/hinzufuegen", "/album/vfl/statistik",
            "/sticker/vfl/1", "/profil/freunde?q=fixture", "/profil/name",
        ):
            self.assertEqual(200, self.client.get(route).status_code, route)
        with self.connect() as connection:
            after = connection.execute(
                "SELECT user_id, album_id, sticker_code, quantity FROM stickers ORDER BY id"
            ).fetchall()
        self.assertEqual([tuple(row) for row in before], [tuple(row) for row in after])


if __name__ == "__main__":
    unittest.main()
