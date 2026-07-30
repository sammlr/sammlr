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


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s04-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class HomeCollectionRoutesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s04-test-")
        self.test_db = Path(self.test_dir.name) / "routes.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S04 test.",
        )
        self.assertEqual(
            self.reference_hash_before,
            sha256(REFERENCE_FIXTURE),
            "The canonical S00 fixture changed during an isolated S04 test.",
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

    def execute(self, statement, parameters=()):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(statement, parameters)
            connection.commit()

    def test_root_is_honest_home_ground_state_without_collection_dashboard(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("<h1>Home</h1>", html)
        self.assertIn("Willkommen bei Sammlr.", html)
        self.assertIn('href="/sammlung"', html)
        self.assertNotIn("Aktive Alben", html)
        self.assertNotIn("Vitrine", html)
        self.assertNotIn("Album hinzufügen", html)
        self.assertNotIn("VfL Osnabrück", html)
        self.assertNotIn("Tauschanfrage", html)
        self.assertNotIn("Versand", html)

    def test_collection_route_preserves_album_cards_favorite_and_add_entry(self):
        response = self.client.get("/sammlung")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("<h1>Sammlr-Zentrale</h1>", html)
        self.assertIn("Aktive Alben", html)
        self.assertIn("VfL Osnabrück", html)
        self.assertIn("FIFA World Cup 2026", html)
        self.assertIn('href="/album/vfl"', html)
        self.assertIn('href="/album/wm26"', html)
        self.assertIn('href="/alben/hinzufuegen"', html)
        favorite_card = re.search(
            r'<a class="album-card home-album-card([^"]*)" href="/album/vfl">',
            html,
        )
        self.assertIsNotNone(favorite_card)
        self.assertIn("is-favorite", favorite_card.group(1))

    def test_collection_vitrine_still_uses_real_album_progress(self):
        self.execute("UPDATE albums SET total=3 WHERE id='vfl'")

        response = self.client.get("/sammlung")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn('<h2 class="home-section-title">Vitrine</h2>', html)
        vitrine_start = html.index(
            '<h2 class="home-section-title">Vitrine</h2>'
        )
        self.assertIn("VfL Osnabrück", html[vitrine_start:])
        self.assertIn("3/3", html[vitrine_start:])

    def test_compatibility_routes_redirect_to_canonical_owners(self):
        cases = (
            ("/home", "/"),
            ("/zentrale", "/sammlung"),
            ("/sammlr-zentrale", "/sammlung"),
        )

        for route, target in cases:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(302, response.status_code)
                self.assertEqual(target, response.headers["Location"])

    def test_anonymous_home_and_collection_routes_require_login(self):
        self.login_as(None)

        for route in ("/", "/sammlung", "/home", "/zentrale"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(302, response.status_code)
                self.assertEqual("/login", response.headers["Location"])

    def test_successful_login_starts_on_home(self):
        self.login_as(None)

        response = self.client.post(
            "/login",
            data={
                "username": "fixture_user_1",
                "password": "fixture-only",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual("/", response.headers["Location"])
        home = self.client.get("/")
        self.assertIn("<h1>Home</h1>", home.get_data(as_text=True))

    def test_internal_collection_links_and_album_return_path_are_stable(self):
        home_html = self.client.get("/").get_data(as_text=True)
        collection_html = self.client.get("/sammlung").get_data(as_text=True)
        add_html = self.client.get(
            "/alben/hinzufuegen"
        ).get_data(as_text=True)
        album_html = self.client.get("/album/vfl").get_data(as_text=True)
        profile_html = self.client.get("/profil").get_data(as_text=True)

        self.assertIn('href="/sammlung"', home_html)
        self.assertIn('href="/alben/hinzufuegen"', collection_html)
        self.assertIn('href="/sammlung">← Zurück</a>', add_html)
        self.assertIn('href="/sammlung">← Zur Sammlung</a>', album_html)
        self.assertIn(
            '<a class="profile-link-card" href="/sammlung">',
            profile_html,
        )
        self.assertIn('class="app-header-brand" href="/"', collection_html)

    def test_album_addition_returns_to_collection_and_preserves_membership(self):
        self.assertIsNone(
            self.query_one(
                """
                SELECT id
                FROM user_albums
                WHERE user_id=1 AND album_id='em24'
                """
            )
        )

        response = self.client.get("/alben/hinzufuegen/em24")

        self.assertEqual(302, response.status_code)
        self.assertEqual("/sammlung", response.headers["Location"])
        self.assertIsNotNone(
            self.query_one(
                """
                SELECT id
                FROM user_albums
                WHERE user_id=1 AND album_id='em24'
                """
            )
        )

    def test_empty_undo_uses_collection_as_collection_workflow_fallback(self):
        with self.client.session_transaction() as session:
            session.pop("last_action", None)

        response = self.client.get("/undo")

        self.assertEqual(302, response.status_code)
        self.assertEqual("/sammlung", response.headers["Location"])

    def test_home_and_collection_reads_do_not_change_persistent_data(self):
        before_hash = sha256(self.test_db)

        home_response = self.client.get("/")
        collection_response = self.client.get("/sammlung")

        self.assertEqual(200, home_response.status_code)
        self.assertEqual(200, collection_response.status_code)
        self.assertEqual(before_hash, sha256(self.test_db))


if __name__ == "__main__":
    unittest.main()
