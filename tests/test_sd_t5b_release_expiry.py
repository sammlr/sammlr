"""Real V21 pending releases, absolute deadlines and synchronized writers."""
from datetime import datetime, timedelta, timezone
import sqlite3
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from tests import test_sd_t5a_atomic_binding as foundation
from services.smartdeal_expiry import expires_at, utc_instant
from services.smartdeal_release import SmartDealReleaseService, ReleaseCode
from services.smartdeal_requests import SmartDealRequestCode
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_optimizer import SmartDealOptimizer
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.community import CommunityService
from services.typed_notifications import TypedNotificationService

NOW = foundation.planning_fixtures.NOW


class DeadlineTests(unittest.TestCase):
    def test_absolute_24_hours(self):
        self.assertEqual(86400, (expires_at(NOW) - NOW).total_seconds())

    def test_different_start_hours(self):
        for h, m in ((0,0),(10,17),(12,0),(23,55),(23,59)):
            start = datetime(2026,9,14,h,m,tzinfo=timezone.utc)
            self.assertEqual(datetime(2026,9,15,h,m,tzinfo=timezone.utc), expires_at(start))

    def test_persisted_formats(self):
        for stamp in ('2026-09-10 12:00:00', '2026-09-10T12:00:00Z', '2026-09-10T14:00:00+02:00'):
            self.assertEqual(NOW+timedelta(hours=24), expires_at(stamp))

    def test_microseconds_preserved(self):
        start = NOW.replace(microsecond=123456)
        self.assertEqual(start+timedelta(hours=24), expires_at(start.isoformat()))

    def test_offset_and_dst_do_not_change_duration(self):
        for start in (datetime(2026,3,28,12,tzinfo=ZoneInfo('Europe/Berlin')),
                      datetime(2026,10,24,12,tzinfo=ZoneInfo('Europe/Berlin'))):
            self.assertEqual(86400, expires_at(start).timestamp()-start.timestamp())
            self.assertEqual(timezone.utc, expires_at(start).tzinfo)

    def test_month_and_year_are_elapsed_time_only(self):
        for start in (datetime(2026,1,31,23,55,tzinfo=timezone.utc), datetime(2026,12,31,10,17,tzinfo=timezone.utc)):
            self.assertEqual(start+timedelta(seconds=86400), expires_at(start))

    def test_invalid_timestamp_fails_closed(self):
        for value in (None, '', 'nonsense'):
            with self.assertRaises((ValueError,TypeError)): expires_at(value)


class ReleaseTests(unittest.TestCase):
    setUp = foundation.AtomicBindingTests.setUp
    configure = foundation.AtomicBindingTests.configure
    quantity = foundation.AtomicBindingTests.quantity
    plan = foundation.AtomicBindingTests.plan
    extra_partner = foundation.AtomicBindingTests.extra_partner
    binding = foundation.AtomicBindingTests.binding
    service = foundation.AtomicBindingTests.service
    create = foundation.AtomicBindingTests.create
    state = foundation.AtomicBindingTests.state
    all_rows = foundation.AtomicBindingTests.all_rows
    assert_reopened = foundation.AtomicBindingTests.assert_reopened
    package = foundation.AtomicBindingTests.package
    race = foundation.AtomicBindingTests.race

    def release(self, db=None, now=NOW):
        return SmartDealReleaseService(self.db if db is None else db, lambda:now)

    def bound(self):
        result = self.create()
        self.assertEqual(SmartDealRequestCode.CREATED,result.code)
        return result

    def assert_terminal(self, result, status):
        other=sqlite3.connect(self.path);other.row_factory=sqlite3.Row
        try:
            q=other.execute('SELECT * FROM trade_requests WHERE id=?',(result.request_id,)).fetchone()
            self.assertEqual(status,q['status']);self.assertIsNone(q['accepted_at'])
            self.assertEqual(NOW,utc_instant(q['binding_created_at']))
            self.assertEqual(self.suggestion.opportunity_identity,self.service(other).identity_for_request(result.request_id))
            rows=other.execute('SELECT * FROM trade_reservations WHERE trade_id=?',(result.trade_id,)).fetchall()
            self.assertTrue(rows);self.assertTrue(all(r['state']=='released' and r['released_at'] and r['release_reason'] for r in rows))
            self.assertEqual(status,other.execute('SELECT lifecycle_state FROM trades WHERE id=?',(result.trade_id,)).fetchone()[0])
            self.assertEqual('ok',other.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertEqual([],other.execute('PRAGMA foreign_key_check').fetchall())
        finally:other.close()

    def cycle(self, cause, now=NOW):
        before=self.all_rows(); initial={u:self.state(u) for u in (1,2)}
        deal=self.bound()
        for u in (1,2):
            self.assertEqual((),self.plan(u).deals)
            self.assertEqual((),self.state(u).outgoing_supply)
        action=getattr(self.release(now=now),cause)
        result=action(deal.request_id) if cause=='expire' else action(deal.request_id,2 if cause=='decline' else 1)
        self.assertEqual(ReleaseCode.RELEASED,result.code)
        status={'decline':'declined','withdraw':'cancelled','expire':'expired'}[cause]
        self.assert_terminal(deal,status)
        after=self.all_rows()
        allowed={'trade_requests','trades','trade_positions','trade_reservations','sqlite_sequence'}
        if cause=='decline':allowed.add('notifications')
        self.assertTrue({t for t in before if before[t]!=after[t]}<=allowed)
        self.assertEqual(before['stickers'],after['stickers'])
        for u in (1,2):
            fresh=self.state(u)
            self.assertEqual(initial[u].needs,fresh.needs)
            self.assertEqual(initial[u].outgoing_supply,fresh.outgoing_supply)
            self.assertEqual((),fresh.incoming_committed_needs)
            self.assertTrue(self.plan(u).deals)
        recreated=self.create()
        self.assertEqual(SmartDealRequestCode.CREATED,recreated.code)
        self.assertNotEqual(deal.request_id,recreated.request_id)

    def test_decline_full_cycle(self):self.cycle('decline')
    def test_withdraw_full_cycle(self):self.cycle('withdraw')
    def test_expiry_full_cycle(self):self.cycle('expire',NOW+timedelta(hours=24))

    def test_multi_album_release(self):
        self.configure(25,('vfl','em24'));self.cycle('withdraw')

    def test_large_package_release(self):
        self.configure(150,('vfl','em24'));deal=self.bound()
        self.assertEqual(300,self.release().withdraw(deal.request_id,1).released_count)
        self.assert_terminal(deal,'cancelled')

    def test_before_deadline_still_active(self):
        deal=self.bound();before=self.all_rows();now=NOW+timedelta(hours=24,microseconds=-1)
        self.assertEqual(ReleaseCode.NOT_DUE,self.release(now=now).expire(deal.request_id).code)
        self.assert_reopened(before)
        state=SmartDealPlanningService(self.db,lambda a:self.catalog[a],lambda:now).build(1)
        self.assertEqual((),state.outgoing_supply);self.assertTrue(state.incoming_committed_needs)

    def test_exact_deadline_expired(self):
        deal=self.bound();self.assertEqual(ReleaseCode.RELEASED,self.release(now=NOW+timedelta(hours=24)).expire(deal.request_id).code)
        self.assert_terminal(deal,'expired')

    def test_after_deadline_expired(self):
        deal=self.bound();self.assertEqual(ReleaseCode.RELEASED,self.release(now=NOW+timedelta(hours=24,microseconds=1)).expire(deal.request_id).code)
        self.assert_terminal(deal,'expired')

    def test_reloaded_binding_controls_all_readers_and_retry(self):
        deal=self.bound()
        # created_at is not binding time: changing it must not shorten the deadline.
        self.db.execute("UPDATE trade_requests SET created_at='2000-01-01 00:00:00' WHERE id=?",(deal.request_id,));self.db.commit()
        now=NOW+timedelta(hours=23)
        other=sqlite3.connect(self.path);other.row_factory=sqlite3.Row
        try:
            state=SmartDealPlanningService(other,lambda a:self.catalog[a],lambda:now).build(1)
            self.assertTrue(state.incoming_committed_needs);self.assertEqual((),state.outgoing_supply)
            self.assertEqual(ReleaseCode.NOT_DUE,self.release(other,now).expire(deal.request_id).code)
            self.assertEqual(SmartDealRequestCode.ALREADY_CREATED,self.service(other,now).create_from_suggestion(self.suggestion,1).code)
        finally:other.close()

    def test_quota_uses_binding_time_and_release_frees_slot(self):
        packages=[self.package(str(i)) for i in range(4)]
        ids=[self.create(p).request_id for p in packages[:3]]
        self.db.execute("UPDATE trade_requests SET created_at='2000-01-01' WHERE contract_type='smartdeal_v1'");self.db.commit()
        self.assertEqual(SmartDealRequestCode.LIMIT_REACHED,self.create(packages[3]).code)
        self.release().withdraw(ids[0],1)
        self.assertEqual(SmartDealRequestCode.CREATED,self.create(packages[3]).code)

    def test_wrong_decline_actor(self):
        deal=self.bound();before=self.all_rows()
        for actor in (1,999,True,'2',None):
            self.assertEqual(ReleaseCode.UNAUTHORIZED,self.release().decline(deal.request_id,actor).code)
        self.assert_reopened(before)

    def test_wrong_withdraw_actor(self):
        deal=self.bound();before=self.all_rows()
        for actor in (2,999,True,'1',None):
            self.assertEqual(ReleaseCode.UNAUTHORIZED,self.release().withdraw(deal.request_id,actor).code)
        self.assert_reopened(before)

    def test_legacy_never_released(self):
        request,trade=foundation.planning_fixtures.PlanningStateTests.bind(self)
        self.db.commit();before=self.all_rows()
        for call in (lambda:self.release().expire(request),lambda:self.release().decline(request,2),lambda:self.release().withdraw(request,1)):
            self.assertEqual(ReleaseCode.NOT_V1,call().code)
        self.assertEqual((),self.release(now=NOW+timedelta(days=100)).sweep());self.assert_reopened(before)

    def accepted_fixture(self, deal, status='accepted'):
        self.db.execute('UPDATE trade_requests SET status=?,accepted_at=? WHERE id=?',(status,NOW.isoformat(),deal.request_id))
        self.db.execute("UPDATE trades SET lifecycle_state='accepted' WHERE id=?",(deal.trade_id,));self.db.commit()

    def test_accepted_not_released_by_any_pending_command(self):
        deal=self.bound();self.accepted_fixture(deal);before=self.all_rows()
        for call in (lambda:self.release().withdraw(deal.request_id,1),lambda:self.release().decline(deal.request_id,2),lambda:self.release(now=NOW+timedelta(days=9)).expire(deal.request_id)):
            self.assertEqual(ReleaseCode.NOT_PENDING,call().code)
        self.assertEqual((),self.release(now=NOW+timedelta(days=9)).sweep());self.assert_reopened(before)

    def test_accepted_timestamp_even_if_open_is_protected(self):
        deal=self.bound();self.accepted_fixture(deal,'open');before=self.all_rows()
        self.assertEqual(ReleaseCode.NOT_PENDING,self.release(now=NOW+timedelta(days=9)).expire(deal.request_id).code)
        self.assertEqual((),self.release(now=NOW+timedelta(days=9)).sweep());self.assert_reopened(before)
        with self.assertRaises(ValueError):self.state(1)

    def test_repeated_decline_is_noop_and_notification_once(self):
        deal=self.bound();self.release().decline(deal.request_id,2);before=self.all_rows()
        self.assertEqual(ReleaseCode.ALREADY_RELEASED,self.release().decline(deal.request_id,2).code)
        self.assert_reopened(before)
        rows=self.db.execute("SELECT user_id,notification_type,target_id FROM notifications WHERE notification_type='trade_request_declined'").fetchall()
        self.assertEqual([(1,'trade_request_declined',deal.request_id)],[tuple(r) for r in rows])

    def test_repeated_withdraw_and_conflicting_decline_preserve_terminal(self):
        deal=self.bound();self.release().withdraw(deal.request_id,1);before=self.all_rows()
        self.assertEqual(ReleaseCode.ALREADY_RELEASED,self.release().withdraw(deal.request_id,1).code)
        self.assertEqual('cancelled',self.release().decline(deal.request_id,2).status);self.assert_reopened(before)

    def test_repeated_expire_and_sweep_noop(self):
        deal=self.bound();service=self.release(now=NOW+timedelta(days=1));service.expire(deal.request_id);before=self.all_rows()
        self.assertEqual(ReleaseCode.ALREADY_RELEASED,service.expire(deal.request_id).code)
        self.assertEqual((),service.sweep());self.assert_reopened(before)

    def test_late_user_action_ends_expired_without_decline_notification(self):
        deal=self.bound();before=self.all_rows()['notifications']
        result=self.release(now=NOW+timedelta(days=1)).decline(deal.request_id,2)
        self.assertEqual('expired',result.status);self.assertEqual(before,self.all_rows()['notifications'])

    def test_other_valid_binding_is_retained(self):
        # A real legacy accepted promise over the same resources remains effective.
        for u,keys in ((1,self.outgoing),(2,self.incoming)):
            for a,c in keys:self.quantity(u,a,c,3)
        self.db.commit();deal=self.bound()
        self.binding(1,2,*self.outgoing[0])
        self.binding(2,1,*self.incoming[0])
        before=[tuple(r) for r in self.db.execute('SELECT * FROM trade_reservations WHERE trade_id<>?',(deal.trade_id,))]
        self.release().withdraw(deal.request_id,1)
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM trade_reservations WHERE trade_id<>?',(deal.trade_id,))])
        self.assertNotIn(self.incoming[0],{(p.album_id,p.sticker_code) for p in self.state(1).needs})

    def assert_corruption_rejected(self, sql, args):
        deal=self.bound();self.db.execute(sql,args(deal));self.db.commit();before=self.all_rows()
        with self.assertRaises(ValueError):self.release().withdraw(deal.request_id,1)
        self.assert_reopened(before)

    def test_foreign_lifecycle_owner_rejected(self):
        self.assert_corruption_rejected('UPDATE trades SET requester_user_id=9 WHERE id=?',lambda d:(d.trade_id,))

    def test_foreign_reservation_owner_rejected(self):
        self.assert_corruption_rejected('UPDATE trade_reservations SET user_id=9 WHERE trade_id=?',lambda d:(d.trade_id,))

    def test_cross_linked_reservation_rejected(self):
        deal=self.bound()
        foreign=self.db.execute("INSERT INTO trades(requester_user_id,partner_user_id,lifecycle_state) VALUES (1,2,'accepted')").lastrowid
        self.db.execute('UPDATE trade_reservations SET trade_id=? WHERE id=(SELECT MIN(id) FROM trade_reservations)',(foreign,))
        self.db.commit();before=self.all_rows()
        with self.assertRaises(ValueError):self.release().withdraw(deal.request_id,1)
        self.assert_reopened(before)

    def test_missing_reservation_rejected(self):
        self.assert_corruption_rejected('DELETE FROM trade_reservations WHERE id=(SELECT MIN(id) FROM trade_reservations WHERE trade_id=?)',lambda d:(d.trade_id,))

    def test_shipped_pending_is_not_reset(self):
        deal=self.bound();self.db.execute("INSERT INTO trade_shipping_status(trade_id,requester_shipped,requester_shipped_at) VALUES (?,1,'2026-09-10 12:00:00')",(deal.trade_id,));self.db.commit();before=self.all_rows()
        with self.assertRaises(ValueError):self.release().withdraw(deal.request_id,1)
        self.assert_reopened(before)

    def test_partial_terminal_is_not_silently_accepted_as_noop(self):
        self.assert_corruption_rejected("UPDATE trade_requests SET status='cancelled' WHERE id=?",lambda d:(d.request_id,))

    def test_clock_before_binding_rejected(self):
        deal=self.bound();before=self.all_rows()
        with self.assertRaises(ValueError):self.release(now=NOW-timedelta(seconds=1)).withdraw(deal.request_id,1)
        self.assert_reopened(before)

    def inject(self, sql):
        deal=self.bound();self.db.execute(sql);self.db.commit();before=self.all_rows()
        with self.assertRaises(sqlite3.IntegrityError):self.release().withdraw(deal.request_id,1)
        self.assert_reopened(before)

    def test_rollback_before_status(self):
        self.inject("CREATE TRIGGER inject BEFORE UPDATE OF status ON trade_requests BEGIN SELECT RAISE(ABORT,'status'); END")

    def test_rollback_after_status_before_supply(self):
        self.inject("CREATE TRIGGER inject BEFORE UPDATE ON trade_reservations BEGIN SELECT RAISE(ABORT,'supply'); END")

    def test_rollback_during_second_side(self):
        self.inject("CREATE TRIGGER inject BEFORE UPDATE ON trade_reservations WHEN NEW.user_id=2 BEGIN SELECT RAISE(ABORT,'side B'); END")

    def test_rollback_during_lifecycle(self):
        self.inject("CREATE TRIGGER inject BEFORE UPDATE ON trades BEGIN SELECT RAISE(ABORT,'lifecycle'); END")

    def test_rollback_during_need_projection(self):
        deal=self.bound();before=self.all_rows()
        with patch.object(SmartDealPlanningService,'_project_bindings',side_effect=ValueError('projection')):
            with self.assertRaises(ValueError):self.release().withdraw(deal.request_id,1)
        self.assert_reopened(before)

    def test_rollback_notification(self):
        deal=self.bound();before=self.all_rows()
        with patch.object(TypedNotificationService,'notify_request_declined',side_effect=RuntimeError('notification')):
            with self.assertRaises(RuntimeError):self.release().decline(deal.request_id,2)
        self.assert_reopened(before)

    def test_rollback_commit(self):
        class Connection(sqlite3.Connection):
            def commit(self):raise sqlite3.OperationalError('commit failed before persistence')
        deal=self.bound();before=self.all_rows();other=sqlite3.connect(self.path,factory=Connection);other.row_factory=sqlite3.Row
        try:
            with self.assertRaises(sqlite3.OperationalError):self.release(other).withdraw(deal.request_id,1)
        finally:other.close()
        self.assert_reopened(before)

    def test_race_decline_withdraw(self):
        deal=self.bound()
        a,b=self.race(lambda db:self.release(db).decline(deal.request_id,2),lambda db:self.release(db).withdraw(deal.request_id,1))
        self.assertEqual((ReleaseCode.RELEASED,ReleaseCode.ALREADY_RELEASED),(a.code,b.code));self.assert_terminal(deal,'declined')

    def test_race_expiry_withdraw(self):
        deal=self.bound();now=NOW+timedelta(days=1)
        a,b=self.race(lambda db:self.release(db,now).expire(deal.request_id),lambda db:self.release(db,now).withdraw(deal.request_id,1))
        self.assertEqual((ReleaseCode.RELEASED,ReleaseCode.ALREADY_RELEASED),(a.code,b.code));self.assert_terminal(deal,'expired')

    def test_race_two_expiries(self):
        deal=self.bound();action=lambda db:self.release(db,NOW+timedelta(days=1)).expire(deal.request_id)
        a,b=self.race(action,action)
        self.assertEqual((ReleaseCode.RELEASED,ReleaseCode.ALREADY_RELEASED),(a.code,b.code));self.assert_terminal(deal,'expired')

    def test_race_release_then_new_binding(self):
        deal=self.bound()
        a,b=self.race(lambda db:self.release(db).withdraw(deal.request_id,1),lambda db:self.service(db).create_from_suggestion(self.suggestion,1))
        self.assertEqual(ReleaseCode.RELEASED,a.code);self.assertEqual(SmartDealRequestCode.CREATED,b.code)
        self.assertNotEqual(deal.request_id,b.request_id)
        self.assertEqual(10,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_race_create_first_sees_existing_binding(self):
        deal=self.bound()
        a,b=self.race(lambda db:self.service(db).create_from_suggestion(self.suggestion,1),lambda db:self.release(db).withdraw(deal.request_id,1))
        self.assertEqual(SmartDealRequestCode.ALREADY_CREATED,a.code);self.assertEqual(ReleaseCode.RELEASED,b.code)
        self.assert_terminal(deal,'cancelled')

    def test_sweep_multiple_due_not_future_or_legacy(self):
        packages=[self.package(str(i)) for i in range(3)]
        old=[self.create(p).request_id for p in packages[:2]]
        future=self.service(now=NOW+timedelta(hours=1)).create_from_suggestion(packages[2],1)
        results=self.release(now=NOW+timedelta(days=1)).sweep()
        self.assertEqual(old,[r.request_id for r in results]);self.assertTrue(all(r.code==ReleaseCode.RELEASED for r in results))
        self.assertEqual('open',self.db.execute('SELECT status FROM trade_requests WHERE id=?',(future.request_id,)).fetchone()[0])

    def test_sweep_rollback_whole_pass(self):
        ids=[self.create(self.package(str(i))).request_id for i in range(2)]
        self.db.execute(f"CREATE TRIGGER inject BEFORE UPDATE OF status ON trade_requests WHEN OLD.id={ids[1]} BEGIN SELECT RAISE(ABORT,'second request'); END");self.db.commit();before=self.all_rows()
        with self.assertRaises(sqlite3.IntegrityError):self.release(now=NOW+timedelta(days=1)).sweep()
        self.assert_reopened(before)

    def test_no_read_mutation_before_explicit_sweep(self):
        deal=self.bound();before=self.all_rows();now=NOW+timedelta(days=1)
        state=SmartDealPlanningService(self.db,lambda a:self.catalog[a],lambda:now).build(1)
        self.assertTrue(state.outgoing_supply);self.assert_reopened(before)
        self.release(now=now).sweep();self.assert_terminal(deal,'expired')

    def test_nested_transaction_preserved(self):
        deal=self.bound();self.db.execute('BEGIN IMMEDIATE');before=self.db.total_changes
        with self.assertRaises(ValueError):self.release().withdraw(deal.request_id,1)
        self.assertTrue(self.db.in_transaction);self.assertEqual(before,self.db.total_changes);self.db.rollback()

    def test_busy_is_nonmutating(self):
        deal=self.bound();before=self.all_rows();self.db.execute('BEGIN IMMEDIATE')
        other=sqlite3.connect(self.path,timeout=0);other.row_factory=sqlite3.Row
        try:self.assertEqual(ReleaseCode.BUSY,self.release(other).withdraw(deal.request_id,1).code)
        finally:other.close();self.db.rollback()
        self.assert_reopened(before)

    def test_one_write_transaction_no_optimizer(self):
        deal=self.bound();trace=[];self.db.set_trace_callback(trace.append)
        try:
            with patch.object(SmartDealOptimizer,'optimize',side_effect=AssertionError('optimizer')),patch.object(SmartDealPairwiseService,'from_planning_inputs',side_effect=AssertionError('pairwise')):
                self.release().withdraw(deal.request_id,1)
        finally:self.db.set_trace_callback(None)
        self.assertEqual('BEGIN IMMEDIATE',trace[0]);self.assertEqual('COMMIT',trace[-1]);self.assertEqual(1,sum(s.startswith('BEGIN') for s in trace))

    def test_block_releases_v1_and_keeps_legacy_behavior(self):
        deal=self.bound();CommunityService(self.db).block(1,2)
        row=self.db.execute('SELECT status FROM trade_requests WHERE id=?',(deal.request_id,)).fetchone()
        self.assertIn(row[0],('cancelled','expired'));self.assert_terminal(deal,row[0])
        self.assertEqual(0,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_block_rollback_includes_reservations(self):
        deal=self.bound();before=self.all_rows()
        with patch.object(SmartDealReleaseService,'_verify_released',side_effect=RuntimeError('release')):
            with self.assertRaises(RuntimeError):CommunityService(self.db).block(1,2)
        self.assert_reopened(before)

    def test_block_does_not_release_accepted(self):
        deal=self.bound();self.accepted_fixture(deal);held=[tuple(r) for r in self.db.execute('SELECT * FROM trade_reservations')]
        CommunityService(self.db).block(1,2)
        self.assertEqual(held,[tuple(r) for r in self.db.execute('SELECT * FROM trade_reservations')])
        self.assertEqual('accepted',self.db.execute('SELECT status FROM trade_requests WHERE id=?',(deal.request_id,)).fetchone()[0])

    def test_missing_request_and_invalid_id(self):
        self.assertEqual(ReleaseCode.NOT_FOUND,self.release().expire(99999).code)
        for value in (True,'1',0,None):
            with self.assertRaises(ValueError):self.release().expire(value)

    def test_race_accepted_fact_commits_before_release(self):
        # Test-only future writer: no Accept service/route is implemented here.
        deal=self.bound()
        def accepted_fact(db):
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE trade_requests SET status='accepted',accepted_at=? WHERE id=? AND status='open' AND accepted_at IS NULL",(NOW.isoformat(),deal.request_id))
            db.execute("UPDATE trades SET lifecycle_state='accepted' WHERE id=?",(deal.trade_id,))
            db.commit()
        a,b=self.race(accepted_fact,lambda db:self.release(db,NOW+timedelta(days=1)).expire(deal.request_id))
        self.assertEqual(ReleaseCode.NOT_PENDING,b.code)
        self.assertEqual(10,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_race_terminal_fact_prevents_future_conditional_accept(self):
        deal=self.bound()
        def conditional_accept_probe(db):
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute("UPDATE trade_requests SET status='accepted',accepted_at=? WHERE id=? AND status='open' AND accepted_at IS NULL",(NOW.isoformat(),deal.request_id)).rowcount
            db.rollback()
            return changed
        a,b=self.race(lambda db:self.release(db).withdraw(deal.request_id,1),conditional_accept_probe)
        self.assertEqual(ReleaseCode.RELEASED,a.code);self.assertEqual(0,b);self.assert_terminal(deal,'cancelled')

    def test_receiver_need_fulfilled_after_binding_stays_fulfilled(self):
        deal=self.bound();self.quantity(1,*self.incoming[0],1);self.db.commit()
        self.release().withdraw(deal.request_id,1)
        self.assertNotIn(self.incoming[0],{(p.album_id,p.sticker_code) for p in self.state(1).needs})
        self.assertEqual(1,self.db.execute('SELECT quantity FROM stickers WHERE user_id=1 AND album_id=? AND sticker_code=?',self.incoming[0]).fetchone()[0])

    def test_release_time_single_injected_fact(self):
        deal=self.bound();now=NOW+timedelta(hours=1,microseconds=123)
        self.release(now=now).withdraw(deal.request_id,1)
        self.assertEqual({now.isoformat(timespec='microseconds')},{r[0] for r in self.db.execute('SELECT released_at FROM trade_reservations WHERE trade_id=?',(deal.trade_id,))})
        self.assertEqual(now.isoformat(timespec='microseconds'),self.db.execute('SELECT updated_at FROM trades WHERE id=?',(deal.trade_id,)).fetchone()[0])
        self.assert_terminal(deal,'cancelled')
