"""Composite runtime/handler integration on synthetic V21 databases."""
from datetime import timedelta
import sqlite3
import unittest
from unittest.mock import patch
from tests import test_sd_t6b_accept_mutual_go as foundation
from services import smartdeal_runtime as runtime
from services.smartdeal_suggestions import SmartDealSuggestion
from services.smartdeal_release import SmartDealReleaseService
from services.smartdeal_acceptance import SmartDealAcceptanceService
NOW = foundation.NOW


class CoreGateTests(unittest.TestCase):
    # Reuse fixture helpers, never rediscover old tests as new tests.
    for _name in ('setUp','configure','quantity','plan','extra_partner','binding','service','create',
                  'state','all_rows','assert_reopened','package','race','release','bound','assert_terminal',
                  'core','go','assert_accepted'):
        locals()[_name] = getattr(foundation.AcceptTests, _name)
    del _name

    def discovery(self, now=NOW, db=None):
        return runtime.discover(self.db if db is None else db, 1,
                                catalog_provider=lambda a:self.catalog[a], now_provider=lambda:now)

    def handler(self, name, deal, actor=2, now=NOW, db=None, form=None):
        import webapp
        def connection():
            c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row
            return c
        def dispatch(c, rid, uid, action, **kw):
            return runtime.dispatch_request(c,rid,uid,action,catalog_provider=lambda a:self.catalog[a],now_provider=lambda:now)
        with webapp.app.test_request_context('/trade/action',method='POST',data=form or {}), \
             patch.object(webapp,'get_db',side_effect=connection if db is None else lambda:db), \
             patch.object(webapp,'current_user_id',return_value=actor), \
             patch.object(webapp,'dispatch_smartdeal_request',side_effect=dispatch):
            return getattr(webapp,name)(deal.request_id)

    def test_composite_accepted(self):
        self.configure(17,('vfl','em24'))
        payload=SmartDealSuggestion.from_deal(1,self.discovery().deals[0])
        self.assertEqual(payload,self.suggestion)
        before=self.all_rows()['stickers'];deal=self.go(payload=payload)
        self.assertEqual((),self.discovery().deals)
        self.handler('accept_trade_request',deal)
        self.assert_accepted(deal)
        self.assertEqual((),self.discovery(NOW+timedelta(days=2)).deals)
        self.assertEqual(before,self.all_rows()['stickers'])

    def test_composite_expiry(self):
        self.configure(17,('vfl','em24'));original=self.discovery().deals
        before=self.all_rows()['stickers'];deal=self.bound()
        self.assertEqual((),self.discovery().deals)
        self.assertEqual(original,self.discovery(NOW+timedelta(hours=24,seconds=1)).deals)
        self.assert_terminal(deal,'expired');self.assertEqual(before,self.all_rows()['stickers'])

    def test_handler_decline(self):
        deal=self.bound();before=self.all_rows()['stickers']
        self.handler('decline_trade_request',deal);self.assert_terminal(deal,'declined')
        self.assertTrue(self.discovery().deals);self.assertEqual(before,self.all_rows()['stickers'])

    def test_handler_withdraw(self):
        deal=self.bound();self.handler('cancel_trade',deal,1);self.assert_terminal(deal,'cancelled')

    def test_legacy_decline_unchanged(self):
        rid=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,status) VALUES ('vfl',1,2,'[]','[]','open')").lastrowid;self.db.commit()
        from types import SimpleNamespace
        self.handler('decline_trade_request',SimpleNamespace(request_id=rid))
        self.assertEqual('declined',self.db.execute('SELECT status FROM trade_requests WHERE id=?',(rid,)).fetchone()[0])

    def test_expired_accept_without_sweep(self):
        deal=self.bound();self.handler('accept_trade_request',deal,now=NOW+timedelta(hours=24))
        self.assert_terminal(deal,'expired')

    def test_accepted_and_legacy_survive_cleanup(self):
        deal=self.bound();self.core().accept(deal.request_id,2);before=self.all_rows()
        runtime.cleanup(self.db,lambda:NOW+timedelta(days=2));self.assert_reopened(before)

    def test_unknown_contract_fails_closed(self):
        class Unknown:
            def execute(self,*args):return self
            def fetchone(self):return {'contract_type':'unknown'}
        with self.assertRaises(ValueError):runtime.dispatch_request(Unknown(),1,1,'accept')

    def test_cleanup_rollback_aborts_discovery(self):
        deal=self.bound();before=self.all_rows()
        with patch.object(SmartDealReleaseService,'_verify_released',side_effect=ValueError('injected')):
            with self.assertRaises(ValueError):self.discovery(NOW+timedelta(days=2))
        self.assert_reopened(before)

    def test_handler_decline_rollback(self):
        deal=self.bound();before=self.all_rows()
        with patch.object(SmartDealReleaseService,'_verify_released',side_effect=ValueError('injected')):
            self.assertEqual(409,self.handler('decline_trade_request',deal)[1])
        self.assert_reopened(before)

    def test_foreign_actor_no_mutation(self):
        deal=self.bound();before=self.all_rows()
        self.assertEqual(403,self.handler('cancel_trade',deal,3)[1]);self.assert_reopened(before)

    def test_cleanup_idempotent(self):
        deal=self.bound();self.discovery(NOW+timedelta(days=2));before=self.all_rows()
        self.discovery(NOW+timedelta(days=2));self.assert_reopened(before)


    def test_race_cleanup_accept(self):
        deal=self.bound();due=NOW+timedelta(days=2)
        self.race(lambda db:runtime.cleanup(db,lambda:due),
                  lambda db:runtime.dispatch_request(db,deal.request_id,2,'accept',catalog_provider=lambda a:self.catalog[a],now_provider=lambda:due))
        self.assert_terminal(deal,'expired')

    def test_race_accept_cleanup(self):
        deal=self.bound()
        self.race(lambda db:runtime.dispatch_request(db,deal.request_id,2,'accept',catalog_provider=lambda a:self.catalog[a],now_provider=lambda:NOW),
                  lambda db:runtime.cleanup(db,lambda:NOW+timedelta(days=2)))
        self.assert_accepted(deal)

    def test_race_cleanup_withdraw(self):
        deal=self.bound();due=NOW+timedelta(days=2)
        self.race(lambda db:runtime.cleanup(db,lambda:due),
                  lambda db:runtime.dispatch_request(db,deal.request_id,1,'withdraw',now_provider=lambda:due))
        self.assert_terminal(deal,'expired')

    def test_race_withdraw_cleanup(self):
        deal=self.bound()
        self.race(lambda db:runtime.dispatch_request(db,deal.request_id,1,'withdraw',now_provider=lambda:NOW),
                  lambda db:runtime.cleanup(db,lambda:NOW+timedelta(days=2)))
        self.assert_terminal(deal,'cancelled')

    def test_race_handler_decline_mutual_go(self):
        deal=self.bound()
        self.race(lambda db:self.handler('decline_trade_request',deal,db=db),
                  lambda db:self.core(db).go(self.suggestion,2))
        self.assert_terminal(deal,'declined')
        # Mutual after terminal may create a new pending instance, never revive old.
        self.assertEqual(0,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE status='accepted' AND contract_type='smartdeal_v1'").fetchone()[0])

    def test_race_mutual_go_handler_decline(self):
        deal=self.bound()
        self.race(lambda db:self.core(db).go(self.suggestion,2),
                  lambda db:self.handler('decline_trade_request',deal,db=db))
        self.assert_accepted(deal)

    def test_race_cleanup_new_binding(self):
        deal=self.bound();due=NOW+timedelta(days=2)
        _,new=self.race(lambda db:runtime.cleanup(db,lambda:due),
                        lambda db:self.service(db,now=due).create_from_suggestion(self.suggestion,1))
        self.assert_terminal(deal,'expired');self.assertNotEqual(deal.request_id,new.request_id)
        self.assertEqual('CREATED',new.code.value)

    def test_race_binding_cleanup(self):
        deal=self.bound();due=NOW+timedelta(days=2)
        first,_=self.race(lambda db:self.service(db,now=due).create_from_suggestion(self.suggestion,1),
                          lambda db:runtime.cleanup(db,lambda:due))
        self.assertNotEqual('CREATED',first.code.value);self.assert_terminal(deal,'expired')

    def test_existing_discovery_entry_cleans_before_projection(self):
        import webapp
        deal=self.bound();due=NOW+timedelta(days=2)
        real=runtime.cleanup
        with webapp.app.test_request_context('/album/vfl/smart-trades'), \
             patch.object(webapp,'current_user_id',return_value=1), \
             patch.object(webapp,'cleanup_smartdeal_runtime',side_effect=lambda c:real(c,lambda:due)):
            webapp.smart_trade_calculation(self.db,'vfl')
        self.assert_terminal(deal,'expired')

    def test_cleanup_preserves_foreign_valid_binding(self):
        old=self.bound();payload=self.package('other')
        newer=self.service(now=NOW+timedelta(hours=2)).create_from_suggestion(payload,1)
        runtime.cleanup(self.db,lambda:NOW+timedelta(hours=25))
        self.assert_terminal(old,'expired')
        self.assertEqual('open',self.db.execute('SELECT status FROM trade_requests WHERE id=?',(newer.request_id,)).fetchone()[0])
        self.assertTrue(all(r[0]=='active' for r in self.db.execute('SELECT state FROM trade_reservations WHERE trade_id=?',(newer.trade_id,))))


def blocked_test(handler):
    def test(self):
        deal=self.bound();self.core().accept(deal.request_id,2);before=self.all_rows()
        response=self.handler(handler,deal,form={'confirm_physical_arrival':'1'})
        self.assertEqual(409,response[1]);self.assert_reopened(before)
    return test

for name in ('confirm_trade_done','confirm_trade_shipping','confirm_trade_receipt','fail_trade_done',
             'report_trade_problem','close_trade_with_problem','resolve_trade_problem'):
    setattr(CoreGateTests,'test_blocked_'+name,blocked_test(name))
del name
