"""Real Flask dispatch/auth/CSRF over synthetic V21 contracts; no public V1 create."""
from datetime import timedelta
import unittest
from unittest.mock import patch
from flask.testing import FlaskClient
from tests import test_smartdeal_cg1 as fixtures
from services import smartdeal_runtime

NOW = fixtures.NOW


class TradeHttpContractTests(unittest.TestCase):
    for _name in ('configure', 'quantity', 'plan', 'extra_partner', 'binding',
                  'service', 'create', 'state', 'all_rows', 'assert_reopened',
                  'package', 'race', 'release', 'bound', 'assert_terminal',
                  'core', 'go', 'assert_accepted'):
        locals()[_name] = getattr(fixtures.CoreGateTests, _name)
    del _name

    def setUp(self):
        fixtures.CoreGateTests.setUp(self)
        import webapp
        self.web = webapp
        self.now = NOW
        self.addCleanup(patch.stopall)
        patch.object(webapp, 'DB', str(self.path)).start()
        patch.dict(webapp.app.config, TESTING=True, CSRF_ENABLED=True,
                   TESTING_AUTH_VERSION_COMPAT=False).start()
        patch.object(webapp, 'all_codes', side_effect=lambda a: self.catalog[a]).start()
        # Inject only deterministic external clock/catalog; real dispatcher and actor.
        patch.object(webapp, 'dispatch_smartdeal_request', side_effect=lambda c, rid, actor, action, **kw:
                     smartdeal_runtime.dispatch_request(c, rid, actor, action,
                         catalog_provider=lambda a: self.catalog[a], now_provider=lambda: self.now)).start()
        self.client = FlaskClient(webapp.app, use_cookies=True)
        self.login(2)

    def login(self, actor, version=None):
        with self.client.session_transaction() as session:
            session.clear()
            session['csrf_token'] = 'td1-synthetic-csrf'
            if actor is not None:
                session['user_id'] = actor
                row = self.db.execute('SELECT auth_version FROM users WHERE id=?', (actor,)).fetchone()
                session['auth_version'] = version if version is not None else row[0]

    def post(self, path, csrf=True, data=None):
        return self.client.post(path, data=data or {}, headers={
            'X-CSRF-Token': 'td1-synthetic-csrf'} if csrf else {}, follow_redirects=False)

    def canonical(self, response, deal):
        self.assertEqual(302, response.status_code)
        self.assertEqual(f'/trades/{deal.request_id}', response.location)

    def test_accept_and_retry(self):
        deal = self.bound()
        self.canonical(self.post(f'/trade/{deal.request_id}/accept'), deal)
        self.assert_accepted(deal)
        before = self.all_rows()
        self.canonical(self.post(f'/trade/{deal.request_id}/accept'), deal)
        self.assert_reopened(before)

    def test_decline(self):
        deal = self.bound()
        self.canonical(self.post(f'/trade/{deal.request_id}/decline'), deal)
        self.assert_terminal(deal, 'declined')

    def test_withdraw(self):
        deal = self.bound(); self.login(1)
        self.canonical(self.post(f'/trades/{deal.request_id}/cancel'), deal)
        self.assert_terminal(deal, 'cancelled')

    def test_anonymous_requires_login(self):
        deal = self.bound(); self.login(None); before = self.all_rows()
        response = self.post(f'/trade/{deal.request_id}/accept')
        self.assertEqual(302, response.status_code); self.assertEqual('/login', response.location)
        self.assert_reopened(before)

    def test_revoked_auth_session(self):
        deal = self.bound(); self.login(2, version=-1); before = self.all_rows()
        response = self.post(f'/trade/{deal.request_id}/accept')
        self.assertEqual(302, response.status_code); self.assertEqual('/login', response.location)
        self.assert_reopened(before)

    def test_missing_csrf(self):
        deal = self.bound(); before = self.all_rows()
        self.assertEqual(403, self.post(f'/trade/{deal.request_id}/accept', csrf=False).status_code)
        self.assert_reopened(before)

    def test_invalid_csrf(self):
        deal = self.bound(); before = self.all_rows()
        response = self.client.post(f'/trade/{deal.request_id}/decline', headers={'X-CSRF-Token': 'wrong'})
        self.assertEqual(403, response.status_code); self.assert_reopened(before)

    def test_foreign_request(self):
        deal = self.bound(); self.login(3); before = self.all_rows()
        self.assertEqual(403, self.post(f'/trade/{deal.request_id}/accept').status_code)
        self.assert_reopened(before)

    def test_sender_cannot_accept_or_decline(self):
        deal = self.bound(); self.login(1); before = self.all_rows()
        for action in ('accept', 'decline'):
            with self.subTest(action=action):
                self.assertEqual(403, self.post(f'/trade/{deal.request_id}/{action}').status_code)
                self.assert_reopened(before)

    def test_receiver_cannot_withdraw(self):
        deal = self.bound(); before = self.all_rows()
        self.assertEqual(403, self.post(f'/trades/{deal.request_id}/cancel').status_code)
        self.assert_reopened(before)

    def test_expired_at_absolute_deadline(self):
        deal = self.bound(); self.now = NOW + timedelta(hours=24)
        self.assertEqual(409, self.post(f'/trade/{deal.request_id}/accept').status_code)
        self.assert_terminal(deal, 'expired')
        before = self.all_rows()
        self.assertEqual(409, self.post(f'/trade/{deal.request_id}/accept').status_code)
        self.assert_reopened(before)

    def test_terminal_cannot_be_accepted(self):
        deal = self.bound(); self.release().decline(deal.request_id, 2); before = self.all_rows()
        self.assertEqual(409, self.post(f'/trade/{deal.request_id}/accept').status_code)
        self.assert_reopened(before)

    def test_unknown_id_safe_legacy_fallback(self):
        before = self.all_rows()
        response = self.post('/trade/999999/accept')
        self.assertEqual(302, response.status_code)
        self.assertTrue(response.location.startswith('/trades'))
        self.assert_reopened(before)

    def test_invalid_route_id_and_wrong_method(self):
        before = self.all_rows()
        self.assertEqual(404, self.post('/trade/not-an-id/accept').status_code)
        self.assertEqual(405, self.client.get('/trade/1/accept').status_code)
        self.assert_reopened(before)

    def test_plural_hint_routes_do_not_mutate(self):
        deal = self.bound(); before = self.all_rows()
        for action in ('accept', 'decline', 'confirm'):
            with self.subTest(action=action):
                response = self.post(f'/trades/{deal.request_id}/{action}')
                self.assertEqual(302, response.status_code)
                self.assertTrue(response.location.startswith('/trades?message='))
                self.assert_reopened(before)

    def legacy(self):
        rid = self.db.execute("""INSERT INTO trade_requests
            (album_id,from_user_id,to_user_id,give_codes,get_codes,status)
            VALUES ('vfl',1,2,'["O0000"]','["I0000"]','open')""").lastrowid
        self.db.commit()
        return rid

    def test_legacy_decline_keeps_contract(self):
        rid = self.legacy(); before = self.all_rows()
        response = self.post(f'/trade/{rid}/decline')
        self.assertEqual(302, response.status_code)
        self.assertEqual(('legacy', 'declined', None, None), tuple(self.db.execute(
            'SELECT contract_type,status,binding_created_at,accepted_at FROM trade_requests WHERE id=?', (rid,)).fetchone()))
        self.assertEqual(before['stickers'], self.all_rows()['stickers'])
        self.assertEqual(before['trade_reservations'], self.all_rows()['trade_reservations'])

    def test_legacy_cancel_remains_hint(self):
        rid = self.legacy(); self.login(1); before = self.all_rows()
        self.assertEqual(302, self.post(f'/trades/{rid}/cancel').status_code)
        self.assert_reopened(before)

    def test_legacy_accept_reserves_only_at_accept(self):
        rid = self.legacy(); before = self.all_rows()
        self.assertEqual([], before['trade_reservations'])
        self.assertEqual(302, self.post(f'/trade/{rid}/accept').status_code)
        self.assertEqual(('legacy', 'accepted', None, None), tuple(self.db.execute(
            'SELECT contract_type,status,binding_created_at,accepted_at FROM trade_requests WHERE id=?', (rid,)).fetchone()))
        self.assertEqual(2, self.db.execute("SELECT count(*) FROM trade_reservations WHERE state='active'").fetchone()[0])
        self.assertEqual(before['stickers'], self.all_rows()['stickers'])


def blocked_case(action):
    def test(self):
        deal = self.bound(); self.core().accept(deal.request_id, 2); before = self.all_rows()
        response = self.post(f'/trade/{deal.request_id}/{action}', data={'confirm_physical_arrival': '1'})
        self.assertEqual(409, response.status_code)
        self.assert_reopened(before)
    return test


for action in ('ship', 'receive', 'confirm', 'fail', 'problem', 'problem/close', 'problem/resolve'):
    setattr(TradeHttpContractTests, 'test_v1_blocks_' + action.replace('/', '_'), blocked_case(action))
del action
