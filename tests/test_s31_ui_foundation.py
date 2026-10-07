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
STYLE_PATH = APP_DIR / "static" / "style.css"
WEBAPP_PATH = APP_DIR / "webapp.py"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
SCREEN_DIR = (
    PROJECT_ROOT / "Dokumentation" / "Product Bible" / "design-system" / "screens"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first, second):
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s31-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402


class UiFoundationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        cls.css = STYLE_PATH.read_text(encoding="utf-8")
        cls.s31_css = cls.css.split(
            "/* S31 – global product workflows on the S30 design foundation */", 1
        )[1]
        cls.source = WEBAPP_PATH.read_text(encoding="utf-8")
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s31-")
        self.test_db = Path(self.test_dir.name) / "ui-foundation.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with sqlite3.connect(self.test_db) as connection:
            self.assertEqual(tuple(range(1, 10)), migrate(connection, 9))
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    @staticmethod
    def navigation(html):
        match = re.search(r'<nav class="bottom-nav">(.*?)</nav>', html, re.DOTALL)
        return match.group(1) if match else ""

    def create_open_trade(self):
        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', 'open')"""
            )
            return cursor.lastrowid

    def test_all_productive_main_pages_use_global_s31_shell(self):
        trade_id = self.create_open_trade()
        routes = (
            "/", "/sammlung", "/favorit", "/alben/hinzufuegen",
            "/album/vfl", "/album/vfl/liste", "/album/vfl/trades",
            "/album/vfl/statistik", "/album/vfl/trophaeen",
            "/album/vfl/smart-trades", "/trades", f"/trades/{trade_id}",
            "/notifications", "/profil", "/profil/freunde",
            "/profil/freunde?q=fixture", "/statistik", "/trophaeen",
        )
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(200, response.status_code, route)
            self.assertIn("s31-product-page", response.get_data(as_text=True), route)
        self.assertNotIn("s31-product-page", self.client.get("/login").get_data(as_text=True))
        self.assertNotIn("s31-product-page", self.client.get("/register").get_data(as_text=True))

    def test_large_and_compact_headers_follow_page_contract(self):
        for route in (
            "/", "/sammlung", "/album/vfl", "/trades", "/notifications",
            "/profil", "/profil/freunde",
        ):
            html = self.client.get(route).get_data(as_text=True)
            self.assertIn("app-header-variant-compact", html, route)
        self.assertIn("--sammlr-header-large-height:calc(var(--sammlr-space-16)", self.s31_css)
        self.assertIn("--sammlr-header-compact-height:var(--sammlr-space-16)", self.s31_css)

    def test_three_target_navigation_has_central_home_and_correct_active_states(self):
        expected = ["/sammlung", "/", "/tauschen"]
        for route, active in (
            ("/", "/"), ("/sammlung", "/sammlung"),
            ("/trades", "/tauschen"),
        ):
            nav = self.navigation(self.client.get(route).get_data(as_text=True))
            entries = re.findall(r'<a class="([^"]+)" href="([^"]+)"[^>]*>', nav)
            self.assertEqual(expected, [href for _classes, href in entries])
            self.assertEqual(1, expected.index("/"))
            self.assertEqual(
                [active],
                [href for classes, href in entries if "active" in classes.split()],
            )
            self.assertEqual(1, nav.count('aria-current="page"'))
        for route in ("/notifications", "/profil"):
            html = self.client.get(route).get_data(as_text=True)
            nav = self.navigation(html)
            self.assertNotIn('href="/notifications"', nav)
            self.assertNotIn('href="/profil"', nav)
            self.assertEqual(0, nav.count('aria-current="page"'))
            self.assertIn('method="POST" action="/notifications"', html)
            if route == "/profil":
                self.assertIn('class="app-header-action app-header-settings" href="/account"', html)
                self.assertNotIn('class="app-header-action app-header-profile"', html)
            else:
                self.assertIn('class="app-header-action app-header-profile" href="/profil"', html)
        self.assertIn("grid-template-columns:repeat(3", self.s31_css)
        self.assertRegex(
            self.s31_css,
            r'\.bottom-nav-link\[href="/"\]\s*\{[^}]*transform:translateY',
        )

    def test_desktop_hides_bottom_navigation_and_mobile_safe_area_remains(self):
        self.assertIn("@media (max-width:430px)", self.s31_css)
        self.assertIn("@media (max-width:390px)", self.s31_css)
        self.assertIn("env(safe-area-inset-bottom)", self.s31_css)
        desktop = re.search(
            r"@media \(min-width:900px\)(.*?)@media",
            self.s31_css + "\n@media",
            re.DOTALL,
        )
        self.assertIsNotNone(desktop)
        self.assertRegex(desktop.group(1), r"bottom-nav[^}]+display:none")

    def test_focused_deal_and_paper_list_keep_context_and_global_navigation(self):
        trade_id = self.create_open_trade()
        trade_html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("app-workflow-header", trade_html)
        self.assertIn("app-header-variant-compact", trade_html)

        list_html = self.client.get("/album/vfl/liste").get_data(as_text=True)
        self.assertIn("app-workflow-header", list_html)
        self.assertNotIn("app-header-variant-compact", list_html)
        self.assertIn('class="sticker-list-logo"', list_html)

        for html in (trade_html, list_html):
            nav = self.navigation(html)
            self.assertEqual(1, nav.count('href="/sammlung"'))
            self.assertEqual(1, nav.count('href="/"'))
            self.assertEqual(1, nav.count('href="/tauschen"'))
            self.assertNotIn('href="/profil"', nav)
            self.assertNotIn('href="/notifications"', nav)
        self.assertIn(".s31-product-page .app-workflow-header", self.s31_css)

    def test_component_families_and_status_mapping_are_tokenized(self):
        for selector in (
            ".page-title", ".card", ".btn", "button[type=", "input:not",
            "dialog", ".trade-tabs", ".sticker-filter-row", ".trade-status-chip",
            ".operational-home-empty", ".wall", ".slot.missing",
        ):
            self.assertIn(selector, self.s31_css)
        for variant in (
            "reserved", "shipping", "partial", "problem", "problem-closed",
            "completed", "expired", "obsolete",
        ):
            self.assertIn(f"trade-status-chip.{variant}", self.s31_css)
        self.assertIn('"Trade mit Problem beendet": "problem-closed"', self.source)
        self.assertIn('"Abgelaufen": "expired"', self.source)
        self.assertIn('"Obsolet": "obsolete"', self.source)
        self.assertGreaterEqual(contrast("#9A3412", "#FFF7ED"), 4.5)

    def test_keyboard_touch_and_dialog_contract(self):
        self.assertIn(":focus-visible", self.s31_css)
        touch_rule = re.search(
            r"\.s31-product-page :where\(\.app-header-action.*?\)\{(.*?)\}",
            self.s31_css,
            re.DOTALL,
        )
        self.assertIsNotNone(touch_rule)
        self.assertIn("min-width:44px", touch_rule.group(1))
        self.assertIn("min-height:44px", touch_rule.group(1))
        self.assertIn("dialog::backdrop", self.s31_css)
        self.assertIn("s31CloseOverlaysOnEscape", self.source)
        self.assertIn("event.key !== 'Escape'", self.source)
        self.assertNotRegex(self.source, r"Escape.*preventDefault|preventDefault.*Escape")
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.s31_css)

    def test_global_ui_reads_do_not_mutate_core_domain_state(self):
        with sqlite3.connect(self.test_db) as connection:
            before = {
                table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in (
                    "stickers", "trade_requests", "trades", "trade_reservations",
                    "friendships", "friendship_requests", "blocks", "trade_ratings",
                )
            }
        for route in (
            "/sammlung", "/album/vfl", "/album/vfl/liste", "/trades",
            "/notifications", "/profil", "/profil/freunde?q=fixture",
        ):
            self.assertEqual(200, self.client.get(route).status_code, route)
        with sqlite3.connect(self.test_db) as connection:
            after = {
                table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in before
            }
        self.assertEqual(before, after)

    def test_s31_adds_no_migration_and_reuses_existing_icons(self):
        self.assertEqual(24, load_migrations()[-1].version)
        nav_source = self.source.split("def bottom_nav", 1)[1].split("@app.route", 1)[0]
        self.assertIn('/static/Stickeralbum.svg', nav_source)
        self.assertIn('bottom-nav-icon-sammlr', nav_source)
        self.assertIn('trade_icon_svg()', nav_source)
        self.assertIn('app-header-bell', self.source)
        self.assertNotIn("icon-library", nav_source.lower())

    def test_reference_screen_manifest_is_complete(self):
        expected = {
            "home-390.png", "sammlung-390.png", "album-390.png",
            "stickerwall-390.png", "trade-390.png",
            "notifications-390.png", "profil-390.png",
        }
        self.assertTrue(SCREEN_DIR.is_dir())
        self.assertEqual(expected, {path.name for path in SCREEN_DIR.glob("*.png")})
        for name in expected:
            self.assertGreater((SCREEN_DIR / name).stat().st_size, 1000, name)


if __name__ == "__main__":
    unittest.main()
