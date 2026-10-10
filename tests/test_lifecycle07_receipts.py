"""Synthetic V1 receipt inventory, ownership, serialization and rollback contracts."""
import json
import sqlite3
import unittest
from datetime import timedelta
from unittest.mock import patch
from tests import test_lifecycle06_shipping as fixtures
from services.trade_lifecycle_receipts import LifecycleReceipts, COUNTS
from services.trade_lifecycle_shipping import LifecycleShipping
from services.trade_lifecycle_foundation import lifecycle_availability
from services.history_cutover import HistoricalInventoryWriteService
from App.Database.migration_runner import migrate, rollback


class ReceiptTests(unittest.TestCase):
    for _name in ('connect','send','stock','target','race','view','call','photo','both','ready','larger',
                  'reduction','book','confirm','released','inventory','qty','rows','count','event','shipping'):
        locals()[_name] = getattr(fixtures.ShippingTests, _name)

    def setUp(self):
        fixtures.ShippingTests.setUp(self)
        migrate(self.db,29)
        self.r = LifecycleReceipts(self.db,lambda:self.now)

    def released(self):
        if self.r._released(self.t):
            return self.a.view_address(self.t, 1)
        participants = sorted({p['from_user_id'] for p in self.r._positions(self.rev)})
        for actor in participants:
            cycle = next(c for c in self.view(actor)['cycles'] if c['owner_id'] == actor)
            if not cycle['completed_at']:
                self.photo(actor); self.call('complete', actor)
        for actor in participants:
            other = next(c for c in self.view(actor)['cycles'] if c['owner_id'] != actor)
            if other['review_state'] != 'approved':
                self.call('approve', actor)
        for actor in participants:
            self.confirm(actor)
        return self.a.view_address(self.t, 1)

    def inspect(self, **changes):
        p=next(p for p in self.r._positions(self.rev) if p['from_user_id']==1)
        return [dict(position=p['id'],wrong_code='',**{k:0 for k in COUNTS}) | {'correct':p['quantity']} | changes]

    def receive(self, inspection=None, actor=2, key='receipt', sender=1, revision=None):
        return self.r.confirm_receipt(self.t,actor,sender,revision or self.rev,key,inspection)

    def snapshot(self):
        return {t:self.rows(t) for t in ('stickers','trade_reservations','lifecycle_need_claims','lifecycle_movements',
            'lifecycle_shipping','lifecycle_receipts','lifecycle_directions','lifecycle_commands','trade_events','notifications',
            'lifecycle_delivery_problems','lifecycle_delivery_responses')}

    def test_complete_exact_credit_no_second_debit_and_other_direction_unchanged(self):
        self.released()
        self.released();self.shipping();before=self.qty();other=self.rows('lifecycle_directions')[1]
        result=self.receive()
        self.assertEqual(before,self.qty());self.assertEqual(1,self.qty(2,'1'))
        self.assertEqual(other,self.rows('lifecycle_directions')[1])
        self.assertEqual('received_complete',self.rows('lifecycle_directions')[0][-1])
        self.assertEqual(self.now.isoformat(),result['received_at'])
        self.assertEqual(0,lifecycle_availability(self.db,2,'vfl','1').committed)
        self.assertEqual('accepted',self.db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0])

    def test_systemic_after_address_release_then_manual_sent_is_idempotent(self):
        self.released()
        before=self.qty();result=self.receive();sent=self.rows('lifecycle_shipping')[0]
        self.assertEqual(before-1,self.qty());self.assertEqual(1,self.qty(2,'1'))
        self.assertIsNone(sent[4]);self.assertEqual('RECEIPT_EVIDENCE',sent[5])
        self.assertEqual(1,self.count('lifecycle_address_releases'))
        self.now+=timedelta(hours=3);snapshot=self.inventory();self.shipping()
        self.assertEqual(snapshot,self.inventory());self.assertEqual(sent,self.rows('lifecycle_shipping')[0])
        self.assertEqual(1,self.event('DirectionSent'));self.assertEqual(1,self.event('ReceiptComplete'))

    def test_partial_quantity_three_accepted_two_and_remaining_claim_one(self):
        self.larger(3);self.released();before=self.qty(1,'11')
        self.receive(self.inspect(correct=2,missing=1),actor=3)
        self.assertEqual(before-3,self.qty(1,'11'));self.assertEqual(2,self.qty(3,'11'))
        a=lifecycle_availability(self.db,3,'vfl','11')
        self.assertEqual((2,1,0),(a.physical,a.committed,a.free_need))
        self.assertEqual(1,self.count('lifecycle_delivery_problems'));self.assertEqual(1,self.event('ReceiptPartial'))
        self.assertEqual('received_with_problem',self.rows('lifecycle_directions')[-2][-1])

    def test_damaged_explicitly_accepted_and_auditable(self):
        self.larger(3);self.released()
        data=self.inspect(correct=1,damaged_accepted=2)
        self.receive(data,actor=3,key='damage')
        self.assertEqual(3,self.qty(3,'11'))
        saved=self.r._receipt(self.t,1)
        self.assertTrue(saved['has_problem']);self.assertEqual(data,json.loads(saved['inspection_json']))

    def test_damage_rejected_no_credit(self):
        self.released()
        self.receive(self.inspect(correct=0,damaged_rejected=1))
        self.assertEqual(0,self.qty(2,'1'));self.assertEqual(1,lifecycle_availability(self.db,2,'vfl','1').committed)

    def test_wrong_code_documented_but_neither_expected_nor_wrong_is_credited(self):
        self.released()
        before=self.qty(2,'2');self.receive(self.inspect(correct=0,wrong=1,wrong_code='2'))
        self.assertEqual(0,self.qty(2,'1'));self.assertEqual(before,self.qty(2,'2'))
        self.assertEqual('2',json.loads(self.r._receipt(self.t,1)['inspection_json'])[0]['wrong_code'])

    def test_wrong_optional_code_must_be_catalog_member_and_actual_deviation(self):
        self.released()
        for code in ('foreign-secret-code','1','<script>'):
            with self.assertRaises(ValueError):self.receive(self.inspect(correct=0,wrong=1,wrong_code=code))
        with self.assertRaises(ValueError):self.receive(self.inspect(wrong_code='2'))
        self.assertEqual(0,self.count('lifecycle_shipping'))

    def test_partition_integer_bounds_and_foreign_positions(self):
        self.released()
        for change in ({'correct':-1},{'correct':2},{'correct':True},{'correct':0.5},{'correct':'1'},
                       {'correct':0},{'missing':1},{'position':999},{'position':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.receive(self.inspect(**change))
        for data in ([],self.inspect()*2,{'correct':1}):
            with self.assertRaises(ValueError):self.receive(data)
        self.assertEqual(0,self.count('lifecycle_movements'))

    def test_ownership_revision_and_manipulated_direction(self):
        self.released()
        for actor,sender,rev in ((1,1,self.rev),(3,1,self.rev),(2,2,self.rev),(2,999,self.rev),(2,1,999)):
            with self.assertRaises(ValueError):self.receive(actor=actor,sender=sender,revision=rev)
        with self.assertRaises(ValueError):self.r.confirm_receipt(999,2,1,self.rev,'foreign')
        self.assertEqual(0,self.count('lifecycle_receipts'))

    def test_identical_retries_keys_payload_conflicts_and_no_undo(self):
        self.released()
        result=self.receive();before=self.inventory();counts=(self.count('trade_events'),self.count('notifications'))
        self.assertEqual(result,self.receive());self.assertEqual(result,self.receive(key='second'))
        self.assertEqual(before,self.inventory());self.assertEqual(counts,(self.count('trade_events'),self.count('notifications')))
        with self.assertRaises(ValueError):self.receive(self.inspect(correct=0,missing=1))
        with self.assertRaises(ValueError):self.receive(self.inspect(correct=0,missing=1),key='new')
        for sql in ('DELETE FROM lifecycle_receipts','UPDATE lifecycle_receipts SET has_problem=1',
                    "UPDATE trade_events SET payload_json='{}' WHERE event_type='ReceiptComplete'",
                    "DELETE FROM trade_events WHERE event_type='ReceiptComplete'",
                    "INSERT OR REPLACE INTO trade_events SELECT * FROM trade_events WHERE event_type='ReceiptComplete'",
                    "UPDATE lifecycle_directions SET receipt_state='expected' WHERE from_user_id=1"):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
            self.db.rollback()

    def test_seven_day_boundary_no_inventory_write_and_retry(self):
        self.released()
        self.released();self.shipping();before=self.inventory();origin=self.now
        self.now=origin+timedelta(days=7)-timedelta(microseconds=1)
        with self.assertRaises(ValueError):self.r.report_non_arrival(self.t,2,1,self.rev,'early')
        self.assertFalse(self.r.receipt_view(self.t,2)['directions'][0]['can_non_arrival'])
        self.now+=timedelta(microseconds=1)
        self.assertTrue(self.r.receipt_view(self.t,2)['directions'][0]['can_non_arrival'])
        first=self.r.report_non_arrival(self.t,2,1,self.rev,'late')
        self.assertEqual(first,self.r.report_non_arrival(self.t,2,1,self.rev,'other'))
        self.assertEqual(before,self.inventory());self.assertEqual(1,self.event('NonArrivalReported'))
        self.assertEqual('accepted',self.db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0])

    def test_nonarrival_without_manual_sent_and_after_receipt_rejected(self):
        self.released()
        with self.assertRaises(ValueError):self.r.report_non_arrival(self.t,2,1,self.rev,'no-sent')
        self.receive();self.now+=timedelta(days=8)
        with self.assertRaises(ValueError):self.r.report_non_arrival(self.t,2,1,self.rev,'received')

    def nonarrival(self):
        self.released();self.shipping();self.now+=timedelta(days=7)
        return self.r.report_non_arrival(self.t,2,1,self.rev,'nonarrival')['problem']

    def test_late_complete_preserves_history_and_problem_evidence(self):
        self.released()
        p=self.nonarrival();self.receive()
        self.assertEqual(1,self.qty(2,'1'));self.assertEqual(1,self.event('LateArrivalReported'))
        self.assertEqual(1,self.event('NonArrivalReported'));self.assertEqual(p,self.rows('lifecycle_delivery_problems')[0][0])
        self.assertTrue(self.r.receipt_view(self.t,2)['directions'][0]['problems'][0]['superseded'])

    def test_late_problem_separate_evidence_and_no_phantom_credit(self):
        self.released()
        self.nonarrival();self.receive(self.inspect(correct=0,wrong=1))
        self.assertEqual(2,self.count('lifecycle_delivery_problems'));self.assertEqual(0,self.qty(2,'1'))
        self.assertEqual('received_with_problem',self.rows('lifecycle_directions')[0][-1])

    def test_sender_response_once_no_inventory_or_problem_resolution(self):
        self.released()
        self.receive(self.inspect(correct=0,missing=1));p=self.rows('lifecycle_delivery_problems')[0][0];before=self.inventory()
        def respond(response='acknowledge',actor=1,key='respond',problem=p):
            return self.r.respond(self.t,actor,1,self.rev,problem,response,key)
        for actor in (2,3):
            with self.assertRaises(ValueError):respond(actor=actor)
        with self.assertRaises(ValueError):respond(problem=999)
        first=respond();self.assertEqual(first,respond());self.assertEqual(first,respond(key='again'))
        with self.assertRaises(ValueError):respond('sent_correctly',key='conflict')
        self.assertEqual(before,self.inventory());self.assertEqual(1,self.event('SenderProblemResponse'))
        self.assertEqual('received_with_problem',self.rows('lifecycle_directions')[0][-1])

    def test_sender_correctly_sent_response_and_stale_nonarrival_response(self):
        self.released()
        p=self.nonarrival();self.receive()
        with self.assertRaises(ValueError):self.r.respond(self.t,1,1,self.rev,p,'sent_correctly','stale')

    def test_both_receipts_never_complete_trade(self):
        self.released()
        self.receive();self.receive(actor=1,sender=2)
        self.assertEqual(['received_complete']*2,[r[-1] for r in self.rows('lifecycle_directions')])
        self.assertEqual('accepted',self.db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0])

    def test_review_has_no_writes(self):
        self.released()
        before=self.snapshot();self.r.review_receipt(self.t,2,1,self.rev)
        self.assertEqual(before,self.snapshot())

    def test_reduced_revision_is_only_authority(self):
        self.larger(3);old=self.rev;proposal=self.reduction(2);self.call('reduction_approve',3,{'proposal':proposal})
        self.rev=self.view()['revision'];self.released()
        with self.assertRaises(ValueError):self.receive(actor=3,revision=old)
        self.receive(actor=3);self.assertEqual(2,self.qty(3,'11'));self.assertEqual(2,self.qty(1,'11'))

    def test_rollbacks_sender_receiver_claim_history_notification_and_command(self):
        self.released()
        failure_points=('sender','receiver','claim','history','notification','command')
        for point in failure_points:
            with self.subTest(point=point):
                before=self.snapshot()
                if point in ('claim','history','command'):
                    table={'claim':'lifecycle_need_claims','history':'trade_events','command':'lifecycle_commands'}[point]
                    action='UPDATE' if point=='claim' else 'INSERT'
                    self.db.execute(f"CREATE TEMP TRIGGER fail_receipt BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'synthetic'); END")
                    try:
                        with self.assertRaises(sqlite3.IntegrityError):self.receive()
                    finally:self.db.execute('DROP TRIGGER fail_receipt')
                else:
                    target={'sender':'services.trade_lifecycle_shipping.HistoricalInventoryWriteService.remove',
                            'receiver':'services.trade_lifecycle_receipts.HistoricalInventoryWriteService.set_quantity',
                            'notification':'services.trade_lifecycle_receipts.TypedNotificationService.create'}[point]
                    with patch(target,side_effect=ValueError('synthetic')):
                        with self.assertRaises(ValueError):self.receive()
                self.assertEqual(before,self.snapshot())

    def test_parallel_receipts_and_manual_sent_exactly_once(self):
        self.released()
        self.released();before=self.qty()
        def receipt(key):return lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,key)
        outcomes=self.race([receipt('a'),receipt('b'),lambda s:LifecycleShipping(s.db,lambda:self.now).send_direction(self.t,1,self.rev,'ship')])
        self.assertEqual(['ok']*3,[r[0] for r in outcomes]);self.assertEqual(before-1,self.qty());self.assertEqual(1,self.qty(2,'1'))
        self.assertEqual(1,self.event('DirectionSent'));self.assertEqual(1,self.count('lifecycle_receipts'))

    def test_parallel_nonarrival_and_receipt(self):
        self.released()
        self.released();self.shipping();self.now+=timedelta(days=7)
        self.race([lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'receipt'),
                   lambda s:LifecycleReceipts(s.db,lambda:self.now).report_non_arrival(self.t,2,1,self.rev,'nonarrival')])
        self.assertEqual(1,self.qty(2,'1'));self.assertEqual('received_complete',self.rows('lifecycle_directions')[0][-1])

    def test_response_races_late_arrival(self):
        self.released()
        p=self.nonarrival()
        self.race([lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'receipt'),
                   lambda s:LifecycleReceipts(s.db,lambda:self.now).respond(self.t,1,1,self.rev,p,'acknowledge','response')])
        self.assertEqual(1,self.qty(2,'1'));self.assertIn(self.count('lifecycle_delivery_responses'),(0,1))

    def test_migration_empty_down_up_and_populated_refusal(self):
        self.released()
        self.assertEqual((29,),rollback(self.db,28));self.assertEqual((29,),migrate(self.db,29))
        self.receive()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,28)
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual('ok',self.db.execute('PRAGMA integrity_check').fetchone()[0])

    def test_notifications_link_and_no_addresses(self):
        self.released()
        from services.typed_notifications import TypedNotificationService
        self.receive()
        payload=self.db.execute("SELECT payload_json FROM trade_events WHERE event_type='ReceiptComplete'").fetchone()[0]
        self.assertEqual({'revision_id','sender'},set(json.loads(payload)))
        self.assertNotIn('Fixture Road',str(self.rows('notifications')))
        service=TypedNotificationService(self.db)
        notification=service.from_row(self.db.execute("SELECT * FROM notifications WHERE notification_type='lifecycle_receipt_update'").fetchone())
        self.assertEqual(f'/tauschen/empfang/{self.t}',service.target_path_for(notification,1))
        self.assertIsNone(service.target_path_for(notification,2))

    def test_multiple_positions_second_credit_failure_rolls_back_all(self):
        from services.smartdeal_optimizer import SmartDealPiece as P
        self.t=self.service.create(1,3,(P('vfl','11'),P('vfl','12')),(P('vfl','16'),P('vfl','17')),'multi')
        self.rev=self.service._row(self.t)['revision_id'];self.acceptance.accept(self.t,3,self.rev,'accept-multi');self.released()
        before=self.snapshot();original=HistoricalInventoryWriteService.set_quantity;calls=[]
        def failure(obj,*args,**kwargs):
            calls.append(1)
            if len(calls)==2:raise ValueError('second receiver write')
            return original(obj,*args,**kwargs)
        with patch.object(HistoricalInventoryWriteService,'set_quantity',failure):
            with self.assertRaises(ValueError):self.receive(actor=3)
        self.assertEqual(before,self.snapshot());self.receive(actor=3)
        self.assertEqual((1,1),(self.qty(3,'11'),self.qty(3,'12')))

    def test_receipt_notification_failure_after_all_inventory_writes(self):
        self.released()
        from services.typed_notifications import TypedNotificationService
        original=TypedNotificationService.create;before=self.snapshot()
        def failure(obj,*args,**kwargs):
            if args[1]=='lifecycle_receipt_update':raise ValueError('receipt notification failed')
            return original(obj,*args,**kwargs)
        with patch.object(TypedNotificationService,'create',failure):
            with self.assertRaises(ValueError):self.receive()
        self.assertEqual(before,self.snapshot())

    def test_inventory_edit_serializes_with_receipt(self):
        self.released()
        from services.inventory_write import InventoryWriteService
        def edit(s):
            with s.store.transaction():InventoryWriteService(s.db).set_quantity(2,'vfl','1',2)
        self.race([lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'receipt'),edit])
        self.assertIn(self.qty(2,'1'),(2,3));self.assertEqual(1,self.count('lifecycle_receipts'))
        self.assertEqual(1,self.db.execute("SELECT SUM(quantity) FROM lifecycle_movements WHERE movement_kind='credit'").fetchone()[0])

    def test_missing_hold_action_against_systemic_receipt(self):
        self.released()
        from services.trade_lifecycle_preparation import LifecyclePreparation
        view=self.view();position=next(p['id'] for p in view['positions'] if p['from_user_id']==1)
        self.race([lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'receipt'),
            lambda s:LifecyclePreparation(s.db,lambda:self.now).command(self.t,1,self.rev,view['basis'],'missing-race','missing',{'position':position,'quantity':1})])
        if self.count('lifecycle_receipts'):
            self.assertEqual(1,self.qty(2,'1'));self.assertEqual(0,self.count('physical_missing_holds'))
        else:
            self.assertEqual(0,self.qty(2,'1'));self.assertEqual(0,self.count('lifecycle_shipping'));self.assertEqual(1,self.count('physical_missing_holds'))

    def test_conflicting_parallel_inspections_have_one_winner(self):
        self.released()
        full=None;missing=self.inspect(correct=0,missing=1)
        results=self.race([lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'full',full),
                           lambda s:LifecycleReceipts(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'missing',missing)])
        self.assertEqual(1,sum(r[0]=='ok' for r in results));self.assertEqual(1,self.count('lifecycle_receipts'))
        saved=self.r._receipt(self.t,1);self.assertEqual(0 if saved['has_problem'] else 1,self.qty(2,'1'))

    def test_sent_correctly_response_persists_without_closing(self):
        self.released()
        self.receive(self.inspect(correct=0,wrong=1));p=self.rows('lifecycle_delivery_problems')[0][0]
        self.r.respond(self.t,1,1,self.rev,p,'sent_correctly','response')
        self.assertEqual('sent_correctly',self.rows('lifecycle_delivery_responses')[0][2])
        self.assertEqual('received_with_problem',self.rows('lifecycle_directions')[0][-1])

    def test_control_photos_hidden_after_systemic_receipt(self):
        photo=self.db.execute('SELECT p.id FROM lifecycle_control_photos p JOIN lifecycle_preparation_cycles c ON c.id=p.cycle_id WHERE c.owner_id=1').fetchone()[0]
        self.s.photo(self.t,2,photo);self.released();self.receive()
        for actor in (1,2):
            with self.assertRaises(ValueError):self.s.photo(self.t,actor,photo)
        self.assertEqual([],next(c['photos'] for c in self.s.view(self.t,2)['cycles'] if c['owner_id']==1))

    def test_existing_receiver_stock_increases_by_accepted_delta_only(self):
        self.released()
        from services.inventory_write import InventoryWriteService
        InventoryWriteService(self.db).set_quantity(2,'vfl','1',4);self.db.commit()
        self.receive();self.assertEqual(5,self.qty(2,'1'))
        self.receive();self.assertEqual(5,self.qty(2,'1'))

    def finish_counter_direction(self, first_inspection=None):
        before = (self.qty(1, '11'), self.qty(3, '16'))
        opposite = dict(self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? AND from_user_id=3', (self.t,)).fetchone())
        self.assertIsNone(self.r._sent(self.t, 1))
        self.receive(first_inspection, actor=3, key='same-receipt')
        self.assertEqual(before[0]-3, self.qty(1, '11'))
        self.assertEqual(opposite, dict(self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? AND from_user_id=3', (self.t,)).fetchone()))
        self.assertEqual('RECEIPT_EVIDENCE', self.r._sent(self.t, 1)['source'])
        snapshot = self.snapshot()
        self.receive(first_inspection, actor=3, key='same-receipt')
        self.assertEqual(snapshot, self.snapshot())
        self.shipping(key='late-manual')
        self.assertEqual(before[0]-3, self.qty(1, '11'))
        self.assertEqual('ready_to_ship', next(d['state'] for d in self.ship.shipping_view(self.t, 3)['directions'] if d['sender']==3))
        self.shipping(actor=3, key='counter-shipping')
        self.assertEqual(before[1]-3, self.qty(3, '16'))
        self.receive(actor=1, sender=3, key='counter-receipt')
        self.assertEqual(3, self.qty(1, '16'))
        self.assertEqual('received_complete', self.db.execute('SELECT receipt_state FROM lifecycle_directions WHERE trade_id=? AND from_user_id=3', (self.t,)).fetchone()[0])
        self.assertEqual('accepted', self.db.execute('SELECT state FROM lifecycle_contracts WHERE trade_id=?', (self.t,)).fetchone()[0])
        with self.assertRaises(ValueError):
            self.call('correct', actor=3)

    def test_bilateral_release_systemic_receipt_then_regular_counter_direction(self):
        self.larger(3)
        self.released()
        self.finish_counter_direction()
        self.assertEqual(3, self.qty(3, '11'))
        self.assertEqual(['received_complete', 'received_complete'], [r[0] for r in self.db.execute('SELECT receipt_state FROM lifecycle_directions WHERE trade_id=?', (self.t,))])

    def early_receipt_then_continue(self, structured):
        self.larger(3)
        inspection = self.inspect(correct=2, missing=1) if structured else None
        def rejected():
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.receive(inspection, actor=3, key='same-receipt')
            with self.assertRaises(ValueError):
                self.r.review_receipt(self.t, 3, 1, self.rev, inspection)
            self.assertEqual(before, self.snapshot())
            self.assertFalse(self.r.receipt_view(self.t, 3)['receipt_enabled'])
        rejected()  # accepted, no preparation
        self.photo(1); self.call('complete', 1)
        rejected()  # only one package prepared
        self.photo(3); self.call('complete', 3)
        rejected()  # both prepared, no photo approval
        self.call('approve', 1)
        rejected()  # one photo approval
        self.call('approve', 3)
        rejected()  # both photos approved, no address release
        self.confirm(1)
        rejected()  # only one address confirmed
        self.confirm(3)
        self.assertTrue(self.r.receipt_view(self.t, 3)['receipt_enabled'])
        self.finish_counter_direction(inspection)
        self.assertEqual(2 if structured else 3, self.qty(3, '11'))
        availability = lifecycle_availability(self.db, 3, 'vfl', '11')
        self.assertEqual(1 if structured else 0, availability.committed)

    def test_early_complete_rejected_without_writes_then_both_directions_continue(self):
        self.early_receipt_then_continue(False)

    def test_early_partial_rejected_without_writes_then_both_directions_continue(self):
        self.early_receipt_then_continue(True)

    def test_early_damage_wrong_and_late_arrival_commands_cannot_bypass_entry(self):
        self.larger(3)
        for quantities in (dict(damaged_accepted=3), dict(damaged_rejected=3), dict(wrong=3)):
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.receive(self.inspect(correct=0, **quantities), actor=3)
            self.assertEqual(before, self.snapshot())
        with self.assertRaises(ValueError):
            self.r.report_non_arrival(self.t, 3, 1, self.rev, 'no-shipping')
        self.assertEqual(before, self.snapshot())
