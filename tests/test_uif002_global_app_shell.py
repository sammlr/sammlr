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
STYLESHEET = APP_DIR / "static" / "style.css"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"
UI_ROADMAP = PROJECT_ROOT / "Dokumentation" / "Post-RC" / "05-ui-backlog.md"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif002-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class UIF002GlobalAppShellTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.css = STYLESHEET.read_text(encoding="utf-8")
        cls.uif002_css = cls.css.split(
            "/* UIF-002 – global app shell and Sammlr design foundation */", 1
        )[1]
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif002-")
        self.test_db = Path(self.test_dir.name) / "shell.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.test_dir.cleanup()

    def get_html(self, path):
        response = self.client.get(path)
        self.assertEqual(200, response.status_code, path)
        return response.get_data(as_text=True)

    def test_palette_a_is_the_single_canonical_color_source(self):
        expected = {
            "--color-background": "#F6F3EF",
            "--color-surface": "#FFFFFF",
            "--color-surface-subtle": "#EEEAE5",
            "--color-text-primary": "#211D24",
            "--color-text-secondary": "#625B66",
            "--color-text-muted": "#766E79",
            "--color-border": "#DDD7DF",
            "--color-border-strong": "#C8C0CB",
            "--color-accent": "#6B32C9",
            "--color-accent-hover": "#5825AD",
            "--color-accent-subtle": "#F0E9FA",
            "--color-accent-foreground": "#FFFFFF",
            "--color-success": "#2E7150",
            "--color-success-subtle": "#E9F4ED",
            "--color-warning": "#9A5B18",
            "--color-warning-subtle": "#FFF2DC",
            "--color-danger": "#B23A32",
            "--color-danger-subtle": "#FCECEA",
        }
        for token, value in expected.items():
            self.assertIn(f"{token}:{value}", self.css)

        for study_only_color in ("#54239A", "#73569B", "#EEE6F6", "#F1EDF5"):
            self.assertNotIn(study_only_color, self.css)

    def test_header_renderer_keeps_profile_settings_exception_scoped(self):
        for route in ("/", "/sammlung", "/trades", "/profil"):
            html = self.get_html(route)
            header = re.search(
                r'<header class="app-header">(.*?)</header>', html, re.DOTALL
            ).group(1)
            self.assertIn("app-header-brand-word", header, route)
            self.assertIn("app-header-bell-svg", header, route)
            self.assertIn('action="/notifications"', header, route)
            if route == "/profil":
                self.assertIn('class="app-header-action app-header-settings" href="/account"', header)
                self.assertNotIn('class="app-header-action app-header-profile"', header)
            else:
                self.assertIn('href="/profil"', header, route)
                self.assertNotIn('class="app-header-action app-header-settings"', header)
            self.assertNotIn("sammlr_logo_header.png", header, route)
            self.assertNotRegex(header.lower(), r"chat|message|nachrichten")

    def test_bottom_navigation_keeps_routes_and_exact_active_destination(self):
        cases = (
            ("/sammlung", "/sammlung"),
            ("/", "/"),
            ("/trades", "/trades"),
        )
        for route, current_href in cases:
            html = self.get_html(route)
            nav = re.search(r'<nav class="bottom-nav">(.*?)</nav>', html, re.DOTALL).group(1)
            self.assertEqual(3, nav.count('class="bottom-nav-link'))
            for href in ("/sammlung", "/", "/trades"):
                self.assertIn(f'href="{href}"', nav)
            self.assertRegex(
                nav,
                rf'class="bottom-nav-link active" href="{re.escape(current_href)}" aria-current="page"',
            )

    def test_side_routes_do_not_invent_a_main_world_active_state(self):
        for route in ("/profil", "/notifications", "/trophaeen", "/statistik", "/account", "/profil/fixture_user_2/album/vfl"):
            html = self.get_html(route)
            nav = re.search(r'<nav class="bottom-nav">(.*?)</nav>', html, re.DOTALL).group(1)
            self.assertEqual(3, nav.count('class="bottom-nav-link'))
            self.assertNotIn('bottom-nav-link active', nav, route)
            self.assertNotIn('aria-current="page"', nav, route)
            for href in ("/sammlung", "/", "/trades"):
                self.assertIn(f'href="{href}"', nav, route)

        profile_world_nav = webapp.bottom_nav("profil")
        self.assertNotIn('bottom-nav-link active', profile_world_nav)
        self.assertNotIn('aria-current="page"', profile_world_nav)

    def test_collection_favorite_state_matches_the_stored_album_only(self):
        html = self.get_html("/sammlung")
        controls = re.findall(
            r'<a class="collection-favorite-control([^"]*)"[^>]*aria-label="([^"]+)"',
            html,
        )
        self.assertEqual(2, len(controls))
        self.assertEqual(1, sum("is-favorite" in classes for classes, _ in controls))
        self.assertEqual(1, sum("Favoritenalbum ändern" == label for _, label in controls))
        self.assertEqual(1, sum("Als Favoritenalbum auswählen" == label for _, label in controls))
        self.assertEqual(1, html.count('<span aria-hidden="true">★</span>'))
        self.assertEqual(1, html.count('<span aria-hidden="true">☆</span>'))

    def test_favorite_toggle_and_reload_keep_the_persisted_state(self):
        selection = self.get_html("/favorit?auswahl=1")
        token = re.search(r'<meta name="csrf-token" content="([^"]+)"', selection).group(1)

        response = self.client.post(
            "/favorit/toggle/wm26",
            headers={"X-CSRF-Token": token},
            follow_redirects=False,
        )
        self.assertEqual(302, response.status_code)

        first_reload = self.get_html("/sammlung")
        wm26_shell = re.search(
            r'<article class="collection-album-card-shell([^"]*)">\s*'
            r'<a class="[^"]*" href="/album/wm26">',
            first_reload,
        ).group(1)
        self.assertIn("is-favorite", wm26_shell)
        self.assertEqual(1, first_reload.count("collection-favorite-control is-favorite"))

        second_reload = self.get_html("/sammlung")
        self.assertEqual(1, second_reload.count("collection-favorite-control is-favorite"))
        self.assertIn('href="/album/wm26"', second_reload)

    def test_global_shell_and_component_foundation_are_token_driven(self):
        required_fragments = (
            ".s31-product-page .app-header{",
            ".s31-product-page .app-header + .page-title{",
            ".s31-product-page .app-header-avatar{",
            ".s31-product-page .notification-badge{",
            ".s31-product-page .bottom-nav:not(.album-bottom-nav){",
            "background:var(--color-accent-subtle) !important",
            "color:var(--color-text-secondary) !important",
            "background:var(--color-surface-subtle) !important",
            "background:var(--color-accent) !important",
            "background:var(--color-success-subtle)",
            "background:var(--color-warning-subtle)",
            "background:var(--color-danger-subtle)",
            ".s31-product-page .collection-favorite-control.is-favorite{",
            "color:var(--color-text-muted)",
            "font-size:16px",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, self.uif002_css)

    def test_responsive_contract_covers_430_390_and_336_capable_state(self):
        self.assertIn("@media (max-width:430px)", self.uif002_css)
        self.assertIn("@media (max-width:350px)", self.uif002_css)
        self.assertIn("width:calc(100% - 16px) !important", self.uif002_css)
        self.assertIn("env(safe-area-inset-bottom)", self.uif002_css)
        self.assertIn("min-width:0", self.uif002_css)

    def test_representative_shell_gets_are_read_only(self):
        before = sha256(self.test_db)
        for route in ("/", "/sammlung", "/trades", "/profil"):
            self.get_html(route)
        self.assertEqual(before, sha256(self.test_db))

    def test_ui_roadmap_stops_after_uif002_for_this_package(self):
        roadmap = UI_ROADMAP.read_text(encoding="utf-8")
        expected_order = [
            "UIF-001", "UIF-002A", "UIF-002", "UIF-003", "UIF-004",
            "UIF-005", "UIF-006", "UIF-007", "UIF-008", "UIF-009",
            "UIF-010", "UIF-011", "UIF-012",
        ]
        documented_order = re.findall(r"\*\*(UIF-\d{3}A?)\s+–", roadmap)
        self.assertEqual(expected_order, documented_order)
        self.assertIn("Chat/Messaging", roadmap)
        self.assertIn("separates Produktpaket", roadmap)


if __name__ == "__main__":
    unittest.main()
