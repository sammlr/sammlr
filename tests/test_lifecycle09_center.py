"""Synthetic center projections: authorization, clocks, lifecycle truth and bounded reads."""
import json
import unittest
from datetime import timedelta
from unittest.mock import patch
from tests import test_lifecycle04_preparation as fixtures
from services.lifecycle_center import LifecycleCenter, PAGE_SIZE
from services.trade_lifecycle_completion import LifecycleCompletion
from services.trade_lifecycle_addresses import LifecycleAddresses
from services.trade_lifecycle_shipping import LifecycleShipping
from tests import test_lifecycle07_receipts as receipt_fixtures
from tests import test_lifecycle05_addresses as address_fixtures
from App.Database.migration_runner import migrate,rollback


class CenterTests(unittest.TestCase):
    for name in ('connect','send','stock','target','race','view','call','photo','both','ready','larger','reduction'):
        locals()[name]=getattr(fixtures.PreparationTests,name)
    book=address_fixtures.AddressTests.book
    confirm=address_fixtures.AddressTests.confirm
    released=receipt_fixtures.ReceiptTests.released
    inspect=receipt_fixtures.ReceiptTests.inspect
    receive=receipt_fixtures.ReceiptTests.receive

    def setUp(self):
        fixtures.PreparationTests.setUp(self);migrate(self.db,30)
        self.r=LifecycleCompletion(self.db,lambda:self.now)
        self.a=LifecycleAddresses(self.db,lambda:self.now)
        self.center=LifecycleCenter(self.db,lambda:self.now);self.counter=0

    def model(self,actor=1,section=None,page=1):return self.center.view(actor,section,page)
    def cards(self,actor=1,section='todos'):return self.model(actor,section)['items']
    def codes(self,actor=1):return {a['code'] for c in self.cards(actor) for a in c['actions']}
    def snapshot(self):
        return {t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in ('stickers','trade_reservations','lifecycle_need_claims','lifecycle_movements','lifecycle_shipping','lifecycle_receipts')}
    def finish(self):
        self.released();self.receive();self.receive(actor=1,sender=2)

    def test_initial_own_preparation_and_independent_directions(self):
        self.assertEqual({'prepare'},self.codes())
        self.assertEqual(self.t,self.cards(section='sendungen')[0]['trade'])
        self.assertEqual(1,self.cards(section='sendungen')[0]['give'])
        self.assertEqual(1,self.cards(section='eingaenge')[0]['receive'])
        self.assertEqual([],self.cards(3))
        self.assertEqual(3,len(self.model()['sections']))

    def test_preparation_deadline_exact_and_no_false_partner_task(self):
        due=self.now+timedelta(hours=72)
        self.now=due-timedelta(microseconds=1)
        a=self.cards()[0]['actions'][0];self.assertEqual(0,a['priority']);self.assertFalse(a['overdue'])
        self.now=due;self.assertTrue(self.cards()[0]['actions'][0]['overdue'])
        self.photo();self.call('complete')
        self.assertEqual(set(),self.codes());self.assertEqual({'prepare'},self.codes(2))
        self.assertIsNotNone(self.cards(section='sendungen')[0]['waiting'])

    def test_mutual_photos_review_and_correction(self):
        self.both();self.assertEqual({'review'},self.codes())
        self.call('problem',2,{'reason':'NOT_RECOGNIZABLE'})
        self.assertIn('correct',self.codes());self.assertNotIn('correct',self.codes(2))
        self.call('correct');self.assertEqual({'prepare'},self.codes())
        self.assertNotIn('review',self.codes(2))

    def test_address_choices_and_ship_deadline(self):
        self.ready();self.assertEqual({'address'},self.codes())
        self.confirm(1);self.assertEqual(set(),self.codes());self.assertEqual({'address'},self.codes(2))
        self.confirm(2);self.assertEqual({'ship','receive'},self.codes())
        self.now+=timedelta(hours=72)
        self.assertEqual('Versand überfällig',self.cards(section='sendungen')[0]['outgoing_status'])
        self.assertTrue(next(a for a in self.cards()[0]['actions'] if a['code']=='ship')['overdue'])
        LifecycleShipping(self.db,lambda:self.now).send_direction(self.t,1,self.rev,'sent')
        self.assertNotIn('ship',self.codes());self.assertIn('ship',self.codes(2))

    def test_nonarrival_seven_day_boundary_and_late_arrival(self):
        self.released();LifecycleShipping(self.db,lambda:self.now).send_direction(self.t,1,self.rev,'sent')
        self.now+=timedelta(days=7)-timedelta(microseconds=1);self.assertNotIn('nonarrival',self.codes(2))
        self.now+=timedelta(microseconds=1);self.assertIn('nonarrival',self.codes(2))
        self.r.report_non_arrival(self.t,2,1,self.rev,'nonarrival')
        self.assertNotIn('nonarrival',self.codes(2));self.assertIn('respond',self.codes())
        self.assertNotIn('close_problem',self.codes(2));self.assertNotIn('rate',self.codes(2))
        self.receive();self.assertNotIn('respond',self.codes());self.assertIn('rate',self.codes(2))
        self.assertEqual('Empfang bestätigt',self.cards(2,'eingaenge')[0]['incoming_status'])

    def test_problem_resolution_fourteen_day_boundary(self):
        self.released();self.receive(self.inspect(correct=0,missing=1));reported=self.now
        p=self.db.execute('SELECT id FROM lifecycle_delivery_problems').fetchone()[0]
        self.assertIn('accept_problem',self.codes(2));self.assertIn('rate',self.codes(2))
        self.now=reported+timedelta(days=14)-timedelta(microseconds=1);self.assertNotIn('close_problem',self.codes(2))
        self.now+=timedelta(microseconds=1);self.assertIn('close_problem',self.codes(2));self.assertNotIn('rate',self.codes(2))
        self.r.resolve_problem(self.t,2,1,self.rev,p,'after_wait','close')
        self.assertNotIn('accept_problem',self.codes(2));self.assertNotIn('respond',self.codes())
        self.assertEqual('Problem abgeschlossen',self.cards(2,'eingaenge')[0]['incoming_status'])

    def test_archive_removes_both_active_cards_but_preserves_rating(self):
        self.finish()
        self.assertEqual([],self.cards(section='sendungen'));self.assertEqual([],self.cards(section='eingaenge'))
        self.assertEqual({'rate'},self.codes());self.assertTrue(self.cards()[0]['archived'])
        archive=self.cards(section='archiv');self.assertEqual(1,len(archive));self.assertEqual('Erfolgreich abgeschlossen',archive[0]['status'])
        self.assertEqual((1,1,0),(archive[0]['received'],archive[0]['partner_received'],archive[0]['problem_count']))
        self.now+=timedelta(days=14);self.assertEqual([],self.cards());self.assertEqual(1,len(self.cards(section='archiv')))

    def test_problem_completion_archive_and_blind_projection(self):
        self.released();self.receive(actor=1,sender=2);self.receive(self.inspect(correct=0,missing=1))
        p=self.db.execute('SELECT id FROM lifecycle_delivery_problems').fetchone()[0]
        self.r.resolve_problem(self.t,2,1,self.rev,p,'problem_accepted','close')
        self.r.submit_rating(self.t,2,self.rev,4,['well_packed'],'rate')
        self.assertEqual('Mit Lieferproblem abgeschlossen',self.cards(section='archiv')[0]['status'])
        self.assertEqual((1,0,1),tuple(self.cards(section='archiv')[0][k] for k in ('received','partner_received','problem_count')))
        for section in (None,'todos','sendungen','eingaenge','archiv'):
            encoded=json.dumps(self.model(section=section));self.assertNotIn('stars',encoded);self.assertNotIn('well_packed',encoded)
        self.assertEqual([],self.r.completion_view(self.t,1)['ratings']['visible'])

    def test_read_materializes_due_reveal_once_without_inventory(self):
        self.finish();self.r.submit_rating(self.t,2,self.rev,4,[],'rate');before=self.snapshot()
        self.now+=timedelta(days=14);self.model();self.model()
        self.assertEqual(before,self.snapshot());self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_events WHERE event_type='RatingRevealed'").fetchone()[0])
        self.assertEqual(1,len(self.r.completion_view(self.t,1)['ratings']['visible']))

    def test_read_catches_up_old_l07_receipts_without_booking(self):
        rollback(self.db,29);self.finish();migrate(self.db,30);before=self.snapshot()
        self.model();self.assertEqual([],self.cards(section='sendungen'));self.assertEqual(1,len(self.cards(section='archiv')))
        self.assertEqual(before,self.snapshot())

    def test_revision_reduction_uses_binding_quantities_and_pending_owner(self):
        self.larger(3);self.reduction(2)
        self.assertIn('reduction',self.codes(3));self.assertFalse(next(c for c in self.cards(section='sendungen') if c['trade']==self.t)['actions'])
        self.assertNotIn('reduction',self.codes())
        self.call('reduction_approve',3,{'proposal':self.s._pending(self.t)['revision_id']})
        card=next(c for c in self.cards(section='sendungen') if c['trade']==self.t)
        self.assertEqual((2,2),(card['give'],card['receive']))

    def many(self,n=30):
        self.stock(1,'1',n+5);self.stock(2,'6',n+5);self.target(1,'6',n+5);self.target(2,'1',n+5)
        for i in range(n-1):
            t=self.send('many-'+str(i));rev=self.service._row(t)['revision_id'];self.acceptance.accept(t,2,rev,'accept-many')

    def test_many_active_trades_fixed_query_count_pagination_and_stable_sort(self):
        self.many();queries=[];self.db.set_trace_callback(queries.append)
        first=self.model(section='todos');self.db.set_trace_callback(None)
        self.assertEqual(30,first['total']);self.assertEqual(PAGE_SIZE,len(first['items']))
        self.assertLess(len([s for s in queries if s.lstrip().upper().startswith('SELECT')]),25)
        second=self.model(section='todos',page=2)
        self.assertFalse({c['trade'] for c in first['items']} & {c['trade'] for c in second['items']})
        self.assertEqual(first,self.model(section='todos'))
        self.assertTrue(all(len(s['items'])<=3 for s in self.model()['sections']))
        self.assertEqual(sorted(c['trade'] for c in first['items']),[c['trade'] for c in first['items']])

    def test_no_payload_reads_or_stock_mutation_on_regular_read(self):
        self.released();before=self.snapshot();queries=[];self.db.set_trace_callback(queries.append)
        self.model();self.db.set_trace_callback(None)
        self.assertEqual(before,self.snapshot())
        for forbidden in ('storage_name','inspection_json','first_name','street','stars','tags_json'):
            self.assertNotIn(forbidden,'\n'.join(queries))

    def test_invalid_actor_page_and_section(self):
        for actor in (0,999):
            with self.assertRaises(ValueError):self.model(actor)
        for page in (0,-1,100001):
            with self.assertRaises(ValueError):self.model(page=page)
        with self.assertRaises(ValueError):self.model(section='other')

    def test_many_archived_trades_paginate_and_expired_ratings_disappear(self):
        self.many(26)
        trades=[tuple(r) for r in self.db.execute('SELECT trade_id,accepted_revision_id FROM lifecycle_contracts')]
        for self.t,self.rev in trades:self.finish()
        self.now+=timedelta(days=14)
        self.assertEqual([],self.cards());self.assertEqual([],self.cards(section='sendungen'))
        pages=[self.model(section='archiv',page=p) for p in (1,2,3)]
        self.assertEqual([12,12,2],[len(p['items']) for p in pages])
        self.assertEqual(26,len({c['trade'] for p in pages for c in p['items']}))

    def test_priority_deadline_then_stable_acceptance_and_trade_id(self):
        self.many(3)
        rows=[tuple(r) for r in self.db.execute('SELECT trade_id,accepted_revision_id FROM lifecycle_contracts ORDER BY trade_id')]
        self.t,self.rev=rows[-1];self.released()
        self.now+=timedelta(hours=73)
        cards=self.cards();self.assertEqual([r[0] for r in rows],[c['trade'] for c in cards])
        self.assertTrue(all(c['actions'][0]['priority']==0 for c in cards))
