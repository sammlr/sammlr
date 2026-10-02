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
STYLESHEET = APP_DIR / "static" / "style.css"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif001-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class UIF001CollectionGoldenScreenTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        cls.css = STYLESHEET.read_text(encoding="utf-8")
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif001-")
        self.test_db = Path(self.test_dir.name) / "golden-screen.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def collection_html(self):
        response = self.client.get("/sammlung")
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def test_collection_is_the_only_uif001_golden_screen(self):
        collection = self.collection_html()
        home = self.client.get("/").get_data(as_text=True)
        trades = self.client.get("/trades").get_data(as_text=True)

        self.assertIn("uif-foundation uif-collection-page", collection)
        self.assertIn("<h1>Sammlung</h1>", collection)
        self.assertIn("Deine Alben und dein Fortschritt.", collection)
        self.assertIn("app-header-brand-word", collection)
        self.assertNotIn("uif-collection-page", home)
        self.assertNotIn("uif-collection-page", trades)
        self.assertIn("app-header-brand-word", home)
        self.assertIn("app-header-brand-word", trades)
        self.assertNotIn("sammlr_logo_header.png", home)

    def test_all_collection_functions_and_navigation_targets_remain_reachable(self):
        html = self.collection_html()

        self.assertIn('href="/album/vfl"', html)
        self.assertIn('href="/album/wm26"', html)
        self.assertIn('href="/alben/hinzufuegen"', html)
        self.assertIn('href="/favorit?auswahl=1"', html)
        self.assertIn('method="POST" action="/notifications"', html)
        self.assertIn('href="/profil"', html)
        self.assertIn('href="/sammlung" aria-current="page"', html)
        self.assertIn('href="/"', html)
        self.assertIn('href="/trades"', html)
        self.assertEqual(2, html.count("collection-album-card-shell"))

    def test_rendered_values_and_progress_keep_existing_product_semantics(self):
        html = self.collection_html()

        self.assertIn("3 von 250 Stickern", html)
        self.assertIn("<strong>2</strong><span>Doppelte</span>", html)
        self.assertIn("<strong>1</strong><span>fehlende verfügbar</span>", html)
        self.assertIn("2 von 992 Stickern", html)
        self.assertIn("<strong>Keine</strong><span>fehlenden erhältlich</span>", html)
        self.assertIn('role="progressbar"', html)
        self.assertIn('aria-valuemin="0" aria-valuemax="100"', html)

    def test_optional_meta_line_is_conservative_and_non_redundant(self):
        html = self.collection_html()

        self.assertIn(
            '<p class="collection-album-meta">2024/25</p>',
            html,
        )
        self.assertNotIn(
            '<p class="collection-album-meta">Germany</p>',
            html,
        )
        self.assertNotIn(
            '<p class="collection-album-meta">2026</p>',
            html,
        )

    def test_badge_uses_actual_unread_count(self):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(
                """
                INSERT INTO notifications (user_id, title, body, is_read)
                VALUES (1, 'UIF-001', 'Unread badge fixture', 0)
                """
            )
            connection.commit()

        html = self.collection_html()
        with sqlite3.connect(self.test_db) as connection:
            unread = connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=1 AND is_read=0"
            ).fetchone()[0]

        self.assertIn(
            f'aria-label="{unread} ungelesene Benachrichtigungen"',
            html,
        )

    def test_collection_get_is_read_only(self):
        before = sha256(self.test_db)
        self.collection_html()
        self.assertEqual(before, sha256(self.test_db))

    def test_foundation_tokens_responsive_contract_and_accessibility_are_scoped(self):
        required_tokens = (
            "--uif-color-page", "--uif-color-surface",
            "--uif-color-surface-secondary", "--uif-color-text",
            "--uif-color-text-secondary", "--uif-color-text-subtle",
            "--uif-color-border", "--uif-color-accent",
            "--uif-color-accent-soft", "--uif-radius-card",
            "--uif-radius-control", "--uif-radius-compact",
            "--uif-shadow-card", "--uif-space-page",
            "--uif-space-section", "--uif-space-card",
            "--uif-type-page-title", "--uif-type-section-title",
            "--uif-type-card-title", "--uif-type-stat",
        )
        for token in required_tokens:
            self.assertIn(token, self.css)

        self.assertIn(".uif-collection-page", self.css)
        self.assertRegex(self.css, r"@media \(max-width:430px\)")
        self.assertRegex(self.css, r"@media \(max-width:350px\)")
        self.assertIn("overflow-wrap:anywhere", self.css)
        self.assertIn("env(safe-area-inset-bottom)", self.css)
        self.assertIn("prefers-reduced-motion:reduce", self.css)
        self.assertIn(":focus-visible", self.css)

    def test_long_title_and_large_values_are_not_truncated_by_renderer(self):
        html = webapp.collection_album_card(
            {
                "id": "long",
                "name": "Eine außergewöhnlich lange internationale Albumsammlung",
                "season": "2024/25",
                "cover": "ALB",
            },
            12345,
            98765,
            67,
            18321,
            4321,
        )

        self.assertIn("Eine außergewöhnlich lange internationale Albumsammlung", html)
        self.assertIn("12345 von 18321 Stickern", html)
        self.assertIn("<strong>98765</strong><span>Doppelte</span>", html)
        self.assertIn("<strong>4321</strong><span>fehlende verfügbar</span>", html)
        self.assertNotIn("text-overflow", html)


if __name__ == "__main__":
    unittest.main()
