"""V21 accept/mutual GO contracts on synthetic databases and real writer races."""
from dataclasses import replace
from datetime import timedelta
import sqlite3
import unittest
from unittest.mock import patch

from tests import test_sd_t5b_release_expiry as foundation
NOW = foundation.NOW
from services.smartdeal_acceptance import SmartDealAcceptanceService, AcceptanceCode as Code
from services.smartdeal_release import ReleaseCode
from services.smartdeal_requests import SmartDealRequestCode
from services.smartdeal_suggestions import SmartDealSuggestion, SuggestionStatus
from services.smartdeal_identity import SmartDealIdentityService, SmartDealOpportunityIdentity
from services.smartdeal_optimizer import SmartDealPiece, SmartDealOptimizer
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_expiry import utc_instant
from services.smart_trade_requests import SMART_ACCEPTED_EVENT


class AcceptTests(unittest.TestCase):
    setUp=foundation.ReleaseTests.setUp
    configure=foundation.ReleaseTests.configure
    quantity=foundation.ReleaseTests.quantity
    plan=foundation.ReleaseTests.plan
    extra_partner=foundation.ReleaseTests.extra_partner
    binding=foundation.ReleaseTests.binding
    service=foundation.ReleaseTests.service
    create=foundation.ReleaseTests.create
    state=foundation.ReleaseTests.state
    all_rows=foundation.ReleaseTests.all_rows
    assert_reopened=foundation.ReleaseTests.assert_reopened
    package=foundation.ReleaseTests.package
    race=foundation.ReleaseTests.race
    release=foundation.ReleaseTests.release
    bound=foundation.ReleaseTests.bound
    assert_terminal=foundation.ReleaseTests.assert_terminal

    def core(self,db=None,now=NOW):
        return SmartDealAcceptanceService(self.db if db is None else db,lambda a:self.catalog[a],lambda:now)

    def go(self,actor=1,payload=None,now=NOW):
        return self.core(now=now).go(self.suggestion if payload is None else payload,actor)

    def assert_accepted(self,deal,stamp=NOW):
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
        try:
            q=db.execute('SELECT * FROM trade_requests WHERE id=?',(deal.request_id,)).fetchone()
            self.assertEqual(('smartdeal_v1','accepted',0,0),(q['contract_type'],q['status'],q['from_confirmed'],q['to_confirmed']))
            self.assertEqual(stamp,utc_instant(q['accepted_at']));self.assertEqual(NOW,utc_instant(q['binding_created_at']))
            self.assertEqual('accepted',db.execute('SELECT lifecycle_state FROM trades WHERE id=?',(deal.trade_id,)).fetchone()[0])
            self.assertEqual(self.suggestion.opportunity_identity,self.service(db).identity_for_request(deal.request_id))
            rows=db.execute('SELECT * FROM trade_reservations WHERE trade_id=?',(deal.trade_id,)).fetchall()
            self.assertEqual(2*self.suggestion.piece_count,len(rows));self.assertTrue(all(r['state']=='active' and r['released_at'] is None for r in rows))
            events=db.execute('SELECT * FROM trade_events WHERE trade_id=? AND event_type=?',(deal.trade_id,SMART_ACCEPTED_EVENT)).fetchall()
            self.assertEqual(1,len(events));self.assertEqual(stamp,utc_instant(events[0]['occurred_at']))
            self.assertEqual('ok',db.execute('PRAGMA integrity_check').fetchone()[0]);self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
        finally:db.close()

    def test_explicit_accept_and_exact_mutation_set(self):
        deal=self.bound();before=self.all_rows();stamp=NOW+timedelta(hours=1)
        result=self.core(now=stamp).accept(deal.request_id,2)
        self.assertEqual(Code.ACCEPTED,result.code);self.assert_accepted(deal,stamp)
        after=self.all_rows()
        self.assertEqual({'trade_requests','trades','trade_events','sqlite_sequence'},{t for t in before if before[t]!=after[t]})
        self.assertEqual(before['stickers'],after['stickers']);self.assertEqual(before['trade_reservations'],after['trade_reservations'])
        self.assertEqual(before['trade_positions'],after['trade_positions']);self.assertEqual(before['notifications'],after['notifications'])

    def test_accepted_pipeline_remains_bound_after_24h(self):
        deal=self.bound();self.core().accept(deal.request_id,2)
        for u in (1,2):
            state=SmartDealPlanningService(self.db,lambda a:self.catalog[a],lambda:NOW+timedelta(days=3)).build(u)
            self.assertEqual((),state.outgoing_supply);self.assertTrue(state.incoming_committed_needs)
            self.assertEqual((),self.plan(u).deals)
        before=self.all_rows();self.assertEqual((),self.release(now=NOW+timedelta(days=3)).sweep());self.assert_reopened(before)

    def test_mutual_go_existing_request(self):
        first=self.go();self.assertEqual(Code.CREATED,first.code)
        second=self.go(2);self.assertEqual(Code.ACCEPTED,second.code)
        self.assertEqual(first.request_id,second.request_id);self.assert_accepted(second)
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='smartdeal_v1'").fetchone()[0])

    def test_mirrored_go(self):
        mirror=SmartDealSuggestion.from_deal(2,self.plan(2).deals[0]);self.assertEqual(self.suggestion,mirror)
        first=self.go(2,mirror);result=self.go(1)
        self.assertEqual(Code.ACCEPTED,result.code);self.assertEqual(first.request_id,result.request_id);self.assert_accepted(result)

    def test_rank_change_does_not_gate_accept(self):
        original=self.suggestion;self.extra_partner(10)
        plan=self.plan();self.assertEqual(2, next(i+1 for i,d in enumerate(plan.deals) if d.partner_id==2))
        first=self.go(payload=original);self.assertEqual(Code.CREATED,first.code)
        self.assertEqual(Code.ACCEPTED,self.go(2,original).code)

    def test_multi_album_mutual_go(self):
        self.configure(25,('vfl','em24'));self.go();result=self.go(2);self.assertEqual(Code.ACCEPTED,result.code);self.assert_accepted(result)

    def test_large_mutual_go(self):
        self.configure(150,('vfl','em24'));self.go();result=self.go(2);self.assertEqual(Code.ACCEPTED,result.code);self.assert_accepted(result)

    def test_initiator_cannot_explicit_accept(self):
        deal=self.bound();before=self.all_rows();self.assertEqual(Code.UNAUTHORIZED,self.core().accept(deal.request_id,1).code);self.assert_reopened(before)

    def test_third_and_noncanonical_actor_rejected(self):
        deal=self.bound();before=self.all_rows()
        for actor in (999,True,'2',None):self.assertEqual(Code.UNAUTHORIZED,self.core().accept(deal.request_id,actor).code)
        self.assert_reopened(before)

    def test_legacy_rejected(self):
        legacy=self.db.execute("SELECT id FROM trade_requests WHERE contract_type='legacy' LIMIT 1").fetchone()[0]
        before=self.all_rows();self.assertEqual(Code.NOT_V1,self.core().accept(legacy,2).code);self.assert_reopened(before)

    def test_before_deadline_accepts(self):
        deal=self.bound();now=NOW+timedelta(hours=24,microseconds=-1)
        self.assertEqual(Code.ACCEPTED,self.core(now=now).accept(deal.request_id,2).code);self.assert_accepted(deal,now)

    def test_exact_deadline_uses_t5b_release(self):
        deal=self.bound();self.assertEqual(Code.EXPIRED,self.core(now=NOW+timedelta(days=1)).accept(deal.request_id,2).code);self.assert_terminal(deal,'expired')

    def test_after_deadline_mutual_go_releases_without_new_request(self):
        first=self.go();result=self.go(2,now=NOW+timedelta(days=1,microseconds=1))
        self.assertEqual(Code.EXPIRED,result.code);self.assert_terminal(first,'expired')
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='smartdeal_v1'").fetchone()[0])

    def test_declined_not_accepted(self):
        deal=self.bound();self.release().decline(deal.request_id,2);before=self.all_rows()
        self.assertEqual(Code.NOT_PENDING,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_withdrawn_not_accepted(self):
        deal=self.bound();self.release().withdraw(deal.request_id,1);before=self.all_rows()
        self.assertEqual(Code.NOT_PENDING,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_terminal_instance_does_not_block_new_opportunity(self):
        first=self.go();self.release().withdraw(first.request_id,1);second=self.go(2)
        self.assertEqual(Code.CREATED,second.code);self.assertNotEqual(first.request_id,second.request_id)

    def corrupt(self,sql,args):
        deal=self.bound();self.db.execute(sql,args(deal));self.db.commit();before=self.all_rows()
        with self.assertRaises(ValueError):self.core().accept(deal.request_id,2)
        self.assert_reopened(before)

    def test_foreign_position_rejected(self):
        self.corrupt('UPDATE trade_positions SET to_user_id=9 WHERE trade_id=?',lambda d:(d.trade_id,))

    def test_mismatched_position_quantity_rejected(self):
        self.corrupt('UPDATE trade_positions SET quantity=2 WHERE trade_id=?',lambda d:(d.trade_id,))

    def test_missing_reservation_rejected(self):
        self.corrupt('DELETE FROM trade_reservations WHERE id=(SELECT MIN(id) FROM trade_reservations WHERE trade_id=?)',lambda d:(d.trade_id,))

    def test_foreign_reservation_owner_rejected(self):
        self.corrupt('UPDATE trade_reservations SET user_id=9 WHERE trade_id=?',lambda d:(d.trade_id,))

    def test_open_with_acceptance_time_is_corruption(self):
        self.corrupt('UPDATE trade_requests SET accepted_at=? WHERE id=?',lambda d:(NOW.isoformat(),d.request_id))

    def test_foreign_lifecycle_owner_rejected(self):
        self.corrupt('UPDATE trades SET requester_user_id=9 WHERE id=?',lambda d:(d.trade_id,))

    def other_payload(self):
        other=self.package('other')
        side=(other.side_b_pieces[0],)+self.suggestion.side_b_pieces[1:]
        return replace(self.suggestion,side_b_pieces=side,opportunity_identity=SmartDealIdentityService.from_view(1,2,self.suggestion.side_a_pieces,side))

    def test_same_pair_size_albums_different_piece_is_not_mutual(self):
        other=self.other_payload();deal=self.bound();before=self.all_rows()
        self.assertEqual(Code.STALE,self.go(2,other).code);self.assert_reopened(before)
        self.assertEqual('open',self.db.execute('SELECT status FROM trade_requests WHERE id=?',(deal.request_id,)).fetchone()[0])

    def test_disjoint_other_package_can_create_without_accepting_first(self):
        other=self.package('other');deal=self.bound();new=self.go(2,other)
        self.assertEqual(Code.CREATED,new.code);self.assertNotEqual(deal.request_id,new.request_id)
        self.assertEqual('open',self.db.execute('SELECT status FROM trade_requests WHERE id=?',(deal.request_id,)).fetchone()[0])

    def test_invalid_payload_no_writes(self):
        before=self.all_rows();self.assertEqual(Code.INVALID_PAYLOAD,self.go(2,replace(self.suggestion,piece_count=6)).code);self.assert_reopened(before)

    def test_digest_collision_never_merges(self):
        other=self.other_payload();self.bound();before=self.all_rows()
        # Force all freshly reconstructed digests to collide; full fields differ.
        class Collision:
            def hexdigest(self):return '0'*64
        with patch('services.smartdeal_identity.hashlib.sha256',return_value=Collision()):
            identity=SmartDealIdentityService.from_view(1,2,other.side_a_pieces,other.side_b_pieces)
            self.assertEqual(Code.STALE,self.go(2,replace(other,opportunity_identity=identity)).code)
        self.assert_reopened(before)

    def test_t4_free_validation_stale_but_exact_bound_accept_valid(self):
        self.bound();self.assertEqual(SuggestionStatus.STALE,self.validator.validate(self.suggestion,2).status)
        self.assertEqual(Code.ACCEPTED,self.go(2).code)

    def test_current_inventory_loss_is_stale(self):
        deal=self.bound();self.quantity(1,*self.outgoing[0],1);self.db.commit();before=self.all_rows()
        self.assertEqual(Code.STALE,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_current_need_fulfilled_is_stale(self):
        deal=self.bound();self.quantity(2,*self.outgoing[0],1);self.db.commit();before=self.all_rows()
        self.assertEqual(Code.STALE,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_foreign_promised_need_stays_protected(self):
        deal=self.bound();self.quantity(2,*self.incoming[0],3);self.db.commit();self.binding(2,1,*self.incoming[0]);before=self.all_rows()
        self.assertEqual(Code.STALE,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_block_is_stale_without_bypassing_eligibility(self):
        deal=self.bound();self.db.execute('INSERT INTO blocks(blocker_user_id,blocked_user_id) VALUES (2,1)');self.db.commit();before=self.all_rows()
        self.assertEqual(Code.STALE,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_pool_revoked_is_stale(self):
        deal=self.bound();self.db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2');self.db.commit();before=self.all_rows()
        self.assertEqual(Code.STALE,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_inactive_partner_is_stale(self):
        deal=self.bound();self.db.execute("UPDATE users SET account_state='deactivated' WHERE id=2");self.db.commit();before=self.all_rows()
        self.assertEqual(Code.STALE,self.core().accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_idempotent_accept(self):
        deal=self.bound();self.core().accept(deal.request_id,2);before=self.all_rows()
        self.assertEqual(Code.ALREADY_ACCEPTED,self.core(now=NOW+timedelta(days=3)).accept(deal.request_id,2).code);self.assert_reopened(before)

    def test_idempotent_counterpart_go_after_accept(self):
        self.go();first=self.go(2);before=self.all_rows()
        again=self.go(2,now=NOW+timedelta(days=3));self.assertEqual(Code.ALREADY_ACCEPTED,again.code)
        self.assertEqual(first.request_id,again.request_id);self.assert_reopened(before)

    def test_idempotent_initiator_go_stays_pending(self):
        first=self.go();before=self.all_rows();again=self.go()
        self.assertEqual(Code.ALREADY_CREATED,again.code);self.assertEqual(first.request_id,again.request_id);self.assert_reopened(before)

    def test_idempotent_parallel_same_actor(self):
        action=lambda db:self.core(db).go(self.suggestion,1)
        a,b=self.race(action,action);self.assertEqual((Code.CREATED,Code.ALREADY_CREATED),(a.code,b.code))
        self.assertEqual(a.request_id,b.request_id);self.assertIsNone(self.db.execute('SELECT accepted_at FROM trade_requests WHERE id=?',(a.request_id,)).fetchone()[0])

    def test_race_a_go_b_go(self):
        a,b=self.race(lambda db:self.core(db).go(self.suggestion,1),lambda db:self.core(db).go(self.suggestion,2))
        self.assertEqual((Code.CREATED,Code.ACCEPTED),(a.code,b.code));self.assertEqual(a.request_id,b.request_id);self.assert_accepted(b)

    def test_race_b_go_a_go(self):
        a,b=self.race(lambda db:self.core(db).go(self.suggestion,2),lambda db:self.core(db).go(self.suggestion,1))
        self.assertEqual((Code.CREATED,Code.ACCEPTED),(a.code,b.code));self.assertEqual(a.request_id,b.request_id);self.assert_accepted(b)

    def test_race_accept_go(self):
        deal=self.bound();a,b=self.race(lambda db:self.core(db).accept(deal.request_id,2),lambda db:self.core(db).go(self.suggestion,2))
        self.assertEqual((Code.ACCEPTED,Code.ALREADY_ACCEPTED),(a.code,b.code));self.assert_accepted(deal)

    def test_race_go_accept(self):
        deal=self.bound();a,b=self.race(lambda db:self.core(db).go(self.suggestion,2),lambda db:self.core(db).accept(deal.request_id,2))
        self.assertEqual((Code.ACCEPTED,Code.ALREADY_ACCEPTED),(a.code,b.code));self.assert_accepted(deal)

    def test_race_accept_decline(self):
        deal=self.bound();a,b=self.race(lambda db:self.core(db).accept(deal.request_id,2),lambda db:self.release(db).decline(deal.request_id,2))
        self.assertEqual(Code.ACCEPTED,a.code);self.assertEqual(ReleaseCode.NOT_PENDING,b.code);self.assert_accepted(deal)

    def test_race_decline_accept(self):
        deal=self.bound();a,b=self.race(lambda db:self.release(db).decline(deal.request_id,2),lambda db:self.core(db).accept(deal.request_id,2))
        self.assertEqual(ReleaseCode.RELEASED,a.code);self.assertEqual(Code.NOT_PENDING,b.code);self.assert_terminal(deal,'declined')

    def test_race_accept_withdraw(self):
        deal=self.bound();a,b=self.race(lambda db:self.core(db).accept(deal.request_id,2),lambda db:self.release(db).withdraw(deal.request_id,1))
        self.assertEqual(Code.ACCEPTED,a.code);self.assertEqual(ReleaseCode.NOT_PENDING,b.code);self.assert_accepted(deal)

    def test_race_withdraw_accept(self):
        deal=self.bound();a,b=self.race(lambda db:self.release(db).withdraw(deal.request_id,1),lambda db:self.core(db).accept(deal.request_id,2))
        self.assertEqual(ReleaseCode.RELEASED,a.code);self.assertEqual(Code.NOT_PENDING,b.code);self.assert_terminal(deal,'cancelled')

    def test_race_before_deadline_accept_then_due_expiry(self):
        deal=self.bound();now=NOW+timedelta(days=1,microseconds=-1)
        a,b=self.race(lambda db:self.core(db,now).accept(deal.request_id,2),lambda db:self.release(db,NOW+timedelta(days=1)).expire(deal.request_id))
        self.assertEqual(Code.ACCEPTED,a.code);self.assertEqual(ReleaseCode.NOT_PENDING,b.code);self.assert_accepted(deal,now)

    def test_race_due_accept_first_still_expires(self):
        deal=self.bound();now=NOW+timedelta(days=1)
        a,b=self.race(lambda db:self.core(db,now).accept(deal.request_id,2),lambda db:self.release(db,now).expire(deal.request_id))
        self.assertEqual(Code.EXPIRED,a.code);self.assertEqual(ReleaseCode.ALREADY_RELEASED,b.code);self.assert_terminal(deal,'expired')

    def test_race_due_expiry_first(self):
        deal=self.bound();now=NOW+timedelta(days=1)
        a,b=self.race(lambda db:self.release(db,now).expire(deal.request_id),lambda db:self.core(db,now).accept(deal.request_id,2))
        self.assertEqual(ReleaseCode.RELEASED,a.code);self.assertEqual(Code.NOT_PENDING,b.code);self.assert_terminal(deal,'expired')

    def test_race_other_opportunity_never_bypasses_binding(self):
        other=self.other_payload()
        a,b=self.race(lambda db:self.core(db).go(self.suggestion,1),lambda db:self.core(db).go(other,2))
        self.assertEqual((Code.CREATED,Code.STALE),(a.code,b.code))

    def inject(self,sql,mutual=False):
        deal=self.bound();self.db.execute(sql);self.db.commit();before=self.all_rows()
        with self.assertRaises(sqlite3.IntegrityError):
            self.go(2) if mutual else self.core().accept(deal.request_id,2)
        self.assert_reopened(before)

    def test_rollback_before_status(self):
        self.inject("CREATE TRIGGER inject BEFORE UPDATE OF status ON trade_requests BEGIN SELECT RAISE(ABORT,'status'); END")

    def test_rollback_after_status_during_acceptance_time(self):
        self.inject("CREATE TRIGGER inject AFTER UPDATE OF accepted_at ON trade_requests WHEN NEW.accepted_at IS NOT NULL BEGIN SELECT RAISE(ABORT,'timestamp'); END")

    def test_rollback_lifecycle(self):
        self.inject("CREATE TRIGGER inject BEFORE UPDATE ON trades BEGIN SELECT RAISE(ABORT,'lifecycle'); END")

    def test_rollback_acceptance_event(self):
        self.inject("CREATE TRIGGER inject BEFORE INSERT ON trade_events BEGIN SELECT RAISE(ABORT,'event'); END")

    def test_rollback_mutual_mid_transition(self):
        self.inject("CREATE TRIGGER inject BEFORE INSERT ON trade_events BEGIN SELECT RAISE(ABORT,'mutual'); END",True)

    def test_rollback_postwrite_projection(self):
        deal=self.bound();before=self.all_rows()
        with patch.object(self.core()._requests.__class__,'_assert_projected',side_effect=RuntimeError('postwrite')):
            with self.assertRaises(RuntimeError):self.core().accept(deal.request_id,2)
        self.assert_reopened(before)

    def test_rollback_commit(self):
        class Connection(sqlite3.Connection):
            def commit(self):raise sqlite3.OperationalError('failure before commit')
        deal=self.bound();before=self.all_rows();db=sqlite3.connect(self.path,factory=Connection);db.row_factory=sqlite3.Row
        try:
            with self.assertRaises(sqlite3.OperationalError):self.core(db).accept(deal.request_id,2)
        finally:db.close()
        self.assert_reopened(before)

    def test_no_global_reoptimization(self):
        self.go()
        with patch.object(SmartDealOptimizer,'optimize',side_effect=AssertionError('optimizer')),patch.object(SmartDealPairwiseService,'from_planning_inputs',side_effect=AssertionError('pairwise')):
            self.assertEqual(Code.ACCEPTED,self.go(2).code)

    def test_nested_transaction_preserved(self):
        deal=self.bound();self.db.execute('BEGIN IMMEDIATE')
        with self.assertRaises(ValueError):self.core().accept(deal.request_id,2)
        self.assertTrue(self.db.in_transaction);self.db.rollback()

    def test_busy_no_mutations(self):
        deal=self.bound();before=self.all_rows();self.db.execute('BEGIN IMMEDIATE');db=sqlite3.connect(self.path,timeout=0);db.row_factory=sqlite3.Row
        try:self.assertEqual(Code.BUSY,self.core(db).accept(deal.request_id,2).code)
        finally:db.close();self.db.rollback()
        self.assert_reopened(before)

    def test_full_outgoing_quota_does_not_block_incoming_accept(self):
        # Three disjoint outgoing B requests, plus incoming A request: accept uses no slot.
        packages=[self.package(str(i)) for i in range(3)]
        for payload in packages:self.assertEqual(Code.CREATED,self.go(2,payload).code)
        first=self.go(1);self.assertEqual(Code.CREATED,first.code)
        self.assertEqual(Code.ACCEPTED,self.go(2).code)

    def test_lookup_several_active_requests(self):
        packages=[self.package(str(i)) for i in range(3)]
        ids=[self.go(1,p).request_id for p in packages]
        before=self.all_rows();trace=[];self.db.execute('BEGIN IMMEDIATE');self.db.set_trace_callback(trace.append)
        try:self.assertEqual(ids[2],self.core()._lookup(packages[2].opportunity_identity)['id'])
        finally:self.db.set_trace_callback(None);self.db.rollback()
        self.assertEqual(2,len(trace));self.assert_reopened(before)

    def test_request_id_validation(self):
        self.assertEqual(Code.NOT_FOUND,self.core().accept(9999,2).code)
        for value in (0,True,'1',None):
            with self.assertRaises(ValueError):self.core().accept(value,2)

    def test_race_four_go_intentions_one_instance(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier=Barrier(4)
        def action(actor):
            db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
            try:
                db.execute('PRAGMA foreign_keys=ON');barrier.wait(10)
                return self.core(db).go(self.suggestion,actor)
            finally:db.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(action,(1,2,1,2)))
        self.assertEqual(1,sum(r.code==Code.CREATED for r in results))
        self.assertEqual(1,sum(r.code==Code.ACCEPTED for r in results))
        self.assertEqual(1,len({r.request_id for r in results}))
        self.assert_accepted(next(r for r in results if r.code==Code.ACCEPTED))
