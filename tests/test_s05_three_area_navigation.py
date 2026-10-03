import atexit
import hashlib
import os
from pathlib import Path
import re
import shutil
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s05-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class ThreeAreaNavigationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s05-test-")
        self.test_db = Path(self.test_dir.name) / "navigation.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S05 test.",
        )
        self.assertEqual(
            self.reference_hash_before,
            sha256(REFERENCE_FIXTURE),
            "The canonical S00 fixture changed during an isolated S05 test.",
        )
        self.test_dir.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            if user_id is not None:
                session["user_id"] = user_id

    def primary_nav(self, html):
        match = re.search(
            r'<nav class="bottom-nav">(.*?)</nav>',
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "Die primäre Bottom-Navigation fehlt.")
        return match.group(1)

    def nav_entries(self, html):
        nav = self.primary_nav(html)
        entries = []
        for match in re.finditer(
            r'<a class="([^"]+)" href="([^"]+)"[^>]*>(.*?)</a>',
            nav,
            flags=re.DOTALL,
        ):
            label_markup = re.sub(
                r"<svg\b.*?</svg>|<img\b[^>]*>",
                "",
                match.group(3),
                flags=re.DOTALL,
            )
            label_markup = re.sub(
                r'<span class="[^"]*(?:bottom-nav-icon|notification-badge)[^"]*".*?</span>',
                "",
                label_markup,
                flags=re.DOTALL,
            )
            label = re.sub(r"<[^>]+>", "", label_markup)
            entries.append(
                {
                    "classes": set(match.group(1).split()),
                    "href": match.group(2),
                    "label": re.sub(r"\s+", " ", label).strip(),
                }
            )
        return entries

    def assert_navigation(self, route, active_href):
        response = self.client.get(route)
        self.assertEqual(200, response.status_code, route)
        entries = self.nav_entries(response.get_data(as_text=True))
        self.assertEqual(
            ["/sammlung", "/", "/tauschen"],
            [entry["href"] for entry in entries],
        )
        self.assertEqual(
            ["Sammlung", "sammlr.", "Tauschen"],
            [entry["label"] for entry in entries],
        )
        self.assertEqual(
            [active_href],
            [entry["href"] for entry in entries if "active" in entry["classes"]],
        )

    def test_primary_navigation_has_three_ordered_targets_with_home_central(self):
        response = self.client.get("/")
        entries = self.nav_entries(response.get_data(as_text=True))

        self.assertEqual(3, len(entries))
        self.assertEqual(
            ["/sammlung", "/", "/tauschen"],
            [entry["href"] for entry in entries],
        )
        self.assertEqual(
            ["Sammlung", "sammlr.", "Tauschen"],
            [entry["label"] for entry in entries],
        )

    def test_home_has_only_home_active(self):
        self.assert_navigation("/", "/")

    def test_collection_has_only_collection_active(self):
        self.assert_navigation("/sammlung", "/sammlung")

    def test_trade_centre_has_only_trade_active(self):
        self.assert_navigation("/trades", "/tauschen")

    def test_collection_subpages_keep_collection_active(self):
        for route in (
            "/favorit",
            "/alben/hinzufuegen",
            "/album/vfl",
            "/album/vfl/statistik",
            "/album/vfl/trophaeen",
        ):
            with self.subTest(route=route):
                self.assert_navigation(route, "/sammlung")

    def test_trade_subpage_keeps_trade_active(self):
        self.assert_navigation("/album/vfl/trades", "/tauschen")

    def test_hierarchical_targets_are_not_rendered_as_primary_links(self):
        for route in ("/", "/sammlung", "/trades"):
            with self.subTest(route=route):
                entries = self.nav_entries(
                    self.client.get(route).get_data(as_text=True)
                )
                self.assertTrue(
                    {"/favorit", "/statistik", "/trophaeen", "/profil", "/notifications"}.isdisjoint(
                        entry["href"] for entry in entries
                    )
                )

    def test_profile_favorite_statistics_and_trophy_routes_remain_available(self):
        for route in ("/profil", "/favorit", "/statistik", "/trophaeen"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(200, response.status_code)
                self.assertEqual(3, len(self.nav_entries(response.get_data(as_text=True))))

        profile_html = self.client.get("/profil").get_data(as_text=True)
        self.assertIn('href="/sammlung"', profile_html)
        self.assertNotIn('href="/statistik"', profile_html)
        self.assertNotIn('href="/trophaeen"', profile_html)

    def test_existing_collection_icon_asset_is_reused(self):
        html = self.client.get("/").get_data(as_text=True)
        nav = self.primary_nav(html)

        self.assertIn('src="/static/Stickeralbum.svg"', nav)
        asset_response = self.client.get("/static/Stickeralbum.svg")
        self.assertEqual(200, asset_response.status_code)
        asset_response.close()

    def test_mobile_navigation_has_three_columns_safe_area_and_desktop_hides_it(self):
        css = STYLESHEET.read_text(encoding="utf-8")

        s31_css = css.split("/* S31 – global product workflows", 1)[1]
        self.assertRegex(
            s31_css,
            r"\.bottom-nav:not\(\.album-bottom-nav\)\s*\{[^}]*"
            r"grid-template-columns:repeat\(3,\s*minmax\(0,1fr\)\)",
        )
        self.assertIn("env(safe-area-inset-bottom)", s31_css)
        desktop_rule = re.search(
            r"@media\s*\(min-width:900px\).*?"
            r"\.bottom-nav:not\(\.album-bottom-nav\)\s*\{([^}]*)\}",
            s31_css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(desktop_rule)
        self.assertIn("display:none", desktop_rule.group(1))

    def test_navigation_gets_do_not_change_persistent_data(self):
        before_hash = sha256(self.test_db)

        for route in ("/", "/sammlung", "/trades", "/favorit", "/profil"):
            with self.subTest(route=route):
                self.assertEqual(200, self.client.get(route).status_code)

        self.assertEqual(before_hash, sha256(self.test_db))


if __name__ == "__main__":
    unittest.main()
