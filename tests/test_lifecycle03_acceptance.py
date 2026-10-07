"""Synthetic-only acceptance/counter contract and concurrency regression."""
import json,sqlite3,unittest
from datetime import timedelta
from unittest.mock import patch
from tests import test_lifecycle02_requests as fixtures
Piece=fixtures.Piece
from App.Database.migration_runner import migrate,rollback,current_version
from services.trade_lifecycle_acceptance import LifecycleAcceptance
from services.trade_lifecycle_foundation import RuleSnapshot,lifecycle_availability
from services.trade_v2_domain import TradeV2Domain


class AcceptanceTests(unittest.TestCase):
    connect=fixtures.RequestsTests.connect
    send=fixtures.RequestsTests.send
    target=fixtures.RequestsTests.target
    stock=fixtures.RequestsTests.stock
    counts=fixtures.RequestsTests.counts
    available=fixtures.RequestsTests.available
    race=fixtures.RequestsTests.race

    def setUp(self):
        fixtures.RequestsTests.setUp(self)
        migrate(self.db,25)
        self.acceptance=LifecycleAcceptance(self.db,lambda:self.now)

    def revision(self,t):return self.service._row(t)['revision_id']
    def accept(self,t,actor=2,key='accept',revision=None):
        return self.acceptance.accept(t,actor,revision or self.revision(t),key)
    def counter(self,t,actor=2,key='counter'):
        rev=self.revision(t);data=self.acceptance.preview_counter(t,actor,rev)
        return self.acceptance.counter(t,actor,rev,key,{k:data[k] for k in ('give','receive')})

    def test_accept_exact_revision_snapshot_and_bilateral_bindings(self):
        t=self.send();rev=self.revision(t)
        stocks=[tuple(r) for r in self.db.execute('SELECT * FROM stickers')]
        hold=self.db.execute('SELECT id FROM trade_reservations').fetchone()[0]
        self.assertEqual('accepted',self.accept(t)['status'])
        self.assertEqual((rev,'accepted'),tuple(self.db.execute('SELECT accepted_revision_id,state FROM lifecycle_contracts').fetchone()))
        self.assertEqual([(1,1),(2,1)],[tuple(r) for r in self.db.execute('SELECT user_id,quantity FROM trade_reservations ORDER BY user_id')])
        self.assertEqual(hold,self.db.execute('SELECT id FROM trade_reservations WHERE user_id=1').fetchone()[0])
        self.assertEqual(['committed','committed'],[r[0] for r in self.db.execute('SELECT state FROM lifecycle_need_claims')])
        self.assertEqual(0,lifecycle_availability(self.db,2,'vfl','1').free_need)
        self.assertEqual(0,self.available().free_need)
        self.assertEqual(['ready','ready'],[r[0] for r in self.db.execute('SELECT preparation_state FROM lifecycle_directions')])
        self.assertEqual(stocks,[tuple(r) for r in self.db.execute('SELECT * FROM stickers')])

    def test_retry_and_different_command_do_not_reaccept(self):
        t=self.send();first=self.accept(t)
        self.assertEqual(first,self.accept(t))
        self.assertEqual('already_accepted',self.accept(t,key='other')['status'])
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_acceptances').fetchone()[0])

    def test_wrong_roles_and_revision(self):
        t=self.send()
        for actor in (1,3):
            with self.assertRaises(ValueError):self.accept(t,actor)
        with self.assertRaises(ValueError):self.accept(t,revision=999)
        self.assertIsNone(self.service._row(t)['accepted_revision_id'])

    def test_expired_withdrawn_rejected_not_accepted(self):
        for action in ('withdrawn','rejected','expired'):
            with self.subTest(action=action):
                t=self.send(action,partner=2)
                if action=='expired':self.now+=timedelta(hours=72)
                else:self.service.transition(t,1 if action=='withdrawn' else 2,action)
                self.assertEqual(action,self.accept(t,key=action)['status'])
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_acceptances').fetchone()[0])

    def test_no_request_release_or_expiry_after_acceptance(self):
        t=self.send();self.accept(t)
        for actor,action in ((1,'withdrawn'),(2,'rejected')):
            with self.assertRaises(ValueError):self.service.transition(t,actor,action)
        self.now+=timedelta(days=5);self.assertEqual(0,self.service.expire())
        self.assertEqual('accepted',self.service.view(1,t)[0]['status'])

    def test_disappeared_recipient_supply_leaves_original_open(self):
        t=self.send();self.stock(2,'6',1)
        self.assertEqual('not_possible',self.accept(t)['status'])
        self.assertEqual('open',self.service._row(t)['status'])
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_rule_snapshots').fetchone()[0])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])

    def test_need_filled_after_send_no_acceptance(self):
        t=self.send()
        self.db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (2,'vfl','1',1,0)");self.db.commit()
        self.assertEqual('not_possible',self.accept(t)['status'])

    def test_sender_need_filled_no_self_credit_overcoverage(self):
        t=self.send();self.target(1,'6',0)
        self.assertEqual('not_possible',self.accept(t)['status'])

    def test_unrelated_stock_change_does_not_invalidate(self):
        t=self.send();self.stock(3,'16',1)
        self.assertEqual('accepted',self.accept(t)['status'])

    def test_pool_change_invalidates_before_acceptance(self):
        t=self.send();self.db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2');self.db.commit()
        self.assertEqual('not_possible',self.accept(t)['status'])

    def test_cross_snapshot_survives_global_change(self):
        for user in (1,2):self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled,cross_album_mode) VALUES (?,'em24',1,'CROSS_ALBUM_ALLOWED')",(user,))
        self.db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED'")
        self.db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (2,'em24','TOPPS 1',2,1)");self.db.commit()
        t=self.service.create(1,2,(Piece('vfl','1'),),(Piece('em24','TOPPS 1'),),'cross')
        self.assertEqual('accepted',self.accept(t)['status'])
        payload=self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0]
        self.db.execute("UPDATE user_albums SET cross_album_mode='SAME_ALBUM_ONLY'");self.db.commit()
        self.assertEqual(payload,self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0])
        rules=RuleSnapshot.loads(payload);rules.validate([(1,2,'vfl','1',1),(2,1,'em24','TOPPS 1',1)])
        self.assertEqual('accepted',self.service.view(1,t)[0]['status'])
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE lifecycle_rule_snapshots SET payload_json='{}'")

    def test_asymmetric_manual_perspective(self):
        t=self.service.create(1,2,(Piece('vfl','1'),Piece('vfl','2')),(Piece('vfl','6'),),'asymmetric')
        self.assertEqual('accepted',self.accept(t)['status'])
        snapshot=RuleSnapshot.loads(self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0])
        self.assertEqual(1,snapshot.proposer);self.assertFalse(snapshot.equal)

    def test_accept_failure_rolls_back_all_new_bindings(self):
        t=self.send()
        with patch.object(self.acceptance.store,'store_rule_snapshot',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):self.accept(t)
        self.assertEqual('open',self.service._row(t)['status'])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])
        self.assertEqual(['pending'],[r[0] for r in self.db.execute('SELECT state FROM lifecycle_need_claims')])

    def test_counter_roles_timer_bindings_and_same_acceptance(self):
        t=self.send();old=self.revision(t);self.now+=timedelta(hours=20)
        data=self.counter(t);new=data['revision'];self.assertNotEqual(old,new)
        rows=self.db.execute('SELECT status,sender_user_id,created_at,expires_at FROM lifecycle_requests ORDER BY revision_id').fetchall()
        self.assertEqual(('superseded',1),tuple(rows[0][:2]));self.assertEqual(('open',2),tuple(rows[1][:2]))
        from services.trade_lifecycle_requests import instant
        self.assertEqual(timedelta(hours=72),instant(rows[1]['expires_at'])-self.now)
        self.assertEqual({2},{r[0] for r in self.db.execute("SELECT user_id FROM trade_reservations WHERE state='active'")})
        with self.assertRaises(ValueError):self.accept(t,2)
        self.assertEqual('accepted',self.accept(t,1)['status'])
        self.assertEqual(new,self.db.execute('SELECT accepted_revision_id FROM lifecycle_contracts').fetchone()[0])
        self.assertEqual(2,RuleSnapshot.loads(self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0]).proposer)

    def test_counter_preview_does_not_replace_or_bind(self):
        t=self.send();before=self.counts();self.acceptance.preview_counter(t,2,self.revision(t))
        self.assertEqual(before,self.counts());self.assertEqual(1,self.service._row(t)['sender_user_id'])

    def test_counter_retry_and_second_counter_forbidden(self):
        t=self.send();rev=self.revision(t);preview=self.acceptance.preview_counter(t,2,rev)
        proposal={k:preview[k] for k in ('give','receive')}
        first=self.acceptance.counter(t,2,rev,'same',proposal)
        self.assertEqual(first,self.acceptance.counter(t,2,rev,'same',proposal))
        with self.assertRaises(ValueError):self.counter(t,1)
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])

    def test_invalid_counter_ends_without_third_revision(self):
        t=self.send();self.counter(t)
        # Counter computes all five available pairs; destroy one now-unheld supply of A.
        self.stock(1,'1',1)
        self.assertEqual('invalidated',self.accept(t,1)['status'])
        self.assertEqual(0,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])
        self.assertEqual(0,self.db.execute("SELECT COUNT(*) FROM lifecycle_need_claims WHERE state<>'released'").fetchone()[0])
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])

    def test_counter_rejection_releases_all(self):
        t=self.send();self.counter(t);self.service.transition(t,1,'rejected')
        self.assertEqual(0,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])
        self.assertEqual('rejected',self.service.view(2,t)[0]['status'])

    def test_counter_failure_restores_original(self):
        t=self.send();rev=self.revision(t);preview=self.acceptance.preview_counter(t,2,rev)
        with patch.object(self.acceptance,'_event',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):self.acceptance.counter(t,2,rev,'counter',{k:preview[k] for k in ('give','receive')})
        self.assertEqual(rev,self.revision(t));self.assertEqual('open',self.service._row(t)['status'])
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_stale_counter_preview_no_silent_change(self):
        t=self.send();rev=self.revision(t);preview=self.acceptance.preview_counter(t,2,rev)
        self.stock(2,'7',1)
        with self.assertRaises(ValueError):self.acceptance.counter(t,2,rev,'counter',{k:preview[k] for k in ('give','receive')})
        self.assertEqual(rev,self.revision(t))

    def test_parallel_accept_accept(self):
        t=self.send();rev=self.revision(t)
        def run(s):return LifecycleAcceptance(s.db,lambda:self.now).accept(t,2,rev,'same')
        results=self.race([run,run]);self.assertEqual(results[0],results[1])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_acceptances').fetchone()[0])

    def test_parallel_accept_withdraw(self):
        t=self.send();rev=self.revision(t)
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(t,2,rev,'accept'),lambda s:s.transition(t,1,'withdrawn')])
        status=self.service._row(t)['status'];self.assertIn(status,('accepted','withdrawn'))
        self.assertEqual(2 if status=='accepted' else 0,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_parallel_accept_expiry(self):
        t=self.send();rev=self.revision(t);self.now+=timedelta(hours=72)
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(t,2,rev,'accept'),lambda s:s.expire()])
        self.assertEqual('expired',self.service._row(t)['status'])

    def test_accepted_revision_and_rows_immutable(self):
        t=self.send();self.accept(t)
        for sql in ['UPDATE lifecycle_contracts SET accepted_revision_id=NULL','UPDATE lifecycle_revision_positions SET quantity=3','UPDATE lifecycle_acceptances SET accepted_by=1']:
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
            self.db.rollback()

    def test_migration_preserves_existing_request(self):
        # Empty down/up is safe; populated rollback is rejected.
        self.assertEqual((25,),rollback(self.db,24));t=self.send();old=dict(self.service._row(t))
        self.assertEqual((25,),migrate(self.db,25));self.assertEqual(old,dict(self.service._row(t)))
        self.assertEqual('accepted',self.accept(t)['status'])
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,24)
        self.assertEqual(25,current_version(self.db))

    def test_small_counter_keeps_smart_origin_and_initial_minimum(self):
        give=tuple(Piece('vfl',str(n)) for n in range(1,6))
        receive=tuple(Piece('vfl',str(n)) for n in range(6,11))
        t=self.service.create(1,2,give,receive,'smart',origin='SMARTDEAL')
        for code in ('7','8','9','10'):self.stock(2,code,1)
        self.assertEqual('not_possible',self.accept(t)['status'])
        self.counter(t)
        self.assertEqual('SMARTDEAL',self.service._row(t)['origin'])
        self.assertEqual(2,len(self.acceptance._positions(self.revision(t))))
        self.assertEqual('accepted',self.accept(t,1,key='counter-accept')['status'])

    def test_two_acceptances_compete_for_last_recipient_supply(self):
        a=self.send()
        b=self.service.create(3,2,(Piece('vfl','16'),),(Piece('vfl','6'),),'other')
        ra,rb=self.revision(a),self.revision(b)
        results=self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(a,2,ra,'a'),
                           lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(b,2,rb,'b')])
        self.assertEqual(['accepted','not_possible'],sorted(v['status'] for _,v in results))
        self.assertEqual(1,self.db.execute("SELECT SUM(quantity) FROM trade_reservations WHERE user_id=2 AND sticker_code='6' AND state='active'").fetchone()[0])

    def test_two_acceptances_compete_for_same_recipient_need(self):
        self.db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (3,'vfl','1',2,1)");self.db.commit()
        a=self.send();b=self.service.create(3,2,(Piece('vfl','1'),),(Piece('vfl','7'),),'other')
        ra,rb=self.revision(a),self.revision(b)
        results=self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(a,2,ra,'a'),
                           lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(b,2,rb,'b')])
        self.assertEqual(['accepted','not_possible'],sorted(v['status'] for _,v in results))
        self.assertEqual(0,lifecycle_availability(self.db,2,'vfl','1').free_need)

    def test_parallel_accept_reject(self):
        t=self.send();rev=self.revision(t)
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(t,2,rev,'a'),lambda s:s.transition(t,2,'rejected')])
        self.assertIn(self.service._row(t)['status'],('accepted','rejected'))

    def test_parallel_counter_doubleclick_and_expiry(self):
        t=self.send();rev=self.revision(t);p=self.acceptance.preview_counter(t,2,rev);proposal={k:p[k] for k in ('give','receive')}
        def run(s):return LifecycleAcceptance(s.db,lambda:self.now).counter(t,2,rev,'same',proposal)
        results=self.race([run,run]);self.assertEqual(results[0],results[1])
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])
        self.now+=timedelta(hours=72)
        self.assertEqual(1,self.service.expire());self.assertEqual('expired',self.service._row(t)['status'])

    def test_parallel_counter_withdraw(self):
        t=self.send();rev=self.revision(t);p=self.acceptance.preview_counter(t,2,rev);proposal={k:p[k] for k in ('give','receive')}
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).counter(t,2,rev,'counter',proposal),lambda s:s.transition(t,1,'withdrawn')])
        row=self.service._row(t)
        self.assertTrue((row['status']=='withdrawn' and row['revision_id']==rev) or (row['status']=='open' and row['sender_user_id']==2))

    def test_counter_accept_vs_guarded_inventory_write(self):
        from services.inventory_write import InventoryWriteService
        t=self.send();self.counter(t);rev=self.revision(t)
        def stock(s):
            s.db.execute('BEGIN IMMEDIATE')
            try:
                result=InventoryWriteService(s.db).set_quantity(1,'vfl','1',1)
                s.db.commit();return result.quantity
            except BaseException:s.db.rollback();raise
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(t,1,rev,'accept'),stock])
        row=self.service._row(t)
        self.assertIn(row['status'],('accepted','invalidated'))
        quantity=self.db.execute("SELECT quantity FROM stickers WHERE user_id=1 AND sticker_code='1'").fetchone()[0]
        self.assertEqual(2 if row['status']=='accepted' else 1,quantity)

    def test_legacy_contract_cannot_enter_acceptance(self):
        request=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,status) VALUES ('vfl',1,2,'open')").lastrowid
        trade=self.db.execute("INSERT INTO trades(legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (?,1,2,'open')",(request,)).lastrowid
        self.db.commit()
        with self.assertRaises(ValueError):self.acceptance.accept(trade,2,1,'legacy')
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_rule_snapshots').fetchone()[0])

    def test_twenty_to_seventeen_never_silently_shrinks(self):
        self.db.execute('DELETE FROM stickers WHERE user_id IN (1,2)')
        for user,start in ((1,1),(2,21)):
            self.db.executemany("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'vfl',?,2,1)",[(user,str(n)) for n in range(start,start+20)])
        self.db.commit()
        t=self.service.create(1,2,tuple(Piece('vfl',str(n)) for n in range(1,21)),tuple(Piece('vfl',str(n)) for n in range(21,41)),'twenty',origin='SMARTDEAL')
        rev=self.revision(t)
        for code in ('21','22','23'):self.stock(2,code,1)
        self.assertEqual('not_possible',self.accept(t)['status'])
        self.assertEqual(40,len(self.acceptance._positions(rev)))
        preview=self.acceptance.preview_counter(t,2,rev)
        self.assertEqual(17,sum(p[2] for p in preview['give']))
        self.assertEqual(17,sum(p[2] for p in preview['receive']))
        self.assertEqual(rev,self.revision(t))

    def test_counter_sender_three_limit_preserves_original(self):
        t=self.send();rev=self.revision(t)
        for partner,give,receive in ((3,'7','16'),(4,'8','26'),(5,'9','36')):
            self.service.create(2,partner,(Piece('vfl',give),),(Piece('vfl',receive),),str(partner))
        preview=self.acceptance.preview_counter(t,2,rev)
        with self.assertRaisesRegex(ValueError,'drei'):
            self.acceptance.counter(t,2,rev,'counter',{k:preview[k] for k in ('give','receive')})
        self.assertEqual(rev,self.revision(t));self.assertEqual('open',self.service._row(t)['status'])

    def test_counter_vs_expiry_has_one_terminal_transition(self):
        t=self.send();rev=self.revision(t);p=self.acceptance.preview_counter(t,2,rev);proposal={k:p[k] for k in ('give','receive')}
        self.now+=timedelta(hours=72)
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).counter(t,2,rev,'c',proposal),lambda s:s.expire()])
        self.assertEqual('expired',self.service._row(t)['status'])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM trade_events').fetchone()[0])

    def test_counter_vs_reject_has_no_partial_bindings(self):
        t=self.send();rev=self.revision(t);p=self.acceptance.preview_counter(t,2,rev);proposal={k:p[k] for k in ('give','receive')}
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).counter(t,2,rev,'c',proposal),lambda s:s.transition(t,2,'rejected')])
        row=self.service._row(t)
        self.assertIn(row['status'],('open','rejected'))
        owners={r[0] for r in self.db.execute("SELECT user_id FROM trade_reservations WHERE state='active'")}
        self.assertEqual({2} if row['status']=='open' else set(),owners)

    def test_counter_vs_guarded_inventory_change(self):
        from services.inventory_write import InventoryWriteService
        t=self.send();rev=self.revision(t);p=self.acceptance.preview_counter(t,2,rev);proposal={k:p[k] for k in ('give','receive')}
        def stock(s):
            s.db.execute('BEGIN IMMEDIATE')
            try:
                result=InventoryWriteService(s.db).set_quantity(2,'vfl','6',1)
                s.db.commit();return result.quantity
            except BaseException:s.db.rollback();raise
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).counter(t,2,rev,'c',proposal),stock])
        row=self.service._row(t)
        quantity=self.db.execute("SELECT quantity FROM stickers WHERE user_id=2 AND sticker_code='6'").fetchone()[0]
        self.assertEqual(1 if row['revision_id']==rev else 2,quantity)

    def test_counter_accept_vs_another_acceptance(self):
        # After the counter A's supply is free; another open request may ask for it.
        t=self.send();self.counter(t);rev=self.revision(t)
        other=self.service.create(3,1,(Piece('vfl','16'),),(Piece('vfl','1'),),'other')
        other_rev=self.revision(other)
        self.race([lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(t,1,rev,'a'),
                   lambda s:LifecycleAcceptance(s.db,lambda:self.now).accept(other,1,other_rev,'b')])
        statuses=[self.service._row(t)['status'],self.service._row(other)['status']]
        self.assertEqual(1,statuses.count('accepted'))
        self.assertEqual(1,self.db.execute("SELECT SUM(quantity) FROM trade_reservations WHERE user_id=1 AND sticker_code='1' AND state='active'").fetchone()[0])

    def test_snapshot_frozen_current_rules_still_apply_to_new_offers(self):
        t=self.send();self.accept(t)
        snapshot=self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0]
        self.db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2');self.db.commit()
        self.assertEqual(snapshot,self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0])
        self.assertEqual('accepted',self.service.view(1,t)[0]['status'])
        with self.assertRaises(ValueError):self.service.create(1,2,(Piece('vfl','2'),),(Piece('vfl','7'),),'new')

if __name__=='__main__':unittest.main()
