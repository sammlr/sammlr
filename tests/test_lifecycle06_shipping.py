"""Synthetic shipping boundary, exact debits, independent directions and races."""
import sqlite3,unittest,json
from datetime import timedelta
from unittest.mock import patch
from tests.test_lifecycle05_addresses import AddressTests
from services.trade_lifecycle_shipping import LifecycleShipping
from services.trade_lifecycle_addresses import LifecycleAddresses
from services.trade_lifecycle_preparation import LifecyclePreparation
from services.inventory import InventoryReadService
from services.inventory_write import InventoryWriteService
from App.Database.migration_runner import migrate,rollback


class ShippingTests(unittest.TestCase):
    connect=AddressTests.connect
    send=AddressTests.send
    stock=AddressTests.stock
    target=AddressTests.target
    race=AddressTests.race
    view=AddressTests.view
    call=AddressTests.call
    photo=AddressTests.photo
    both=AddressTests.both
    ready=AddressTests.ready
    larger=AddressTests.larger
    reduction=AddressTests.reduction
    book=AddressTests.book
    confirm=AddressTests.confirm
    released=AddressTests.released
    inventory=AddressTests.inventory
    def setUp(self):
        AddressTests.setUp(self);migrate(self.db,28)
        self.ship=LifecycleShipping(self.db,lambda:self.now)
    def qty(self,owner=1,code='1'):
        row=self.db.execute('SELECT quantity FROM stickers WHERE user_id=? AND album_id=\'vfl\' AND sticker_code=?',(owner,code)).fetchone()
        return row[0] if row else 0
    def shipping(self,actor=1,key='ship',revision=None):return self.ship.send_direction(self.t,actor,revision or self.rev,key)
    def rows(self,table):return [tuple(r) for r in self.db.execute('SELECT * FROM '+table)]
    def count(self,table):return self.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
    def event(self,kind):return self.db.execute('SELECT COUNT(*) FROM trade_events WHERE event_type=?',(kind,)).fetchone()[0]

    def test_deadline_exact_release_origin_boundary_overdue_no_mutations(self):
        self.now+=timedelta(hours=5);self.released();origin=self.now;before=self.inventory()
        self.now+=timedelta(hours=72)-timedelta(microseconds=1)
        v=self.ship.shipping_view(self.t,1);self.assertEqual((origin+timedelta(hours=72)).isoformat(),v['due_at'])
        self.assertEqual({'ready_to_ship'},{d['state'] for d in v['directions']})
        self.now+=timedelta(microseconds=1);v=self.ship.shipping_view(self.t,2)
        self.assertEqual({'overdue'},{d['state'] for d in v['directions']});self.assertEqual(0,v['remaining_seconds'])
        self.ship.shipping_view(self.t,1);self.assertEqual(2,self.event('ShippingOverdue'));self.assertEqual(before,self.inventory())
        self.assertEqual('accepted',self.db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0])
        self.shipping();self.assertEqual('sent',self.ship.shipping_view(self.t,1)['directions'][0]['state'])

    def test_happy_path_exact_sender_only_debit_availability_and_need(self):
        self.stock(1,'1',3);self.released();before=self.qty();partner=self.qty(2,'6')
        need=self.rows('lifecycle_need_claims');missing=self.rows('physical_missing_holds')
        supply=InventoryReadService(self.db).snapshot(1,'vfl',('1',)).sticker('1').available
        result=self.shipping()
        self.assertEqual(before-1,self.qty());self.assertEqual(partner,self.qty(2,'6'))
        self.assertEqual(need,self.rows('lifecycle_need_claims'));self.assertEqual(missing,self.rows('physical_missing_holds'))
        self.assertEqual(supply,InventoryReadService(self.db).snapshot(1,'vfl',('1',)).sticker('1').available)
        self.assertEqual(self.now.isoformat(),result['sent_at']);self.assertEqual(result['sent_at'],result['sender_confirmed_at'])
        self.assertEqual('SENDER_CONFIRMATION',result['source'])
        self.assertEqual([('released',),('active',)],[(r[0],) for r in self.db.execute('SELECT state FROM trade_reservations ORDER BY user_id')])
        self.assertEqual(1,self.event('DirectionSent'));self.assertEqual(1,self.count('lifecycle_movements'))
        self.assertEqual('partially_sent',self.ship.shipping_view(self.t,2)['shipping_state'])

    def test_both_sent_keep_all_need_bindings_and_no_credit(self):
        self.released();before=(self.qty(),self.qty(2,'6'));needs=self.rows('lifecycle_need_claims')
        self.shipping();self.shipping(2)
        self.assertEqual((before[0]-1,before[1]-1),(self.qty(),self.qty(2,'6')))
        self.assertEqual(0,self.qty(2,'1'));self.assertEqual(0,self.qty(1,'6'))
        self.assertEqual(needs,self.rows('lifecycle_need_claims'))
        self.assertEqual('in_transit',self.ship.shipping_view(self.t,1)['shipping_state'])
        self.assertEqual(['expected','expected'],[r[0] for r in self.db.execute('SELECT receipt_state FROM lifecycle_directions')])
        self.assertEqual('accepted',self.db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0])

    def test_retry_different_key_no_second_timestamp_event_notification(self):
        self.released();first=self.shipping();inventory=self.inventory();counts=[self.count(t) for t in ('lifecycle_movements','trade_events','notifications')]
        self.now+=timedelta(hours=1)
        self.assertEqual(first,self.shipping());self.assertEqual(first,self.shipping(key='different'))
        self.assertEqual(inventory,self.inventory());self.assertEqual(counts,[self.count(t) for t in ('lifecycle_movements','trade_events','notifications')])

    def test_wrong_actor_revision_pre_release_and_forged_source(self):
        with self.assertRaises(ValueError):self.shipping()
        self.released()
        for actor,rev in ((3,self.rev),(1,999)):
            with self.assertRaises(ValueError):self.ship.send_direction(self.t,actor,rev,'wrong')
        with self.ship.store.transaction():
            with self.assertRaises(ValueError):self.ship.finalize_direction_sent(self.t,1,self.rev,actor=2)
        self.assertEqual(0,self.count('lifecycle_shipping'))

    def test_multiquantity_reduced_revision_missing_hold_persists(self):
        # Create 3-per-direction, mark one truly missing, bilaterally reduce to 2.
        self.larger(3)
        position=self.view()['positions'][0]['id'];self.call('missing',data={'position':position,'quantity':1})
        proposal=self.reduction(2);self.call('reduction_approve',3,{'proposal':proposal})
        self.rev=self.view()['revision']
        for user in (1,3):self.photo(user);self.call('complete',user)
        for user in (1,3):self.call('approve',user)
        self.confirm(1);self.confirm(3)
        missing=self.rows('physical_missing_holds');before=self.qty(1,'11')
        self.shipping();self.assertEqual(before-2,self.qty(1,'11'))
        self.assertEqual(missing,self.rows('physical_missing_holds'))
        self.assertEqual(0,InventoryReadService(self.db).snapshot(1,'vfl',('11',)).sticker('11').available)
        self.assertEqual(2,self.db.execute('SELECT quantity FROM lifecycle_movements').fetchone()[0])

    def test_multi_position_atomic_rollback_on_second_inventory_write(self):
        from services.smartdeal_optimizer import SmartDealPiece as P
        t=self.service.create(1,3,(P('vfl','11'),P('vfl','12')),(P('vfl','16'),P('vfl','17')),'multi')
        self.t=t;self.rev=self.service._row(t)['revision_id'];self.acceptance.accept(t,3,self.rev,'accept-multi')
        for a in (1,3):self.photo(a);self.call('complete',a)
        for a in (1,3):self.call('approve',a)
        self.confirm();self.confirm(3);before=self.inventory()
        from services.history_cutover import HistoricalInventoryWriteService as W
        original=W.remove;calls=[]
        def failing(obj,*args,**kwargs):
            calls.append(1)
            if len(calls)==2:raise ValueError('synthetic injected failure')
            return original(obj,*args,**kwargs)
        with patch.object(W,'remove',failing):
            with self.assertRaises(ValueError):self.shipping()
        self.assertEqual(before,self.inventory());self.assertEqual(0,self.count('lifecycle_shipping'));self.assertEqual(0,self.count('lifecycle_movements'))
        self.shipping();self.assertEqual(2,self.count('lifecycle_movements'))

    def test_notification_failure_rolls_back_everything(self):
        self.released();before=self.inventory()
        with patch('services.trade_lifecycle_shipping.TypedNotificationService.create',side_effect=ValueError('synthetic failure')):
            with self.assertRaises(ValueError):self.shipping()
        self.assertEqual(before,self.inventory());self.assertEqual(0,self.event('DirectionSent'));self.assertEqual(0,self.count('lifecycle_movements'))

    def test_future_evidence_inside_external_transaction_then_manual_no_double_debit(self):
        # No release is fabricated: future full-package evidence can finalize before a click.
        before=self.qty()
        with self.ship.store.transaction():
            result=self.ship.finalize_direction_sent(self.t,1,self.rev,actor=2,source='RECEIPT_EVIDENCE')
            self.assertTrue(self.db.in_transaction)
            self.assertIsNone(result['sender_confirmed_at'])
            self.assertEqual(result,self.ship.finalize_direction_sent(self.t,1,self.rev,actor=2,source='RECEIPT_EVIDENCE'))
        self.assertEqual(0,self.count('lifecycle_address_releases'))
        self.assertEqual(before-1,self.qty());self.assertEqual(result,self.shipping())
        self.assertEqual(1,self.count('lifecycle_movements'));self.assertEqual('expected',self.db.execute('SELECT receipt_state FROM lifecycle_directions WHERE from_user_id=1').fetchone()[0])

    def test_primitive_requires_unit_of_work_and_outer_rollback(self):
        self.released();before=self.inventory()
        with self.assertRaises(ValueError):self.ship.finalize_direction_sent(self.t,1,self.rev,actor=1)
        with self.assertRaises(ValueError):
            with self.ship.store.transaction():
                self.ship.finalize_direction_sent(self.t,1,self.rev,actor=1)
                raise ValueError('outer rollback')
        self.assertEqual(before,self.inventory());self.assertEqual(0,self.count('lifecycle_shipping'))

    def test_no_normal_cancellation_or_amendment_after_sent(self):
        v=self.view();self.released();self.shipping();before=self.inventory()
        for who,action in ((1,'withdrawn'),(2,'rejected')):
            with self.assertRaises(ValueError):self.service.transition(self.t,who,action)
        for action in ('correct','complete','reduction_propose'):
            with self.assertRaises(ValueError):self.s.command(self.t,1,self.rev,v['basis'],'stale-'+action,action,{})
        with self.assertRaises(ValueError):self.confirm()
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:self.db.execute("UPDATE lifecycle_contracts SET state='ended' WHERE trade_id=?",(self.t,))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:self.db.execute("UPDATE lifecycle_directions SET shipping_state='not_sent' WHERE trade_id=? AND from_user_id=1",(self.t,))
        self.assertEqual(before,self.inventory())

    def test_parallel_same_sender_and_both_senders(self):
        self.released();before=self.qty()
        def send(actor,key):return lambda s:LifecycleShipping(s.db,lambda:self.now).send_direction(self.t,actor,self.rev,key)
        outcomes=self.race([send(1,'a'),send(1,'b')]);self.assertEqual(['ok','ok'],[r[0] for r in outcomes]);self.assertEqual(before-1,self.qty())
        outcomes=self.race([send(1,'retry'),send(2,'other')]);self.assertEqual(['ok','ok'],[r[0] for r in outcomes]);self.assertEqual(2,self.count('lifecycle_shipping'))

    def test_shipping_races_inventory_edit(self):
        self.released();self.stock(1,'1',3)
        def edit(s):
            with s.store.transaction():
                r=InventoryWriteService(s.db).set_quantity(1,'vfl','1',0)
                if not r.allowed:raise ValueError('bound stock')
        self.race([lambda s:LifecycleShipping(s.db,lambda:self.now).send_direction(self.t,1,self.rev,'ship'),edit])
        self.assertEqual(1,self.count('lifecycle_shipping'));self.assertIn(self.qty(),(0,2))
        self.assertEqual(1,self.count('lifecycle_movements'))

    def test_shipping_races_stale_address_and_reduction(self):
        v=self.a.view_address(self.t,1);entry=self.book();self.released()
        def addr(s):return LifecycleAddresses(s.db,lambda:self.now).confirm(self.t,1,self.rev,v['basis'],v['generation'],entry['id'],entry['version'],'stale')
        def reduce(s):return LifecyclePreparation(s.db,lambda:self.now).command(self.t,1,self.rev,v['basis'],'stale-reduce','reduction_propose',{})
        self.race([lambda s:LifecycleShipping(s.db,lambda:self.now).send_direction(self.t,1,self.rev,'ship'),addr,reduce])
        self.assertEqual(1,self.count('lifecycle_shipping'));self.assertEqual(1,self.count('lifecycle_movements'))

    def test_payloads_no_addresses_or_sticker_lists(self):
        self.released();self.shipping()
        payload=self.db.execute("SELECT payload_json FROM trade_events WHERE event_type='DirectionSent'").fetchone()[0]
        self.assertEqual({'revision_id','sender','source','sent_at'},set(json.loads(payload)))
        self.assertNotIn('Fixture Road',str(self.rows('notifications')));self.assertNotIn('Fixture Road',payload)

    def test_migration_empty_down_up_populated_refused(self):
        self.assertEqual((28,),rollback(self.db,27));self.assertEqual((28,),migrate(self.db,28))
        self.released();self.shipping()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,27)
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall());self.assertEqual('ok',self.db.execute('PRAGMA integrity_check').fetchone()[0])
