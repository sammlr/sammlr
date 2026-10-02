"""Read-only preview boundaries and fixture consistency; no database required."""
import importlib
import sys
import unittest
from unittest.mock import patch


class TradeV2PreviewTests(unittest.TestCase):
    def test_no_database_or_production_app(self):
        before = set(sys.modules)
        with patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')):
            module = importlib.import_module('App.trade_v2')
            app = module.create_app()
            with app.test_client() as client:
                for path in ('/', '/active', '/partners', '/partners/karlheinz', '/deals/fatima',
                             '/partners/karlheinz/smartdeal', '/partners/karlheinz/manual', '/partners/karlheinz/manual/review', '/requests/manual-karlheinz', '/requests/manual-karlheinz/next', '/requests/fatima', '/requests/fatima/next', '/requests/fatima/amendment', '/requests/fatima/shipping', '/requests/fatima/receipt'):
                    url = '/trade-v2' + path
                    self.assertEqual(client.get(url).status_code, 200)
                    self.assertEqual(client.post(url).status_code, 405)
                self.assertEqual(client.get('/trade-v2/deals/karlheinz').status_code, 404)
                self.assertEqual(client.get('/trade-v2/partners/unknown').status_code, 404)
        self.assertFalse(any(m == 'webapp' or m == 'App.webapp' or m.startswith('App.services.') for m in set(sys.modules)-before))
        for rule in app.url_map.iter_rules():
            self.assertLessEqual(rule.methods, {'HEAD', 'GET', 'OPTIONS'})

    def test_normalized_fixtures_and_origins(self):
        from App.trade_v2.fixtures import PARTNERS, DEALS, TOP_IDS, top_deals, deal_for
        self.assertEqual(len(top_deals()), 5)
        self.assertEqual(len(set(TOP_IDS)), 5)
        self.assertGreaterEqual(len(PARTNERS), 10)
        self.assertLessEqual(len(PARTNERS), 15)
        for partner in PARTNERS:
            self.assertEqual(partner['max_swap'], min(partner['for_me'], partner['from_me']))
            self.assertGreaterEqual(partner['total_duplicates'], partner['for_me'])
            deal = deal_for(partner['slug'], 'SMARTDEAL')
            self.assertEqual(set(deal), set(DEALS['fatima']))
            self.assertEqual(deal['origin'], 'SMARTDEAL')
            self.assertGreaterEqual(deal['receive_count'], 5)
            self.assertEqual(deal['receive_count'], deal['give_count'])
            self.assertLessEqual(deal['receive_count'], partner['max_swap'])
            for side in ('receive', 'give'):
                items = [item for album in deal[side] for item in album['items']]
                self.assertEqual(len(items), deal[side+'_count'])
                self.assertEqual(len({item['key'] for item in items}), len(items))
                self.assertEqual({a['id'] for a in deal[side]}, {a['id'] for a in partner['albums']})
            self.assertIsNone(deal_for(partner['slug'], 'MANUAL'))
        for deal in top_deals():
            self.assertEqual(deal['origin'], 'TOP_SUGGESTION')
        self.assertIsNone(deal_for('fatima', 'legacy'))
        # Top discovery has no overlapping receive needs or allocated Give pieces.
        for side in ('receive', 'give'):
            keys = [i['key'] for d in top_deals() for a in d[side] for i in a['items']]
            self.assertEqual(len(keys), len(set(keys)))


if __name__ == '__main__':
    unittest.main()
