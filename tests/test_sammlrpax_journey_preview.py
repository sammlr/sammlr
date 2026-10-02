"""Isolated design preview: no database, domain handlers or production styles."""
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"App"))
from flask import Flask
from trade_visual_preview import register_trade_visual_preview, ALBUMS, GIVE

ROOT = Path(__file__).resolve().parents[1]
ROUTE = '/preview/sammlrpax-journey-v1'


class SammlrPaxJourneyPreviewTests(unittest.TestCase):
    def app(self, environment='testing'):
        app = Flask(__name__, template_folder=str(ROOT/'App/templates'), static_folder=str(ROOT/'App/static'))
        app.config['SAMMLR_ENV'] = environment
        register_trade_visual_preview(app)
        return app

    def test_get_is_static_and_database_free(self):
        with patch('sqlite3.connect', side_effect=AssertionError('DB accessed')):
            response = self.app().test_client().get(ROUTE)
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        for content in ('Fatima', 'Pax anfragen', 'Sticker prüfen', 'Musterstraße 89', 'pj-data'):
            self.assertIn(content, html)
        for sheet in ('/static/style.css', 'compact_sticker_stack.css', 'trade_visual_preview.css'):
            self.assertNotIn(sheet, html)
        self.assertNotIn('<form', html)

    def test_get_only_and_no_production_registration(self):
        app = self.app()
        rule = next(r for r in app.url_map.iter_rules() if r.rule == ROUTE)
        self.assertEqual({'GET','HEAD','OPTIONS'}, rule.methods)
        self.assertEqual(405, app.test_client().post(ROUTE).status_code)
        self.assertEqual(404, self.app('production').test_client().get(ROUTE).status_code)
        app.config['SAMMLR_ENV']='production'
        self.assertEqual(404, app.test_client().get(ROUTE).status_code)

    def test_app_registration_keeps_real_trade_handler_and_avoids_db(self):
        from tests import test_smartdeal_cg1 as fixtures
        import webapp as web
        before = web.app.view_functions['trades'] if 'trades' in web.app.view_functions else {
            r.rule: web.app.view_functions[r.endpoint] for r in web.app.url_map.iter_rules() if r.rule=='/trades'
        }
        with patch.dict(web.app.config, TESTING=True, SAMMLR_ENV='testing'):
            with patch.object(web, 'get_db', side_effect=AssertionError('Preview accessed app DB')):
                response = web.app.test_client().get(ROUTE)
        self.assertEqual(200,response.status_code)
        after = web.app.view_functions['trades'] if 'trades' in web.app.view_functions else {
            r.rule: web.app.view_functions[r.endpoint] for r in web.app.url_map.iter_rules() if r.rule=='/trades'
        }
        self.assertEqual(before,after)

    def test_symmetric_fixture_has_23_stickers_in_six_albums(self):
        for groups in (ALBUMS,GIVE):
            self.assertEqual(6,len(groups))
            self.assertEqual(23,sum(len(codes) for _,codes in groups))
            self.assertEqual(23,len({(album,code) for album,codes in groups for code in codes}))

    def test_no_client_mutation_transport_or_persistence(self):
        js=(ROOT/'App/static/sammlrpax_journey_v1.js').read_text()
        for forbidden in ('fetch(', 'XMLHttpRequest', 'sendBeacon', 'localStorage', 'sessionStorage', 'document.cookie', 'WebSocket'):
            self.assertNotIn(forbidden,js)
        css=(ROOT/'App/static/sammlrpax_journey_v1.css').read_text()
        for forbidden in ('.sticker-slot-frame','.sticker-wall-stack-layer','dashed','dotted'):
            self.assertNotIn(forbidden,css)

    def test_existing_preview_routes_are_retained(self):
        app=self.app()
        for path in ('/preview/trades-v1','/preview/trades-v1/partners'):
            self.assertEqual(200,app.test_client().get(path).status_code)


if __name__=='__main__':unittest.main()
