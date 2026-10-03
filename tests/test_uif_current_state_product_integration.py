import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
STYLE = APP_DIR / "static" / "style.css"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif-current-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class UIFCurrentStateProductIntegrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        cls.css = STYLE.read_text(encoding="utf-8")
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif-current-")
        self.db_path = Path(self.temp_dir.name) / "product-ui.db"
        shutil.copy2(FIXTURE, self.db_path)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def html(self, route):
        response = self.client.get(route)
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def execute(self, statement, parameters=()):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute(statement, parameters)
            connection.commit()
            return int(cursor.lastrowid)

    def test_home_is_product_integrated_with_real_favorite_and_no_visual_fixture(self):
        self.execute("UPDATE users SET favorite_album_id='vfl' WHERE id=1")
        html = self.html("/")

        self.assertIn('<main class="home-concept-shell"', html)
        self.assertIn("<h1>Für dich</h1>", html)
        self.assertIn("Tauschchance", html)
        self.assertIn("Favoritenalbum", html)
        self.assertIn("VfL Osnabrück", html)
        self.assertIn('href="/album/vfl"', html)
        self.assertNotIn("isolierter Visual-Concept-State", html)
        self.assertNotIn("Visual Fixture", html)
        self.assertNotIn(">17<", html)
        self.assertNotIn('class="feed-empty"', html)

    def test_trade_tabs_and_partner_cards_use_approved_regular_structure(self):
        html = self.html("/trades?tab=partners")

        self.assertIn("<h1>Tauschen</h1>", html)
        self.assertIn(">Tauschpartner</a>", html)
        self.assertIn("Trades", html)
        self.assertIn("Anfragen", html)
        self.assertIn('class="trade-concept-tabs"', html)
        self.assertIn('class="trade-person-card trade-partner-concept-card"', html)
        self.assertIn("Tausch starten", html)
        self.assertNotIn("<h1>Tauschbörse</h1>", html)
        self.assertNotIn("Absprachen", html)
        self.assertNotIn("Visual Fixture", html)
        self.assertNotIn("fixture=request", html)

    def test_real_running_trade_and_request_render_without_fixture_quantities(self):
        accepted_id = self.execute(
            """
            INSERT INTO trade_requests
                (album_id, from_user_id, to_user_id, give_codes, get_codes,
                 status, from_confirmed, to_confirmed)
            VALUES ('vfl', 1, 2, '["1"]', '["2", "3"]', 'accepted', 1, 0)
            """
        )
        request_id = self.execute(
            """
            INSERT INTO trade_requests
                (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
            VALUES ('vfl', 2, 1, '["1", "2"]', '["3"]', 'open')
            """
        )

        running = self.html("/trades?tab=agreements")
        requests = self.html("/trades?tab=requests")
        self.assertIn('class="trade-person-card trade-running-concept-card"', running)
        self.assertIn(f'href="/trades/{accepted_id}?origin=trades"', running)
        self.assertIn("2 erhalten", running)
        self.assertIn("1 gesendet", running)
        self.assertIn('class="trade-person-card trade-request-concept-card"', requests)
        self.assertIn(f'href="/trades/{request_id}?origin=trades"', requests)
        self.assertIn("Du erhältst", requests)
        self.assertIn("2 Sticker", requests)
        self.assertIn("Du gibst", requests)
        self.assertIn("1 Sticker", requests)
        self.assertNotIn("3 erhalten", requests)
        self.assertNotIn("3 geben", requests)

    def test_regular_routes_keep_global_shell_navigation_and_read_only_gets(self):
        before = sha256(self.db_path)
        for route, active_target in (
            ("/", 'href="/" aria-current="page"'),
            ("/sammlung", 'href="/sammlung" aria-current="page"'),
            ("/trades", 'href="/tauschen" aria-current="page"'),
        ):
            with self.subTest(route=route):
                html = self.html(route)
                self.assertIn('class="app-header"', html)
                self.assertIn('class="bottom-nav"', html)
                self.assertIn(active_target, html)
                self.assertIn('action="/notifications"', html)
                self.assertIn('href="/profil"', html)
        self.assertEqual(before, sha256(self.db_path))

    def test_responsive_styles_cover_mobile_and_wide_product_routes(self):
        self.assertIn(".home-concept-grid{", self.css)
        self.assertIn(".s30-home-page .page-title{", self.css)
        self.assertIn("display:block !important", self.css)
        self.assertIn(".trade-concept-tabs{", self.css)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", self.css)
        self.assertIn("@media (max-width:350px)", self.css)
        self.assertIn("@media (min-width:860px)", self.css)
        self.assertIn(".s30-home-page .bottom-nav:not(.album-bottom-nav)", self.css)
        self.assertIn(".s30-trade-page .bottom-nav:not(.album-bottom-nav)", self.css)
        self.assertIn("display:grid !important", self.css)


if __name__ == "__main__":
    unittest.main()
