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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s30-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402


class DesignFoundationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        cls.css = STYLE_PATH.read_text(encoding="utf-8")
        cls.source = WEBAPP_PATH.read_text(encoding="utf-8")
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s30-")
        self.test_db = Path(self.test_dir.name) / "design-foundation.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with sqlite3.connect(self.test_db) as connection:
            self.assertEqual(tuple(range(1, 10)), migrate(connection, 9))
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def token(self, name):
        match = re.search(rf"--{re.escape(name)}\s*:\s*([^;]+);", self.css)
        self.assertIsNotNone(match, name)
        return match.group(1).strip()

    def test_typography_spacing_radius_and_shadow_contract(self):
        expected = {
            "sammlr-type-display-size": "40px",
            "sammlr-type-display-weight": "700",
            "sammlr-type-display-line": "1.1",
            "sammlr-type-h1-size": "32px",
            "sammlr-type-h1-weight": "700",
            "sammlr-type-h1-line": "1.2",
            "sammlr-type-h2-size": "24px",
            "sammlr-type-h2-weight": "700",
            "sammlr-type-h2-line": "1.25",
            "sammlr-type-h3-size": "20px",
            "sammlr-type-h3-weight": "600",
            "sammlr-type-h3-line": "1.3",
            "sammlr-type-body-size": "16px",
            "sammlr-type-body-weight": "400",
            "sammlr-type-body-line": "1.5",
            "sammlr-type-small-size": "14px",
            "sammlr-type-small-weight": "400",
            "sammlr-type-small-line": "1.45",
            "sammlr-type-caption-size": "12px",
            "sammlr-type-caption-weight": "500",
            "sammlr-type-caption-line": "1.4",
        }
        for name, value in expected.items():
            self.assertEqual(value, self.token(name))
        self.assertEqual(
            ["4px", "8px", "12px", "16px", "24px", "32px", "48px", "64px"],
            [self.token(f"sammlr-space-{name}") for name in (1, 2, 3, 4, 6, 8, 12, 16)],
        )
        self.assertEqual(
            ["8px", "12px", "16px", "24px", "999px"],
            [self.token(f"sammlr-radius-{name}") for name in ("small", "medium", "large", "xl", "pill")],
        )
        for name in ("small", "medium", "large"):
            self.assertTrue(self.token(f"sammlr-shadow-{name}"))

    def test_primary_and_status_tokens_have_aa_text_contrast(self):
        self.assertEqual("var(--color-accent)", self.token("sammlr-color-primary"))
        self.assertEqual("#6B32C9", self.token("color-accent"))
        self.assertNotIn("#5d2f86", self.css.lower())
        self.assertGreaterEqual(contrast("#6B32C9", "#FFFFFF"), 4.5)
        pairs = (
            ("missing", "#B91C1C", "#FEF2F2"),
            ("owned", "#166534", "#F0FDF4"),
            ("duplicate", "#6D28D9", "#F5F3FF"),
            ("transit", "#1D4ED8", "#EFF6FF"),
            ("open", "#C2410C", "#FFF7ED"),
        )
        for name, foreground, background in pairs:
            self.assertEqual(foreground, self.token(f"sammlr-status-{name}"))
            self.assertEqual(background, self.token(f"sammlr-status-{name}-bg"))
            self.assertGreaterEqual(contrast(foreground, background), 4.5, name)
        semantic_pairs = (
            ("success", "color-success", "color-success-subtle"),
            ("warning", "color-warning", "color-warning-subtle"),
            ("error", "color-danger", "color-danger-subtle"),
        )
        for status, foreground_token, background_token in semantic_pairs:
            foreground = self.token(foreground_token)
            background = self.token(background_token)
            self.assertEqual(f"var(--{foreground_token})", self.token(f"sammlr-status-{status}"))
            self.assertEqual(f"var(--{background_token})", self.token(f"sammlr-status-{status}-bg"))
            self.assertGreaterEqual(contrast(foreground, background), 4.5, status)
        self.assertEqual("var(--color-text-muted)", self.token("sammlr-status-disabled"))
        self.assertEqual("var(--color-surface-subtle)", self.token("sammlr-status-disabled-bg"))
        self.assertGreaterEqual(contrast("#766E79", "#EEEAE5"), 3.0)

    def test_reference_migration_is_scoped_and_has_no_theme_hardcodes(self):
        marker = "/* S30 – token foundation and scoped reference-page migration */"
        s30_css = self.css.split(marker, 1)[1].split(
            "/* S31 – global product workflows", 1
        )[0]
        rules_after_root = s30_css.split("}\n\n.s30-reference-page", 1)[1]
        self.assertNotRegex(rules_after_root, r"#[0-9a-fA-F]{3,8}\b")
        self.assertIn(":not(.app-header *)", s30_css)
        self.assertIn(":not(.bottom-nav *)", s30_css)
        for page_class in (
            "s30-home-page", "s30-collection-page", "s30-album-page",
            "s30-trade-page", "s30-deal-page", "s30-notifications-page",
        ):
            self.assertEqual(1, self.source.count(page_class), page_class)
        self.assertEqual(0, self.source.count("s30-profile-page"))

    def test_component_families_use_tokens(self):
        s30_css = self.css.split("/* S30 – token foundation", 1)[1]
        for component in (
            ".btn", ".card", "input:not", 'input[type="checkbox"]',
            ".operational-home-empty", ".success", ".warning", ".error",
            ".incoming-transit-badge", ".duplicate", ".open", "dialog",
        ):
            self.assertIn(component, s30_css)
        self.assertGreaterEqual(s30_css.count("var(--sammlr-"), 50)
        self.assertIn(":focus-visible", s30_css)

    def test_mobile_reference_widths_and_reduced_motion_are_explicit(self):
        self.assertIn("@media (max-width:430px)", self.css)
        self.assertIn("@media (max-width:390px)", self.css)
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.css)
        for width in (430, 390):
            block = self.css.split(f"@media (max-width:{width}px)", 1)[1]
            self.assertIn(".s30-reference-page", block)

    def test_reference_get_routes_render_foundation_and_keep_shell(self):
        with sqlite3.connect(self.test_db) as connection:
            request_cursor = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', 'open')"""
            )
            trade_id = request_cursor.lastrowid
        routes_and_classes = (
            ("/", "s30-home-page", "app-header", "bottom-nav"),
            ("/sammlung", "s30-collection-page", "app-header", "bottom-nav"),
            ("/album/vfl", "s30-album-page", "app-header", "bottom-nav"),
            ("/trades", "s30-trade-page", "app-header", "bottom-nav"),
            (f"/trades/{trade_id}", "s30-deal-page", "sticker-list-header", "trade-detail-bar"),
            ("/notifications", "s30-notifications-page", "app-header", "bottom-nav"),
        )
        for route, page_class, header_class, navigation_class in routes_and_classes:
            response = self.client.get(route)
            self.assertEqual(200, response.status_code, route)
            body = response.get_data(as_text=True)
            self.assertIn(f"s30-reference-page {page_class}", body)
            self.assertIn(header_class, body)
            self.assertIn(navigation_class, body)
        profile = self.client.get("/profil").get_data(as_text=True)
        self.assertIn("collector-showcase-page", profile)
        self.assertIn("app-header", profile)
        self.assertIn("bottom-nav", profile)

    def test_reference_gets_do_not_mutate_inventory_or_trade_state(self):
        with sqlite3.connect(self.test_db) as connection:
            before = {
                table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("stickers", "trade_requests", "trades", "trade_reservations")
            }
        for route in ("/", "/sammlung", "/album/vfl", "/trades", "/notifications", "/profil"):
            self.assertEqual(200, self.client.get(route).status_code)
        with sqlite3.connect(self.test_db) as connection:
            after = {
                table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in before
            }
        self.assertEqual(before, after)

    def test_empty_reference_states_offer_an_existing_action(self):
        self.assertIn('Finde Tauschpartner für deine fehlenden Sticker.</h2>', self.source)
        self.assertIn('href="/trades">Tauschpartner ansehen</a>', self.source)
        self.assertIn('Noch keine Benachrichtigungen.</h2>', self.source)
        self.assertIn('class="notification-open" href="/"', self.source)


if __name__ == "__main__":
    unittest.main()
