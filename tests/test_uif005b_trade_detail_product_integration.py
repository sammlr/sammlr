import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
REFERENCE_DB = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCT_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif005b-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_DB, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from services.trade_receipt import TradeReceiptStatusDTO  # noqa: E402
from services.trade_shipping import TradeShippingStatusDTO  # noqa: E402


class UIF005BTradeDetailProductIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product_hash = sha256(PRODUCT_DB)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-uif005b-")
        self.test_db = Path(self.test_dir.name) / "trade-detail.db"
        shutil.copy2(REFERENCE_DB, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.product_hash, sha256(PRODUCT_DB))
        self.test_dir.cleanup()

    def detail(self):
        response = self.client.get("/trades/1?origin=trades")
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def test_regular_route_uses_approved_product_structure_and_real_data(self):
        html = self.detail()
        self.assertIn("trade-product-page", html)
        self.assertIn("Trade mit fixture_user_2", html)
        self.assertIn("VfL Osnabrück", html)
        self.assertIn("Tauschinhalt", html)
        self.assertIn('class="app-header"', html)
        self.assertIn('class="bottom-nav-link active" href="/trades"', html)

    def test_legacy_trade_detail_visual_components_are_not_rendered(self):
        html = self.detail()
        for forbidden in (
            "sticker-list-paper",
            "sticker-list-logo",
            "sticker-list-trade-head",
            "sticker-list-trade-columns",
            "Aktueller Tausch",
            "Visual Fixture",
            "uif005a-",
        ):
            self.assertNotIn(forbidden, html)

    def test_shipping_history_is_exactly_one_native_collapsible_component(self):
        html = self.detail()
        self.assertEqual(1, html.count('<details class="trade-product-timeline">'))
        self.assertEqual(1, html.count("Gesamten Verlauf anzeigen"))
        self.assertEqual(1, html.count("Verlauf ausblenden"))
        self.assertIn("Versandstatus", html)
        self.assertIn("Trade abgeschlossen", html)

    def test_expanded_history_contains_the_complete_canonical_sequence(self):
        items = [
            {"label": "Anfrage gesendet", "state": "done", "timestamp": "2026-08-27T10:00:00Z"},
            {"label": "Eigener Empfang ausstehend", "state": "pending", "timestamp": None},
            {"label": "Trade abgeschlossen", "state": "pending", "timestamp": None},
        ]
        html = webapp.trade_timeline_html(items, "fixture_user_2")
        self.assertEqual(1, html.count('role="listitem" data-source-label="Anfrage gesendet"'))
        self.assertEqual(1, html.count('role="listitem" data-source-label="Eigener Empfang ausstehend"'))
        self.assertEqual(1, html.count('role="listitem" data-source-label="Trade abgeschlossen"'))
        self.assertEqual(1, html.count('<details class="trade-product-timeline">'))

    def test_receipt_is_the_only_primary_action_when_partner_already_shipped(self):
        trade = {"id": 7, "status": "accepted"}
        shipping = TradeShippingStatusDTO(
            trade_request_id=7,
            lifecycle_trade_id=7,
            requester_user_id=1,
            partner_user_id=2,
            requester_shipped=False,
            requester_shipped_at=None,
            partner_shipped=True,
            partner_shipped_at="2026-08-27T10:00:00Z",
        )
        receipt = TradeReceiptStatusDTO(
            trade_request_id=7,
            lifecycle_trade_id=7,
            requester_user_id=1,
            partner_user_id=2,
            requester_received=False,
            requester_received_at=None,
            partner_received=False,
            partner_received_at=None,
        )
        with webapp.app.test_request_context("/trades/7"):
            webapp.session["user_id"] = 1
            html = webapp.trade_detail_primary_action(
                trade,
                False,
                shipping_status=shipping,
                receipt_status=receipt,
                problem_schema_enabled=True,
            )
        self.assertEqual(1, html.count("trade-product-primary"))
        self.assertIn('class="trade-product-secondary">Eigenen Versand bestätigen', html)
        self.assertIn("Alles vollständig erhalten", html)

    def test_product_css_rejects_paper_and_handwriting_language(self):
        css = (APP_DIR / "static" / "style.css").read_text(encoding="utf-8")
        block = css.split("/* UIF-005B", 1)[1]
        self.assertNotIn("Bradley Hand", block)
        self.assertNotIn("Marker Felt", block)
        self.assertNotIn("#f5eedf", block.lower())
        self.assertIn("box-sizing:border-box", block)
        self.assertIn("overflow-wrap:anywhere", block)
        self.assertIn(".trade-product-timeline-event.pending .trade-product-step-icon", block)

    def test_existing_trade_mutation_endpoints_remain_wired(self):
        source = (APP_DIR / "webapp.py").read_text(encoding="utf-8")
        for suffix in (
            "/accept", "/decline", "/ship", "/receive",
            "/problem/resolve", "/problem/close",
        ):
            self.assertIn(f"/trade/{{trade['id']}}{suffix}", source)
        self.assertIn('/trades/{rating_state.legacy_trade_request_id}/rating', source)


if __name__ == "__main__":
    unittest.main()
