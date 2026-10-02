"""PAX-01–03 route isolation and synthetic fixture contracts."""
import sys
import unittest
from unittest.mock import patch
from App.pax import create_app
from App.pax.fixtures import CANDIDATES


class PaxPreviewTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_only_isolated_get_routes(self):
        self.assertEqual({'/static/<path:filename>', '/pax/', '/pax/<candidate_id>', '/pax/layer-comparison'},
                         {r.rule for r in self.app.url_map.iter_rules()})
        for rule in self.app.url_map.iter_rules():
            self.assertLessEqual(rule.methods, {'GET', 'HEAD', 'OPTIONS'})
        for path in ['/pax/', '/pax/fatima', '/pax/justus']:
            self.assertEqual(405, self.client.post(path).status_code)
        self.assertEqual(404, self.client.get('/trades').status_code)

    def test_all_candidates_and_unknown_candidate(self):
        response = self.client.get('/pax/')
        self.assertEqual(200, response.status_code)
        self.assertEqual(5, response.text.count('data-candidate='))
        for candidate in CANDIDATES:
            self.assertEqual(200, self.client.get('/pax/' + candidate['id']).status_code)
        self.assertEqual(404, self.client.get('/pax/not-real').status_code)

    def test_counter_and_direct_content_without_extra_open(self):
        html = self.client.get('/pax/').text
        self.assertEqual(5, html.count('class="pj-pack pax-counter-pack"'))
        for removed in ('pax-register', 'pax-previous', 'pax-next', ' inert', 'pax-summary'):
            self.assertNotIn(removed, html)
        for candidate in CANDIDATES:
            detail = self.client.get('/pax/' + candidate['id']).text
            self.assertIn('<section data-screen="board">', detail)
            self.assertNotIn('id="pax-open"', detail)
            self.assertNotIn('data-screen="closed"', detail)
            self.assertIn('id="pax-request"', detail)

    def test_fixture_counts_and_no_invented_scores(self):
        self.assertEqual(5, len(CANDIDATES))
        self.assertEqual(5, len({c['receive_count'] for c in CANDIDATES}))
        for c in CANDIDATES:
            self.assertEqual(c['receive_count'], c['give_count'])
            for direction in ('receive', 'give'):
                self.assertEqual(c[direction + '_count'], sum(len(a['items']) for a in c[direction]))
            self.assertNotIn('rating', c)
        self.assertEqual(6, CANDIDATES[0]['album_count'])
        self.assertEqual(23, CANDIDATES[0]['receive_count'])

    def test_instances_are_preserved(self):
        items = CANDIDATES[1]['give'][0]['items']
        self.assertEqual(37, len(items))
        self.assertEqual(items[0]['code'], items[1]['code'])
        self.assertNotEqual(items[0]['key'], items[1]['key'])
        self.assertEqual(37, len({i['key'] for i in items}))

    def test_no_database_access_or_product_app_import(self):
        with patch('sqlite3.connect', side_effect=AssertionError('No DB access')):
            client = create_app().test_client()
            self.assertEqual(200, client.get('/pax/').status_code)
            for c in CANDIDATES:
                self.assertEqual(200, client.get('/pax/' + c['id']).status_code)
        self.assertNotIn('App.webapp', sys.modules)
        self.assertNotIn('webapp', sys.modules)


if __name__ == '__main__':
    unittest.main()
