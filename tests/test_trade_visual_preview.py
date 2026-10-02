"""V2 fixture preview isolation; no domain state is needed to render."""
from pathlib import Path
import unittest
from unittest.mock import patch
from flask import Flask
from flask.testing import FlaskClient
from tests import test_smartdeal_cg1 as core_fixtures
from trade_visual_preview import register_trade_visual_preview, ALBUMS, GIVE, DEALS, PACKS

ROOT = Path(__file__).resolve().parents[1]


class TradeVisualPreviewTests(unittest.TestCase):
    def setUp(self):
        import webapp
        self.web = webapp
        self.config = patch.dict(webapp.app.config, TESTING=True, SAMMLR_ENV='testing', CSRF_ENABLED=True)
        self.config.start(); self.addCleanup(self.config.stop)
        self.client = FlaskClient(webapp.app, use_cookies=True)

    def test_get_without_database_access(self):
        with patch.object(self.web, 'get_db', side_effect=AssertionError('Preview accessed DB')):
            response = self.client.get('/preview/trades-v1')
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('DESIGN PREVIEW', html)
        self.assertIn('aria-controls="fatima-package"', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('Tausch anfragen', html)
        self.assertNotIn('<form', html)
        self.assertNotIn('method="POST"', html)

    def test_fixture_counts_and_complete_package(self):
        self.assertEqual([23,17,12,9,6], [d[1] for d in DEALS])
        self.assertEqual(6, len(ALBUMS)); self.assertEqual(6, len(GIVE))
        for groups in (ALBUMS, GIVE):
            self.assertEqual(23, sum(len(codes) for _, codes in groups))
            self.assertEqual(23, len({(album, code) for album, codes in groups for code in codes}))

    def test_post_not_registered(self):
        for path in ('/preview/trades-v1', '/preview/trades-v1/partners'):
            with self.subTest(path=path):
                rules = [r for r in self.web.app.url_map.iter_rules() if r.rule == path]
                self.assertEqual(1, len(rules)); self.assertNotIn('POST', rules[0].methods)
                with self.client.session_transaction() as session: session['csrf_token'] = 'preview-test'
                with patch.object(self.web, 'get_db', side_effect=AssertionError('POST accessed DB')):
                    response = self.client.post(path, headers={'X-CSRF-Token':'preview-test'})
                self.assertEqual(405, response.status_code)

    def test_not_registered_in_production(self):
        app = Flask(__name__); app.config['SAMMLR_ENV'] = 'production'
        register_trade_visual_preview(app)
        for path in ('/preview/trades-v1', '/preview/trades-v1/partners'):
            self.assertEqual(404, app.test_client().get(path).status_code)

    def test_partner_preview_without_database(self):
        with patch.object(self.web, 'get_db', side_effect=AssertionError('Preview accessed DB')):
            response = self.client.get('/preview/trades-v1/partners')
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('<h1>Sammler</h1>', html)
        self.assertIn('Hat <strong>37</strong> Sticker', html)
        self.assertIn('Bundesliga 07/08', html)
        self.assertNotIn('<form', html)
        self.assertNotIn('method="POST"', html)
        self.assertIn('href="/preview/trades-v1"', html)

    def test_home_has_five_packs_and_discovery_instead_of_partner_list(self):
        html = self.client.get('/preview/trades-v1').get_data(as_text=True)
        self.assertEqual(5, html.count('class="pack"'))
        self.assertIn('SammlrPax', html)
        self.assertIn('Alle Sammler ansehen', html)
        self.assertIn('href="/preview/trades-v1/partners"', html)
        self.assertNotIn('class="partner"', html)
        self.assertNotIn('Tauschen.</h1>', html)
        for pack in PACKS:
            self.assertIn('aria-controls="' + pack['name'].lower() + '-package"', html)
            for direction in ('incoming', 'outgoing'):
                self.assertEqual(pack['size'], sum(len(codes) for _, codes in pack[direction]))
                self.assertEqual(pack['albums'], len(pack[direction]))

    def test_runtime_environment_switch_fails_closed(self):
        with patch.dict(self.web.app.config, SAMMLR_ENV='production'):
            with patch.object(self.web, 'get_db', side_effect=AssertionError('Unexpected DB access')):
                # No auth exemption remains if switched after registration.
                response = self.client.get('/preview/trades-v1')
            self.assertIn(response.status_code, (302, 404))

    def test_existing_trades_handler_stays_registered_and_protected(self):
        self.assertIs(self.web.trades_overview, self.web.app.view_functions['trades_overview'])
        response = self.client.get('/trades')
        self.assertEqual(302, response.status_code); self.assertEqual('/login', response.location)
        html = self.client.get('/preview/trades-v1').get_data(as_text=True)
        self.assertNotIn('action=', html)
        script = (ROOT/'App/static/trade_visual_preview.js').read_text()
        for operation in ('fetch(', 'XMLHttpRequest', 'sendBeacon', 'localStorage', '.submit('):
            self.assertNotIn(operation, script)


class PaxBoardFixtureTests(unittest.TestCase):
    def test_board_has_separate_package_stacks_and_variants(self):
        import webapp
        with patch.dict(webapp.app.config, TESTING=True, SAMMLR_ENV='testing'):
            with patch.object(webapp, 'get_db', side_effect=AssertionError('Preview accessed DB')):
                html = FlaskClient(webapp.app).get('/preview/trades-v1').get_data(as_text=True)
        self.assertEqual(10, html.count('class="pax-stack"'))
        self.assertEqual(5, html.count('A · Mit Post-its'))
        self.assertEqual(5, html.count('B · Nur Stapel'))
        self.assertIn('aria-controls="fatima-in-stickers"', html)
        self.assertIn('aria-controls="fatima-out-stickers"', html)
        self.assertNotIn('data-quantity-delta', html)
        self.assertNotIn('data-stack-quantity', html)
        self.assertIn('compact_sticker_stack.css', html)
        self.assertNotIn('<form', html)

    def test_preview_geometry_cannot_override_canonical_wall(self):
        shared = (ROOT/'App/static/compact_sticker_stack.css').read_text()
        self.assertNotIn('.sticker-wall-stack-layer', shared)
        self.assertNotIn('.sticker-slot-frame', shared)
        self.assertIn('.pax-stack-layer', shared)
        self.assertNotIn('rotate(', shared)
        self.assertNotIn('translateX(', shared)
        self.assertIn('1px', shared)
