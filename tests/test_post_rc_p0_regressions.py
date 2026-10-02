import atexit
import hashlib
from html.parser import HTMLParser
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
STICKER_STYLE_PATH = APP_DIR / "static" / "sticker_list.css"
WEBAPP_PATH = APP_DIR / "webapp.py"
STICKER_MODULE_PATH = APP_DIR / "sticker_list.py"
STICKER_TEMPLATE_PATH = APP_DIR / "templates" / "sticker_list.html"
STICKER_JS_PATH = APP_DIR / "static" / "sticker_list.js"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CsrfMetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if tag == "meta" and values.get("name") == "csrf-token":
            self.token = values.get("content")


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-post-rc-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "post-rc-test-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402


class PostRcP0RegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        cls.global_css = STYLE_PATH.read_text(encoding="utf-8")
        cls.sticker_css = STICKER_STYLE_PATH.read_text(encoding="utf-8")
        cls.css = cls.global_css + "\n" + cls.sticker_css
        cls.source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                WEBAPP_PATH,
                STICKER_MODULE_PATH,
                STICKER_TEMPLATE_PATH,
                STICKER_JS_PATH,
            )
        )
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-post-rc-")
        self.db_path = Path(self.temp_dir.name) / "post-rc.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 18)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def login_as(self, user_id):
        with self.connect() as connection:
            auth_version = connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (user_id,)
            ).fetchone()[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id
            login_session["auth_version"] = auth_version

    def rendered_csrf_token(self):
        response = self.client.get("/album/vfl")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        parser = CsrfMetaParser()
        parser.feed(html)
        self.assertRegex(parser.token or "", r"^[0-9a-f]{64}$")
        return parser.token, html

    def quantity(self, user_id=1, album_id="vfl", code="1"):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT quantity FROM stickers "
                "WHERE user_id=? AND album_id=? AND sticker_code=?",
                (user_id, album_id, code),
            ).fetchone()
        return row["quantity"] if row else None

    def quantity_post(self, code, delta, token=None):
        headers = {"X-CSRF-Token": token} if token is not None else None
        return self.client.post(
            f"/album/vfl/sticker/{code}/quantity",
            data={"delta": str(delta)},
            headers=headers,
            csrf_protect=False,
        )

    def create_open_trade(self):
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', 'open')"""
            )
            connection.commit()
            return cursor.lastrowid

    def test_rendered_fetch_contract_changes_own_quantity_both_directions(self):
        token, html = self.rendered_csrf_token()
        with self.client.session_transaction() as login_session:
            self.assertEqual(login_session["csrf_token"], token)
        self.assertIn("'X-CSRF-Token': document.querySelector", html)

        own_before = self.quantity()
        foreign_before = self.quantity(user_id=2)
        increased = self.quantity_post("1", 1, token)
        self.assertEqual(200, increased.status_code)
        self.assertEqual(own_before + 1, self.quantity())
        self.assertEqual(foreign_before, self.quantity(user_id=2))

        decreased = self.quantity_post("1", -1, token)
        self.assertEqual(200, decreased.status_code)
        self.assertEqual(own_before, self.quantity())
        self.assertEqual(foreign_before, self.quantity(user_id=2))

    def test_missing_and_wrong_csrf_are_json_403_without_mutation(self):
        token, _ = self.rendered_csrf_token()
        before = self.quantity()
        for supplied in (None, token + "wrong"):
            with self.subTest(token=supplied):
                response = self.quantity_post("1", 1, supplied)
                self.assertEqual(403, response.status_code)
                self.assertEqual(
                    {"status": "error", "code": "forbidden"},
                    response.get_json(),
                )
                self.assertEqual(before, self.quantity())

    def test_unassigned_album_fails_closed_and_creates_no_inventory(self):
        token, _ = self.rendered_csrf_token()
        foreign_before = self.quantity(user_id=2, code="3")
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM stickers "
                "WHERE user_id=1 AND album_id='vfl' AND sticker_code='3'"
            )
            connection.execute(
                "DELETE FROM user_albums WHERE user_id=1 AND album_id='vfl'"
            )
            connection.commit()

        response = self.quantity_post("3", 1, token)
        self.assertEqual(403, response.status_code)
        self.assertEqual({"status": "error", "code": "forbidden"}, response.get_json())
        self.assertIsNone(self.quantity(code="3"))
        self.assertEqual(foreign_before, self.quantity(user_id=2, code="3"))

    def test_html_and_fetch_forbidden_contracts_are_controlled(self):
        html_response = self.client.post(
            "/add/vfl/1",
            csrf_protect=False,
            headers={"Accept": "text/html"},
        )
        self.assertEqual(403, html_response.status_code)
        self.assertEqual("text/html", html_response.mimetype)
        html = html_response.get_data(as_text=True)
        self.assertIn("Zugriff nicht möglich", html)
        self.assertNotIn("403 Forbidden", html)
        self.assertNotIn("Traceback", html)

        json_response = self.quantity_post("1", 1)
        self.assertEqual(403, json_response.status_code)
        self.assertEqual({"status": "error", "code": "forbidden"}, json_response.get_json())

    def test_sticker_list_and_trade_share_dynamic_bottom_space_contract(self):
        trade_id = self.create_open_trade()
        sticker_list = self.client.get("/album/vfl/liste").get_data(as_text=True)
        trade_detail = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)

        for html in (sticker_list, trade_detail):
            self.assertIn('class="sticker-list-tradebar', html)
            self.assertIn('class="bottom-nav"', html)
            self.assertLess(
                html.index('class="sticker-list-tradebar'),
                html.index('class="bottom-nav"'),
            )

        self.assertIn("function syncBottomLayoutSpace()", sticker_list)
        self.assertIn("--sammlr-bottom-nav-space", self.css)
        self.assertIn("--sammlr-trade-dock-height", self.css)
        self.assertIn("--sammlr-bottom-content-space", self.css)
        self.assertRegex(
            self.css,
            r"\.sticker-list-shell\s*\{[^}]*padding-bottom:var\(--sammlr-bottom-content-space\)",
        )
        self.assertRegex(
            self.css,
            r"\.trade-detail-shell\s*\{[^}]*padding-bottom:var\(--sammlr-bottom-content-space\)",
        )
        dock_rules = re.findall(
            r"\.sticker-list-tradebar\s*\{(.*?)\n\}", self.css, re.DOTALL
        )
        active_dock_rule = next(
            (rule for rule in dock_rules if "var(--sammlr-bottom-nav-space)" in rule),
            None,
        )
        self.assertIsNotNone(active_dock_rule)
        self.assertIn("100dvh", active_dock_rule)
        self.assertIn("overflow-y:auto", active_dock_rule)
        self.assertRegex(
            self.css,
            r"(?s)@media \(min-width:720px\).*?max-height:min\(\s*320px,\s*calc\(100dvh",
        )

    def test_sticker_list_is_a_full_page_trade_sheet_with_preserved_controls(self):
        html = self.client.get("/album/vfl/liste").get_data(as_text=True)

        self.assertNotIn('<header class="app-header', html)
        self.assertIn('<a class="sticker-list-logo" href="/" aria-label="Sammlr. Startseite">', html)
        self.assertIn(
            '<img class="sticker-list-wordmark" src="/static/ceoklaue-wordmark.svg" alt="sammlr.">',
            html,
        )
        self.assertIn('<a class="sticker-list-back" href="/album/vfl"', html)
        self.assertIn('aria-label="← Zurück zum Album"', html)
        self.assertIn('class="sticker-list-tradebar is-idle"', html)
        self.assertIn('id="stickerListClear"', html)
        self.assertIn('id="stickerListReviewButton" disabled', html)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn("tradebar.classList.toggle('is-active', canReview)", self.source)
        self.assertIn("tradebar.classList.toggle('is-idle', !canReview)", self.source)
        self.assertIn("item.setAttribute('aria-pressed', 'true')", self.source)
        self.assertIn("stickerListRenderReview()", self.source)
        self.assertIn("requestSubmit()", html)

        self.assertIn("/* Stickerliste: digitaler Sammlr-Tauschzettel */", self.css)
        self.assertIn("#fcfaf6", self.css)
        self.assertIn("background-size:140px 140px, 140px 140px, 28px 28px", self.css)
        self.assertIn("animation:none !important", self.css)
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.css)
        self.assertIn(".sticker-list-glassboard-page .sticker-list-tradebar.is-idle", self.css)
        self.assertIn(".sticker-list-glassboard-page .sticker-list-tradebar.is-active", self.css)
        self.assertIn("overflow-x:hidden", self.css)
        self.assertIn("/* CEOKlaue Final", self.css)
        for alternate in (1, 2, 3):
            self.assertIn(f'url("/static/fonts/ceoklaue-final-alt{alternate}.woff2")', self.css)
            self.assertIn(f'ceoklaue-alt-{alternate}', html)
        self.assertIn('src="/static/sticker_list.js"', html)
        self.assertIn("function stickerListCeoklaueIndex", self.source)

    def test_ceoklaue_runtime_does_not_escape_the_sticker_list_scope(self):
        sticker_list = self.client.get("/album/vfl/liste").get_data(as_text=True)
        album = self.client.get("/album/vfl").get_data(as_text=True)
        profile = self.client.get("/profil").get_data(as_text=True)

        self.assertIn('data-sticker-list-mixing-seed=', sticker_list)
        self.assertIn('src="/static/sticker_list.js"', sticker_list)
        self.assertIn('class="ceoklaue-run"', sticker_list)
        for other_page in (album, profile):
            self.assertNotIn('data-sticker-list-mixing-seed=', other_page)
            self.assertNotIn('src="/static/sticker_list.js"', other_page)
            self.assertNotIn('class="ceoklaue-run"', other_page)

    def test_next_trade_action_remains_inside_scrollable_dock(self):
        trade_id = self.create_open_trade()
        html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        dock = re.search(
            r'<aside class="sticker-list-tradebar trade-detail-bar">(.*?)</aside>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(dock)
        self.assertRegex(dock.group(1), r"<(?:form|button|a)\b")
        self.assertIn("max-height:min(", self.css)
        self.assertIn("overflow-y:auto !important", self.css)

    def test_fixed_glassboard_postit_rules_do_not_leak_into_trade_detail(self):
        trade_id = self.create_open_trade()
        sticker_list = self.client.get("/album/vfl/liste").get_data(as_text=True)
        trade_detail = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)

        self.assertIn(
            '<body class="s31-product-page sticker-list-page sticker-list-glassboard-page"',
            sticker_list,
        )
        self.assertIn('class="sticker-list-tradebar trade-detail-bar"', trade_detail)
        self.assertIn('class="s31-product-page sticker-list-page trade-detail-page', trade_detail)
        self.assertNotIn("sticker-list-glassboard-page", trade_detail)
        self.assertIn('href="/static/sticker_list.css"', sticker_list)
        self.assertIn('src="/static/sticker_list.js"', sticker_list)
        self.assertNotIn("/static/sticker_list.css", trade_detail)
        self.assertNotIn("/static/sticker_list.js", trade_detail)
        album = self.client.get("/album/vfl").get_data(as_text=True)
        self.assertNotIn("/static/sticker_list.css", album)
        self.assertNotIn("/static/sticker_list.js", album)

        self.assertIn(
            ".sticker-list-glassboard-page .sticker-list-tradebar::before",
            self.sticker_css,
        )
        self.assertIn(
            ".sticker-list-glassboard-page .sticker-list-tradebar::after",
            self.sticker_css,
        )
        self.assertNotIn(
            ".sticker-list-page .sticker-list-tradebar::before",
            self.global_css,
        )
        self.assertNotIn(
            ".sticker-list-page .sticker-list-tradebar::after",
            self.global_css,
        )


if __name__ == "__main__":
    unittest.main()
