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


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s07-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class DeepLinkOriginContextTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s07-test-")
        self.test_db = Path(self.test_dir.name) / "deep-links.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S07 test.",
        )
        self.assertEqual(
            self.reference_hash_before,
            sha256(REFERENCE_FIXTURE),
            "The canonical S00 fixture changed during an isolated S07 test.",
        )
        self.test_dir.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            if user_id is not None:
                session["user_id"] = user_id

    def create_open_trade(self):
        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1"], "get_codes": ["3"]},
        )
        self.assertEqual(302, response.status_code)
        connection = webapp.get_db()
        trade_id = connection.execute(
            "SELECT MAX(id) AS id FROM trade_requests"
        ).fetchone()["id"]
        connection.close()
        return trade_id

    def detail_back_link(self, trade_id=1, origin=None):
        query_string = {"origin": origin} if origin is not None else None
        response = self.client.get(
            f"/trades/{trade_id}",
            query_string=query_string,
        )
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        match = re.search(
            r'<a class="sticker-list-back" href="([^"]+)">([^<]+)</a>',
            html,
        )
        self.assertIsNotNone(match, "Der kontextuelle Deal-Rückweg fehlt.")
        return match.group(1), match.group(2), html

    def test_allowed_origin_list_is_small_and_explicit(self):
        self.assertEqual(
            {"home", "trades", "album_trades", "notifications"},
            set(webapp.TRADE_DETAIL_ORIGINS),
        )

    def test_deal_opened_from_home_returns_to_home(self):
        href, label, _ = self.detail_back_link(origin="home")

        self.assertEqual("/", href)
        self.assertEqual("← zurück zu Home", label)

    def test_deal_opened_from_trade_centre_returns_to_my_deals(self):
        href, label, _ = self.detail_back_link(origin="trades")

        self.assertEqual("/trades?tab=requests", href)
        self.assertEqual("← zurück zu Tauschbörse", label)

    def test_direct_deal_url_without_origin_uses_trade_centre_fallback(self):
        href, label, html = self.detail_back_link()

        self.assertEqual("/trades?tab=requests", href)
        self.assertEqual("← zurück zu Tauschbörse", label)
        self.assertIn("fixture_user_2", html)

    def test_unknown_origin_uses_safe_trade_centre_fallback(self):
        href, _, _ = self.detail_back_link(origin="not-a-context")

        self.assertEqual("/trades?tab=requests", href)

    def test_external_and_manipulated_origins_are_rejected(self):
        invalid_origins = (
            "https://example.invalid/path",
            "//example.invalid/path",
            "javascript:alert(1)",
            "/profil",
        )

        for origin in invalid_origins:
            with self.subTest(origin=origin):
                href, _, html = self.detail_back_link(origin=origin)
                self.assertEqual("/trades?tab=requests", href)
                self.assertNotIn("example.invalid", href)
                self.assertNotIn("javascript:", html.lower())

    def test_album_trade_origin_returns_to_verified_trade_album(self):
        href, label, _ = self.detail_back_link(origin="album_trades")

        self.assertEqual("/album/vfl/trades?tab=requests", href)
        self.assertEqual("← zurück zu Album-Tauschbörse", label)

    def test_existing_trade_lists_emit_only_allowed_context_values(self):
        trade_id = self.create_open_trade()

        global_html = self.client.get(
            "/trades?tab=requests"
        ).get_data(as_text=True)
        album_html = self.client.get(
            "/album/vfl/trades?tab=requests"
        ).get_data(as_text=True)

        self.assertIn(
            f'href="/trades/{trade_id}?origin=trades"',
            global_html,
        )
        self.assertIn(
            f'href="/trades/{trade_id}?origin=album_trades"',
            album_html,
        )

    def test_valid_origin_never_bypasses_trade_permission(self):
        self.login_as(3)

        response = self.client.get("/trades/1", query_string={"origin": "home"})

        self.assertEqual(302, response.status_code)
        self.assertTrue(response.headers["Location"].startswith("/trades?message="))
        self.assertNotIn("origin=home", response.headers["Location"])

    def test_unknown_trade_id_is_handled_before_origin_context(self):
        response = self.client.get(
            "/trades/9999",
            query_string={"origin": "home"},
        )

        self.assertEqual(302, response.status_code)
        self.assertTrue(response.headers["Location"].startswith("/trades?message="))

    def test_trade_alias_keeps_existing_direct_access_with_origin(self):
        response = self.client.get("/trade/1", query_string={"origin": "home"})

        self.assertEqual(200, response.status_code)
        self.assertIn(
            '<a class="sticker-list-back" href="/">← zurück zu Home</a>',
            response.get_data(as_text=True),
        )

    def test_deal_detail_get_does_not_change_persistent_data(self):
        before_hash = sha256(self.test_db)

        response = self.client.get("/trades/1", query_string={"origin": "home"})

        self.assertEqual(200, response.status_code)
        self.assertEqual(before_hash, sha256(self.test_db))


if __name__ == "__main__":
    unittest.main()
