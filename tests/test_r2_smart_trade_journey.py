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
REFERENCE_DB = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCT_DB = APP_DIR / "Database" / "sammlr.db"
STYLE = APP_DIR / "static" / "style.css"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-r2-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_DB, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402


class R2SmartTradeJourneyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product_hash = sha256(PRODUCT_DB)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.product_hash == sha256(PRODUCT_DB)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-r2-")
        self.db_path = Path(self.temp_dir.name) / "r2.db"
        shutil.copy2(REFERENCE_DB, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, target_version=5)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.product_hash, sha256(PRODUCT_DB))
        self.temp_dir.cleanup()

    def get_html(self, route):
        response = self.client.get(route)
        self.assertEqual(200, response.status_code, route)
        return response.get_data(as_text=True)

    def test_album_hub_converges_on_approved_trade_language(self):
        before = sha256(self.db_path)
        html = self.get_html("/album/vfl/trades?tab=partners")

        self.assertIn("r2-trade-hub-page", html)
        self.assertIn('<main class="trade-concept-shell"', html)
        self.assertIn('<nav class="trade-concept-tabs r2-album-trade-tabs"', html)
        self.assertIn("Tauschpartner", html)
        self.assertIn("Trades", html)
        self.assertIn("Anfragen", html)
        self.assertIn("SmartMatch öffnen", html)
        self.assertIn('href="/trades">Alle Trades</a>', html)
        self.assertIn("trade-person-card trade-partner-concept-card", html)
        self.assertNotIn("Absprachen", html)
        self.assertEqual(before, sha256(self.db_path))

    def test_smartmatch_is_read_only_and_leads_into_canonical_detail(self):
        before = sha256(self.db_path)
        html = self.get_html("/album/vfl/smart-trades")

        self.assertIn("r2-smart-match-page", html)
        self.assertIn("<h1>SmartMatch</h1>", html)
        self.assertIn("Smart-Anfragen global offen", html)
        self.assertIn("nicht editierbar", html)
        self.assertNotIn('name="give_codes"', html)
        self.assertNotIn('name="get_codes"', html)
        if 'data-smart-package="read-only"' in html:
            self.assertIn("r2-smart-match-card", html)
            self.assertIn("SmartMatch anfragen", html)
        self.assertEqual(before, sha256(self.db_path))

    def test_manual_composer_preserves_existing_form_and_unequal_trade_rule(self):
        before = sha256(self.db_path)
        html = self.get_html("/album/vfl/trade/2")

        self.assertIn("r2-trade-composer-page", html)
        self.assertIn("<h1>Tausch mit fixture_user_2</h1>", html)
        self.assertIn('id="tradeWizard"', html)
        self.assertIn("1 Fehlende", html)
        self.assertIn("2 Doppelte", html)
        self.assertIn("3 Prüfen", html)
        self.assertIn('action="/album/vfl/trade/2/request"', html)
        self.assertIn(
            "Du musst mindestens so viele Sticker anbieten, wie du suchst.",
            html,
        )
        self.assertEqual(before, sha256(self.db_path))

    def test_approved_global_trades_and_detail_surfaces_remain_intact(self):
        overview = self.get_html("/trades?tab=partners")
        detail = self.get_html("/trades/1?origin=trades")

        self.assertIn("s30-trade-page", overview)
        self.assertIn('class="trade-concept-tabs"', overview)
        self.assertNotIn("r2-trade-journey-page", overview)
        self.assertIn("trade-product-page", detail)
        self.assertIn("Tauschinhalt", detail)
        self.assertNotIn("r2-trade-journey-page", detail)

    def test_r2_styles_are_scoped_solid_and_mobile_bounded(self):
        css = STYLE.read_text(encoding="utf-8")
        r2_css = css.split("/* R2 – Smart Trade Journey convergence.", 1)[1]

        self.assertIn(".r2-trade-journey-page", r2_css)
        self.assertIn("overflow-x:hidden", r2_css)
        self.assertIn("@media (max-width:430px)", r2_css)
        self.assertIn("grid-template-columns:minmax(0,1fr)", r2_css)
        self.assertNotIn("dashed", r2_css)
        self.assertNotIn("dotted", r2_css)


if __name__ == "__main__":
    unittest.main()
