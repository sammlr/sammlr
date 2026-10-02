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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-r3-card-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.smart_trade_requests import SMART_REQUEST_MARKER  # noqa: E402


class R3TradeRequestCardPresentationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-r3-card-")
        self.db_path = Path(self.temp_dir.name) / "request-cards.db"
        shutil.copy2(FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 20)
            connection.execute("DELETE FROM trade_requests")
            connection.execute("DELETE FROM trades")
            self.incoming_manual = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 2, 1, '["AUS2"]', '["SEN3"]', 'open')
                """
            ).lastrowid
            self.outgoing_manual = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["1"]', '["3"]', 'open')
                """
            ).lastrowid
            self.outgoing_smart = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status, from_confirmed)
                VALUES ('vfl', 1, 3, '["4"]', '["5"]', 'open', ?)
                """,
                (SMART_REQUEST_MARKER,),
            ).lastrowid
            self.accepted = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, '["6"]', '["7"]', 'accepted')
                """
            ).lastrowid
            connection.commit()
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def html(self, path):
        response = self.client.get(path)
        self.assertEqual(200, response.status_code, path)
        return response.get_data(as_text=True)

    def test_album_request_cards_keep_direction_type_status_and_actions(self):
        before = sha256(self.db_path)
        html = self.html("/album/vfl/trades?tab=requests")

        self.assertGreaterEqual(html.count("Manuelle Anfrage"), 2)
        self.assertIn("SmartMatch-Anfrage", html)
        self.assertGreaterEqual(html.count('class="trade-status-chip open"'), 3)
        self.assertIn("Du erhältst:</strong> AUS2", html)
        self.assertIn("Du gibst:</strong> SEN3", html)
        self.assertIn("Du erhältst:</strong> 3", html)
        self.assertIn("Du gibst:</strong> 1", html)
        self.assertNotIn("Du suchst", html)
        self.assertNotIn("Du bietest an", html)
        self.assertNotIn("Du gibst ab", html)
        self.assertIn("Wartet auf Antwort", html)
        self.assertIn(f'action="/trade/{self.incoming_manual}/accept"', html)
        self.assertIn(f'action="/trade/{self.incoming_manual}/decline"', html)
        for trade_id in (
            self.incoming_manual, self.outgoing_manual, self.outgoing_smart
        ):
            self.assertIn(
                f'href="/trades/{trade_id}?origin=album_trades">Ansehen</a>',
                html,
            )
        self.assertNotIn('class="ceoklaue-run"', html)
        self.assertEqual(before, sha256(self.db_path))

    def test_global_request_cards_show_the_same_complete_digital_information(self):
        before = sha256(self.db_path)
        html = self.html("/trades?tab=requests")

        self.assertIn('class="trade-person-card trade-request-concept-card"', html)
        self.assertIn("Manuelle Anfrage", html)
        self.assertIn("SmartMatch-Anfrage", html)
        self.assertIn("AUS2", html)
        self.assertIn("SEN3", html)
        self.assertIn("Wartet auf Antwort", html)
        self.assertIn(f'href="/trades/{self.incoming_manual}?origin=trades"', html)
        self.assertIn(f'href="/trades/{self.outgoing_smart}?origin=trades"', html)
        self.assertNotIn('class="ceoklaue-run"', html)
        self.assertEqual(before, sha256(self.db_path))

    def test_advanced_card_status_and_styles_remain_digital_and_solid(self):
        agreements = self.html("/album/vfl/trades?tab=agreements")
        self.assertIn("Manuelle Anfrage", agreements)
        self.assertIn("Wartet auf Durchführung", agreements)
        self.assertIn(f'href="/trades/{self.accepted}?origin=album_trades"', agreements)

        css = STYLE.read_text(encoding="utf-8")
        scoped = css.split(
            "/* R3 Acceptance Fix 3.1 – digital request cards only. */", 1
        )[1].split("@media (max-width:390px)", 1)[0]
        self.assertIn("font-family:var(--sammlr-font-family)", scoped)
        self.assertIn("background:var(--color-surface-subtle)", scoped)
        self.assertNotIn("Bradley Hand", scoped)
        self.assertNotIn("Marker Felt", scoped)
        self.assertNotIn("#f5eedf", scoped)
        self.assertNotIn("border-style:", scoped)
        self.assertIn(
            "Keep later legacy selector specificity out of the R3 request-card surface.",
            css,
        )


if __name__ == "__main__":
    unittest.main()
