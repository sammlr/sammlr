"""Synthetic L08 integration, boundaries, privacy, concurrency and atomic rollback."""
import json
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from tests import test_lifecycle07_receipts as fixtures
from services.trade_lifecycle_completion import LifecycleCompletion
from services.trade_ratings import TradeRatingService
from services.trade_lifecycle_foundation import lifecycle_availability
from App.Database.migration_runner import migrate, rollback


class CompletionTests(unittest.TestCase):
    for _name, _method in vars(fixtures.ReceiptTests).items():
        if callable(_method) and not _name.startswith('_') and not _name.startswith('test_') and _name != 'setUp':
            locals()[_name] = _method

    def setUp(self):
        fixtures.ReceiptTests.setUp(self)
        migrate(self.db,30)
        self.now = datetime.now(timezone.utc)
        self.c = self.r = LifecycleCompletion(self.db, lambda:self.now)
        self.released()

    def state(self):
        return self.db.execute('SELECT state FROM lifecycle_contracts WHERE trade_id=?',(self.t,)).fetchone()[0]

    def problem(self, actor=2, sender=1, nonarrival=False):
        if nonarrival:
            self.shipping(actor=sender,key='ship-'+str(sender));self.now+=timedelta(days=7)
            return self.c.report_non_arrival(self.t,actor,sender,self.rev,'non-'+str(sender))['problem']
        self.receive(self.inspect(correct=0,missing=1),actor=actor,sender=sender)
        return self.db.execute("SELECT id FROM lifecycle_delivery_problems WHERE trade_id=? AND from_user_id=? AND kind='inspection'",(self.t,sender)).fetchone()[0]

    def close(self, problem, mode='problem_accepted', actor=2, sender=1, key='close'):
        return self.c.resolve_problem(self.t,actor,sender,self.rev,problem,mode,key)

    def rate(self, actor=2, stars=4, tags=None, key='rate'):
        return self.c.submit_rating(self.t,actor,self.rev,stars,tags or [],key)

    def full_snapshot(self):
        return list(self.db.iterdump())

    def test_last_receipt_completes_atomically_and_no_second_events(self):
        self.receive();self.assertEqual('accepted',self.state())
        self.receive(actor=1,sender=2)
        self.assertEqual('ended',self.state())
        self.assertEqual('completed',self.rows('lifecycle_completions')[0][2])
        self.assertEqual(2,self.event('DirectionResolvedComplete'));self.assertEqual(1,self.event('TradeCompletedSuccessfully'))
        before=self.full_snapshot();self.receive(actor=1,sender=2)
        self.assertEqual(before,self.full_snapshot())
        self.c.completion_view(self.t,1);self.assertEqual(1,self.event('TradeCompletedSuccessfully'))
        with self.assertRaises(ValueError):self.shipping(actor=2,key='after-completion')

    def test_problem_accept_releases_only_unfulfilled_claim_and_preserves_inventory(self):
        self.larger(3);self.released()
        self.receive(self.inspect(correct=2,missing=1),actor=3)
        problem=self.db.execute('SELECT id FROM lifecycle_delivery_problems WHERE trade_id=?',(self.t,)).fetchone()[0]
        a=lifecycle_availability(self.db,3,'vfl','11');self.assertEqual((2,1,0),(a.physical,a.committed,a.free_need))
        other=[tuple(r) for r in self.db.execute('SELECT c.* FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id WHERE p.revision_id<>?',(self.rev,))]
        before=self.inventory()['stickers'];self.close(problem,actor=3)
        self.assertEqual(before,self.inventory()['stickers'])
        a=lifecycle_availability(self.db,3,'vfl','11');self.assertEqual((2,0,1),(a.physical,a.committed,a.free_need))
        self.assertEqual(other,[tuple(r) for r in self.db.execute('SELECT c.* FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id WHERE p.revision_id<>?',(self.rev,))])
        self.assertEqual((3,2,'released'),tuple(self.db.execute('SELECT c.quantity,c.received_quantity,c.state FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id WHERE p.revision_id=? AND p.from_user_id=1',(self.rev,)).fetchone()))
        self.assertEqual('accepted',self.state());self.shipping(actor=3);self.receive(actor=1,sender=3)
        self.assertEqual('closed_with_problem',self.rows('lifecycle_completions')[0][2])

    def test_complete_then_problem_accept_completes_with_problem(self):
        self.receive(actor=1,sender=2);p=self.problem();self.assertEqual('accepted',self.state())
        self.close(p);self.assertEqual('ended',self.state());self.assertEqual(1,self.event('TradeCompletedWithProblem'))
        self.assertEqual(0,self.count('trade_ratings'))

    def test_both_problems_need_both_resolutions(self):
        p=self.problem()
        position=next(p for p in self.r._positions(self.rev) if p['from_user_id']==2)
        inspection=[dict(position=position['id'],correct=0,missing=1,wrong=0,damaged_accepted=0,damaged_rejected=0,wrong_code='')]
        self.receive(inspection,actor=1,sender=2)
        q=self.db.execute('SELECT id FROM lifecycle_delivery_problems WHERE from_user_id=2').fetchone()[0]
        self.close(p);self.assertEqual('accepted',self.state())
        self.close(q,actor=1,sender=2);self.assertEqual('ended',self.state())
        self.assertEqual(1,self.event('TradeCompletedWithProblem'))

    def test_problem_boundary_before_exact_and_after_fourteen_days(self):
        p=self.problem();start=self.now
        self.now=start+timedelta(days=14)-timedelta(microseconds=1)
        before=self.full_snapshot()
        with self.assertRaises(ValueError):self.close(p,mode='after_wait')
        self.assertEqual(before,self.full_snapshot())
        self.now+=timedelta(microseconds=1);self.close(p,mode='after_wait')
        self.now+=timedelta(days=1);self.close(p,mode='after_wait',key='retry')
        self.assertEqual(1,self.event('DirectionResolvedAfterWait'))

    def test_nonarrival_cannot_accept_early_or_rate_until_final_close(self):
        p=self.problem(nonarrival=True);before=self.inventory()
        with self.assertRaises(ValueError):self.close(p)
        with self.assertRaises(ValueError):self.close(p,mode='after_wait')
        with self.assertRaises(ValueError):self.rate()
        self.now+=timedelta(days=14);self.close(p,mode='after_wait')
        self.assertEqual(before['stickers'],self.inventory()['stickers']);self.assertEqual(0,self.count('lifecycle_receipts'))
        self.rate();self.assertEqual(1,self.count('trade_ratings'))
        snapshot=self.full_snapshot()
        with self.assertRaises(ValueError):self.receive()
        self.assertEqual(snapshot,self.full_snapshot())

    def test_late_arrival_supersedes_old_nonarrival_problem(self):
        p=self.problem(nonarrival=True);self.receive();self.now+=timedelta(days=14)
        with self.assertRaises(ValueError):self.close(p,mode='after_wait')
        self.assertEqual('accepted',self.state());self.assertEqual(1,self.qty(2,'1'))

    def test_resolution_retry_conflict_and_ownership(self):
        p=self.problem();first=self.close(p);snapshot=self.full_snapshot()
        self.assertEqual(first,self.close(p));self.assertEqual(snapshot,self.full_snapshot())
        self.assertEqual(first,self.close(p,key='new'))
        for kwargs in [dict(actor=1),dict(actor=3),dict(mode='after_wait'),dict(sender=999)]:
            with self.assertRaises(ValueError):self.close(p,key='bad',**kwargs)
        self.assertEqual(1,self.event('DirectionResolvedProblemAccepted'))

    def test_rating_independent_eligibility_and_blind_until_both(self):
        with self.assertRaises(ValueError):self.rate()
        self.receive();self.rate(tags=['well_packed','as_described'])
        self.assertEqual('accepted',self.state())
        self.assertEqual([],self.c.completion_view(self.t,1)['ratings']['visible'])
        self.assertEqual(0,TradeRatingService(self.db).summary_for_user(1,self.now).rating_count)
        self.receive(actor=1,sender=2);self.rate(actor=1,stars=5)
        self.assertEqual(2,len(self.c.completion_view(self.t,1)['ratings']['visible']))
        self.assertEqual(1,TradeRatingService(self.db).summary_for_user(1,self.now).rating_count)
        self.assertEqual(2,self.event('RatingSubmitted'));self.assertEqual(2,self.event('RatingRevealed'))
        payloads=[json.loads(r[0]) for r in self.db.execute("SELECT payload_json FROM trade_events WHERE event_type LIKE 'Rating%'")]
        self.assertTrue(all('stars' not in p and 'tags' not in p for p in payloads))

    def test_reveal_waits_for_other_eligibility_deadline_not_own(self):
        self.receive();self.rate();self.now+=timedelta(days=20)
        self.assertEqual([],self.c.completion_view(self.t,1)['ratings']['visible'])
        self.receive(actor=1,sender=2);start=self.now
        self.now=start+timedelta(days=14)-timedelta(microseconds=1)
        self.assertEqual([],self.c.completion_view(self.t,1)['ratings']['visible'])
        self.now+=timedelta(microseconds=1)
        self.assertEqual(1,len(self.c.completion_view(self.t,1)['ratings']['visible']))
        with self.assertRaises(ValueError):self.rate(actor=1)
        self.assertEqual(1,self.event('RatingRevealed'))

    def test_rating_exact_deadline_and_retry_after_expiry(self):
        self.receive();start=self.now
        self.now=start+timedelta(days=14)-timedelta(microseconds=1);first=self.rate()
        self.now+=timedelta(microseconds=1)
        self.assertEqual(first,self.rate());self.assertEqual(first,self.rate(key='other'))
        with self.assertRaises(ValueError):self.rate(stars=1,key='conflict')

    def test_new_rating_at_deadline_rejected(self):
        self.receive();self.now+=timedelta(days=14)
        with self.assertRaises(ValueError):self.rate()
        self.now+=timedelta(days=1)
        with self.assertRaises(ValueError):self.rate()
        self.assertEqual(0,self.count('trade_ratings'))

    def test_rating_validation_tags_stars_owner_revision(self):
        self.receive()
        for stars in (0,6,True,1.5,'5'):
            with self.assertRaises(ValueError):self.rate(stars=stars)
        for tags in (['negative'],['well_packed','well_packed'],[1],{'well_packed':1}):
            with self.assertRaises(ValueError):self.c.submit_rating(self.t,2,self.rev,5,tags,'bad')
        for actor in (1,3):
            with self.assertRaises(ValueError):self.rate(actor=actor)
        with self.assertRaises(ValueError):self.c.submit_rating(self.t,2,999,5,[],'bad')
        self.assertEqual(0,self.count('trade_ratings'))

    def test_rollbacks_claim_completion_event_notification_command(self):
        self.receive(actor=1,sender=2);p=self.problem()
        for table,action in [('lifecycle_need_claims','UPDATE'),('lifecycle_completions','INSERT'),('trade_events','INSERT'),('notifications','INSERT'),('lifecycle_commands','INSERT')]:
            before=self.full_snapshot()
            self.db.execute(f"CREATE TEMP TRIGGER fail_l08 BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'synthetic'); END")
            try:
                with self.assertRaises(sqlite3.IntegrityError):self.close(p)
            finally:self.db.execute('DROP TRIGGER fail_l08')
            self.assertEqual(before,self.full_snapshot())

    def test_last_receipt_completion_failure_rolls_back_inventory(self):
        self.receive();before=self.full_snapshot()
        self.db.execute("CREATE TEMP TRIGGER fail_l08 BEFORE INSERT ON lifecycle_completions BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        try:
            with self.assertRaises(sqlite3.IntegrityError):self.receive(actor=1,sender=2)
        finally:self.db.execute('DROP TRIGGER fail_l08')
        self.assertEqual(before,self.full_snapshot())

    def test_rating_and_reveal_rollback(self):
        self.receive();self.receive(actor=1,sender=2);self.rate()
        for table in ('lifecycle_rating_details','lifecycle_rating_publications','trade_events','notifications','lifecycle_commands'):
            before=self.full_snapshot();self.db.execute(f"CREATE TEMP TRIGGER fail_l08 BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'synthetic'); END")
            try:
                with self.assertRaises(sqlite3.IntegrityError):self.rate(actor=1)
            finally:self.db.execute('DROP TRIGGER fail_l08')
            self.assertEqual(before,self.full_snapshot())

    def test_parallel_resolution_and_last_receipt(self):
        p=self.problem()
        results=self.race([lambda s:LifecycleCompletion(s.db,lambda:self.now).resolve_problem(self.t,2,1,self.rev,p,'problem_accepted','a'),
            lambda s:LifecycleCompletion(s.db,lambda:self.now).resolve_problem(self.t,2,1,self.rev,p,'problem_accepted','b'),
            lambda s:LifecycleCompletion(s.db,lambda:self.now).confirm_receipt(self.t,1,2,self.rev,'last')])
        self.assertTrue(all(r[0]=='ok' for r in results));self.assertEqual(1,self.event('TradeCompletedWithProblem'))
        self.assertEqual(1,self.event('DirectionResolvedProblemAccepted'))

    def test_parallel_ratings_reveal_once(self):
        self.receive();self.receive(actor=1,sender=2)
        results=self.race([lambda s:LifecycleCompletion(s.db,lambda:self.now).submit_rating(self.t,2,self.rev,4,[],'a'),
            lambda s:LifecycleCompletion(s.db,lambda:self.now).submit_rating(self.t,1,self.rev,5,[],'b'),
            lambda s:LifecycleCompletion(s.db,lambda:self.now).submit_rating(self.t,2,self.rev,4,[],'c')])
        self.assertTrue(all(r[0]=='ok' for r in results));self.assertEqual(2,self.count('trade_ratings'));self.assertEqual(2,self.event('RatingRevealed'))

    def test_nonarrival_close_races_late_receipt(self):
        p=self.problem(nonarrival=True);self.now+=timedelta(days=14)
        result=self.race([lambda s:LifecycleCompletion(s.db,lambda:self.now).resolve_problem(self.t,2,1,self.rev,p,'after_wait','close'),
            lambda s:LifecycleCompletion(s.db,lambda:self.now).confirm_receipt(self.t,2,1,self.rev,'late')])
        self.assertEqual(1,sum(r[0]=='ok' for r in result));self.assertIn(self.qty(2,'1'),(0,1))
        self.assertEqual(1,self.count('lifecycle_direction_resolutions'))

    def test_migration_reverse_guard_and_immutable_evidence(self):
        self.assertEqual((30,),rollback(self.db,29));self.assertEqual((30,),migrate(self.db,30))
        self.receive();self.rate()
        for sql in ('DELETE FROM lifecycle_rating_eligibility','UPDATE lifecycle_direction_resolutions SET kind=kind','DELETE FROM trade_ratings'):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,29)
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual('ok',self.db.execute('PRAGMA integrity_check').fetchone()[0])

    def test_existing_l07_receipts_catch_up_without_inventory_changes(self):
        rollback(self.db,29);self.receive();self.receive(actor=1,sender=2)
        self.assertEqual('accepted',self.state());before=self.inventory();migrate(self.db,30)
        self.c.completion_view(self.t,1)
        self.assertEqual('ended',self.state());self.assertEqual(before,self.inventory());self.assertEqual(1,self.event('TradeCompletedSuccessfully'))

    def test_resolved_nonarrival_history_is_not_labelled_problem_free(self):
        self.problem(nonarrival=True);self.receive();self.receive(actor=1,sender=2)
        self.assertEqual('closed_with_problem',self.rows('lifecycle_completions')[0][2])

    def test_data_export_and_profile_do_not_leak_hidden_received_rating(self):
        from services.user_data_export import UserDataExportService
        self.receive();self.rate(tags=['well_packed'])
        export=UserDataExportService(self.db).export_for_user(1)
        self.assertIsNotNone(export)
        self.assertEqual(0,TradeRatingService(self.db).summary_for_user(1).rating_count)
        encoded=json.dumps(export.ratings,default=str)
        self.assertNotIn('"stars": 4',encoded)
        self.receive(actor=1,sender=2);self.rate(actor=1,stars=5)
        self.assertEqual(1,TradeRatingService(self.db).summary_for_user(1).rating_count)

    def test_problem_claim_release_reappears_in_matching_projection(self):
        from services.trade_v2_domain import TradeV2Domain
        self.larger(3);self.released();self.receive(self.inspect(correct=2,missing=1),actor=3)
        p=self.db.execute('SELECT id FROM lifecycle_delivery_problems WHERE trade_id=?',(self.t,)).fetchone()[0]
        self.close(p,actor=3)
        inputs=TradeV2Domain(self.db).market(3)
        self.assertTrue(any(p.album_id=='vfl' and p.sticker_code=='11' and p.quantity==1 for p in inputs.inputs.subject.needs))

    def test_sender_response_races_final_resolution(self):
        p=self.problem()
        self.race([lambda s:LifecycleCompletion(s.db,lambda:self.now).resolve_problem(self.t,2,1,self.rev,p,'problem_accepted','c'),
                   lambda s:LifecycleCompletion(s.db,lambda:self.now).respond(self.t,1,1,self.rev,p,'acknowledge','s')])
        self.assertEqual(1,self.event('DirectionResolvedProblemAccepted'));self.assertIn(self.count('lifecycle_delivery_responses'),(0,1))

    def test_simultaneous_resolution_of_both_problem_directions(self):
        p=self.problem()
        position=next(p for p in self.r._positions(self.rev) if p['from_user_id']==2)
        self.receive([dict(position=position['id'],correct=0,missing=1,wrong=0,damaged_accepted=0,damaged_rejected=0,wrong_code='')],actor=1,sender=2)
        q=self.db.execute('SELECT id FROM lifecycle_delivery_problems WHERE from_user_id=2').fetchone()[0]
        self.race([lambda s:LifecycleCompletion(s.db,lambda:self.now).resolve_problem(self.t,2,1,self.rev,p,'problem_accepted','a'),
                   lambda s:LifecycleCompletion(s.db,lambda:self.now).resolve_problem(self.t,1,2,self.rev,q,'problem_accepted','b')])
        self.assertEqual(1,self.event('TradeCompletedWithProblem'));self.assertEqual(2,self.event('DirectionResolvedProblemAccepted'))

    def test_rating_race_at_deadline_has_no_late_insert(self):
        self.receive();self.now+=timedelta(days=14)
        result=self.race([lambda s:LifecycleCompletion(s.db,lambda:self.now).submit_rating(self.t,2,self.rev,3,[],'a'),
                          lambda s:LifecycleCompletion(s.db,lambda:self.now).submit_rating(self.t,2,self.rev,3,[],'b')])
        self.assertEqual(0,sum(r[0]=='ok' for r in result));self.assertEqual(0,self.count('trade_ratings'))

    def test_shipping_guard_still_forbids_cancellation_and_revision_changes(self):
        self.receive()
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE lifecycle_contracts SET state='ended' WHERE trade_id=?",(self.t,))
        self.db.rollback()
        self.receive(actor=1,sender=2)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE lifecycle_contracts SET state='accepted' WHERE trade_id=?",(self.t,))

    def test_new_disputed_resolution_after_fourteen_days(self):
        problem=self.problem();self.now+=timedelta(days=15)
        self.close(problem,mode='after_wait')
        self.assertEqual(1,self.event('DirectionResolvedAfterWait'))

    def test_problem_inspection_qualifies_before_resolution_and_not_before_timestamp(self):
        problem=self.problem();stamp=self.now;self.now-=timedelta(microseconds=1)
        with self.assertRaises(ValueError):self.rate()
        self.now=stamp;self.rate()
        self.assertEqual(1,self.count('trade_ratings'))
        self.assertEqual(0,self.count('lifecycle_direction_resolutions'))
        self.close(problem)
        self.assertEqual(stamp.isoformat(),self.db.execute('SELECT eligible_at FROM lifecycle_rating_eligibility').fetchone()[0])

    def test_accepted_damage_releases_no_fulfilled_claim_and_adds_no_stock(self):
        self.receive(self.inspect(correct=0,damaged_accepted=1))
        problem=self.db.execute('SELECT id FROM lifecycle_delivery_problems').fetchone()[0]
        before=self.rows('lifecycle_need_claims');stock=self.inventory()['stickers']
        self.close(problem)
        self.assertEqual(before,self.rows('lifecycle_need_claims'))
        self.assertEqual(stock,self.inventory()['stickers'])
