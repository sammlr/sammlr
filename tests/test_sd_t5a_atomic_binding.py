"""V21 atomic open bindings, rollback and synchronized multi-connection races."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
import sqlite3
from threading import Barrier, Event
import unittest
from unittest.mock import patch

from tests import test_sd_t4_suggestions as fixtures
from tests import test_sd_t2a_planning_state as planning_fixtures
from services.smartdeal_requests import SmartDealRequestService, SmartDealRequestCode
from services.smartdeal_suggestions import SmartDealSuggestion, SuggestionStatus
from services.smartdeal_optimizer import SmartDealCandidate, SmartDealPiece, SmartDealOptimizer
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.inventory import InventoryReadService
from services.trade_reservations import TradeReservationService


class AtomicBindingTests(unittest.TestCase):
    setUp = fixtures.SuggestionTests.setUp
    configure = fixtures.SuggestionTests.configure
    quantity = fixtures.SuggestionTests.quantity
    plan = fixtures.SuggestionTests.plan
    extra_partner = fixtures.SuggestionTests.extra_partner
    binding = fixtures.SuggestionTests.binding

    def service(self, db=None, now=None):
        return SmartDealRequestService(self.db if db is None else db,lambda a:self.catalog[a],lambda:now or planning_fixtures.NOW)

    def create(self, suggestion=None, actor=1):
        return self.service().create_from_suggestion(self.suggestion if suggestion is None else suggestion,actor)

    def state(self, user):
        return SmartDealPlanningService(self.db,lambda a:self.catalog[a],lambda:planning_fixtures.NOW).build(user)

    def all_rows(self, connection=None):
        db=self.db if connection is None else connection
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t:[tuple(r) for r in db.execute(f'SELECT * FROM "{t}" ORDER BY rowid')] for t in tables}

    def assert_reopened(self, before):
        db=sqlite3.connect(self.path)
        try:
            self.assertEqual(before,self.all_rows(db))
            self.assertEqual([('ok',)],db.execute('pragma integrity_check').fetchall())
            self.assertEqual([],db.execute('pragma foreign_key_check').fetchall())
        finally:db.close()
        self.assertFalse(self.db.in_transaction)

    def package(self, label, partner=2, size=5):
        out,inc=[],[]
        for i in range(size):
            a,b=f'{label}O{i}',f'{label}I{i}'
            self.catalog['vfl'].extend((a,b));self.quantity(1,'vfl',a,2);self.quantity(partner,'vfl',b,2)
            out.append(SmartDealPiece('vfl',a));inc.append(SmartDealPiece('vfl',b))
        self.db.commit()
        return SmartDealSuggestion.from_deal(1,SmartDealCandidate(partner,tuple(out),tuple(inc),size,('vfl',)))

    def test_a_exact_open_v1_request(self):
        result=self.create();self.assertEqual(SmartDealRequestCode.CREATED,result.code)
        row=self.db.execute('SELECT * FROM trade_requests WHERE id=?',(result.request_id,)).fetchone()
        self.assertEqual(('smartdeal_v1','open',None,0,0),(row['contract_type'],row['status'],row['accepted_at'],row['from_confirmed'],row['to_confirmed']))
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='smartdeal_v1'").fetchone()[0])
        self.assertEqual('open',self.db.execute('SELECT lifecycle_state FROM trades WHERE id=?',(result.trade_id,)).fetchone()[0])

    def test_b_multi_album_and_reopened_identity(self):
        self.configure(25,('vfl','em24'));result=self.create()
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
        try:self.assertEqual(self.suggestion.opportunity_identity,self.service(db).identity_for_request(result.request_id))
        finally:db.close()
        self.assertEqual(50,self.db.execute('SELECT COUNT(*) FROM trade_positions').fetchone()[0])

    def test_c_d_e_f_g_h_both_bindings_one_time_no_inventory_or_acceptance(self):
        before=self.all_rows();result=self.create()
        self.assertEqual(SmartDealRequestCode.CREATED,result.code)
        after=self.all_rows()
        changed={t for t in before if before[t]!=after[t]}
        self.assertEqual({'trade_requests','trades','trade_positions','trade_reservations'},changed-{'sqlite_sequence'})
        for user,keys in ((1,self.outgoing),(2,self.incoming)):
            rows=self.db.execute('SELECT album_id,sticker_code,quantity,state,created_at FROM trade_reservations WHERE user_id=?',(user,)).fetchall()
            self.assertEqual(set(keys),{(r[0],r[1]) for r in rows})
            self.assertTrue(all(r[2]==1 and r[3]=='active' for r in rows))
        stamp=self.db.execute('SELECT binding_created_at FROM trade_requests WHERE id=?',(result.request_id,)).fetchone()[0]
        self.assertEqual(planning_fixtures.NOW.isoformat(timespec='microseconds'),stamp)
        for table in ('trade_requests','trades','trade_positions','trade_reservations'):
            clause=" WHERE contract_type='smartdeal_v1'" if table=='trade_requests' else ''
            self.assertEqual({stamp},{r[0] for r in self.db.execute(f'SELECT created_at FROM {table}'+clause)})
        for user,received in ((1,self.incoming),(2,self.outgoing)):
            state=self.state(user)
            self.assertFalse(set(received)&{(p.album_id,p.sticker_code) for p in state.needs})
            self.assertEqual(set(received),{(p.album_id,p.sticker_code) for p in state.incoming_committed_needs})

    def test_i_j_fresh_pipeline_cannot_reuse_bound_resources(self):
        self.create()
        for user in (1,2):
            self.assertEqual((),self.state(user).outgoing_supply)
            self.assertEqual((),self.plan(user).deals)
            snap=InventoryReadService(self.db).snapshot(user,'vfl')
            keys=self.outgoing if user==1 else self.incoming
            self.assertTrue(all(snap.sticker(c).reservable==0 for _,c in keys))

    def test_k_same_actor_retry_preserves_identity_and_timestamp(self):
        result=self.create();before=self.all_rows()
        later=self.service(now=planning_fixtures.NOW+timedelta(hours=1)).create_from_suggestion(self.suggestion,1)
        self.assertEqual(SmartDealRequestCode.ALREADY_CREATED,later.code)
        self.assertEqual(result.request_id,later.request_id)
        self.assertEqual(self.suggestion.opportunity_identity,self.service().identity_for_request(result.request_id))
        self.assert_reopened(before)

    def test_counterpart_same_package_does_not_accept(self):
        first=self.create();before=self.all_rows();other=self.create(actor=2)
        self.assertEqual(SmartDealRequestCode.EXISTING_COUNTERPART_REQUEST,other.code)
        self.assertEqual(first.request_id,other.request_id);self.assert_reopened(before)

    def assert_rejected_without_writes(self, code, suggestion=None):
        before=self.all_rows();digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(code,self.create(suggestion).code)
        self.assert_reopened(before);self.assertEqual(digest,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_l_previous_valid_is_not_write_authorization(self):
        self.assertEqual(SuggestionStatus.VALID,self.validator.validate(self.suggestion,1).status)
        self.quantity(1,*self.outgoing[0],1);self.db.commit()
        self.assert_rejected_without_writes(SmartDealRequestCode.STALE)

    def test_m_invalid_no_writes(self):
        self.assert_rejected_without_writes(SmartDealRequestCode.INVALID_PAYLOAD,replace(self.suggestion,contract_type='legacy'))

    def test_n_a_piece_lost(self):
        self.quantity(1,*self.outgoing[0],1);self.db.commit();self.assert_rejected_without_writes(SmartDealRequestCode.STALE)

    def test_o_b_piece_lost(self):
        self.quantity(2,*self.incoming[0],1);self.db.commit();self.assert_rejected_without_writes(SmartDealRequestCode.STALE)

    def test_p_need_fulfilled(self):
        for receiver,keys in ((1,self.incoming),(2,self.outgoing)):
            self.quantity(receiver,*keys[0],1);self.db.commit();self.assert_rejected_without_writes(SmartDealRequestCode.STALE)
            self.db.execute('DELETE FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?',(receiver,*keys[0]));self.db.commit()

    def test_q_blocked_both_directions(self):
        for a,b in ((1,2),(2,1)):
            self.db.execute('INSERT INTO blocks(blocker_user_id,blocked_user_id) VALUES (?,?)',(a,b));self.db.commit()
            self.assert_rejected_without_writes(SmartDealRequestCode.STALE)
            self.db.execute('DELETE FROM blocks');self.db.commit()

    def injected_sql_failure(self, sql):
        self.db.execute(sql);self.db.commit();before=self.all_rows()
        with self.assertRaises(sqlite3.IntegrityError):self.create()
        self.assert_reopened(before)

    def test_r_failure_at_request_insert(self):
        self.injected_sql_failure("CREATE TRIGGER inject BEFORE INSERT ON trade_requests BEGIN SELECT RAISE(ABORT,'request'); END")

    def test_s_failure_after_request_insert(self):
        self.injected_sql_failure("CREATE TRIGGER inject BEFORE INSERT ON trades BEGIN SELECT RAISE(ABORT,'after request'); END")

    def test_t_failure_a_reservation(self):
        self.injected_sql_failure("CREATE TRIGGER inject BEFORE INSERT ON trade_reservations WHEN NEW.user_id=1 BEGIN SELECT RAISE(ABORT,'A'); END")

    def test_u_failure_b_reservation(self):
        self.injected_sql_failure("CREATE TRIGGER inject BEFORE INSERT ON trade_reservations WHEN NEW.user_id=2 BEGIN SELECT RAISE(ABORT,'B'); END")

    def test_v_failure_need_projection_after_all_reservations(self):
        before=self.all_rows()
        with patch.object(SmartDealRequestService,'_assert_projected',side_effect=RuntimeError('need projection')):
            with self.assertRaises(RuntimeError):self.create()
        self.assert_reopened(before)

    def test_w_failure_binding_timestamp_leaves_nothing_on_reopen(self):
        self.injected_sql_failure("CREATE TRIGGER inject BEFORE UPDATE OF binding_created_at ON trade_requests BEGIN SELECT RAISE(ABORT,'timestamp'); END")

    def test_failure_during_real_t2a_postwrite_need_projection(self):
        original=SmartDealPlanningService._project_bindings
        def project(user,now,rows):
            if any(r['contract_type']=='smartdeal_v1' for r in rows):raise ValueError('synthetic projection failure')
            return original(user,now,rows)
        before=self.all_rows()
        with patch.object(SmartDealPlanningService,'_project_bindings',side_effect=project):
            with self.assertRaises(ValueError):self.create()
        self.assert_reopened(before)

    def test_nested_transaction_is_preserved_and_rejected(self):
        self.quantity(1,'vfl','uncommitted',2);before=self.db.total_changes
        with self.assertRaises(ValueError):self.create()
        self.assertTrue(self.db.in_transaction);self.assertEqual(before,self.db.total_changes);self.db.rollback()

    def test_no_optimizer_in_write_path(self):
        with patch.object(SmartDealOptimizer,'optimize',side_effect=AssertionError('optimizer')),patch.object(SmartDealPairwiseService,'from_planning_inputs',side_effect=AssertionError('pairwise')):
            self.assertEqual(SmartDealRequestCode.CREATED,self.create().code)

    def test_revalidation_occurs_after_write_lock_and_same_clock(self):
        trace=[];self.db.set_trace_callback(trace.append)
        try:self.create()
        finally:self.db.set_trace_callback(None)
        self.assertEqual('BEGIN IMMEDIATE',trace[0]);self.assertEqual('COMMIT',trace[-1])
        self.assertEqual(1,sum(s.startswith('BEGIN') for s in trace))
        first_read=next(i for i,s in enumerate(trace) if s.startswith('SELECT account_state'))
        first_write=next(i for i,s in enumerate(trace) if s.startswith('INSERT INTO trade_requests'))
        self.assertLess(first_read,first_write)

    def test_quota_three_four_and_retry_at_limit(self):
        packages=[self.package(str(i)) for i in range(4)]
        for p in packages[:3]:self.assertEqual(SmartDealRequestCode.CREATED,self.create(p).code)
        self.assert_rejected_without_writes(SmartDealRequestCode.LIMIT_REACHED,packages[3])
        self.assertEqual(SmartDealRequestCode.ALREADY_CREATED,self.create(packages[0]).code)

    def test_legacy_open_requests_do_not_consume_v1_quota(self):
        before=self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='legacy'").fetchone()[0]
        for _ in range(4):self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,from_confirmed) VALUES ('vfl',1,2,'[]','[]',-22)")
        self.db.commit();self.assertEqual(SmartDealRequestCode.CREATED,self.create().code)
        self.assertEqual(before+4,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='legacy'").fetchone()[0])

    def test_existing_legacy_binding_blocks_v1_and_v1_blocks_legacy_accept(self):
        request=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes) VALUES ('vfl',1,2,?,?)",
            (json.dumps([self.outgoing[0][1]]),json.dumps([self.incoming[0][1]]))).lastrowid
        self.db.commit();self.create()
        before=self.all_rows();result=TradeReservationService(self.db).accept(request,2)
        self.assertFalse(result.accepted);self.assert_reopened(before)

    def test_legacy_accept_cannot_accept_v1_empty_legacy_adapter(self):
        result=self.create();before=self.all_rows()
        self.assertFalse(TradeReservationService(self.db).accept(result.request_id,2).accepted)
        self.assert_reopened(before)

    def test_expired_retry_stays_unaccepted_without_cleanup(self):
        result=self.create();before=self.all_rows()
        expired=self.service(now=planning_fixtures.NOW+timedelta(hours=24)).create_from_suggestion(self.suggestion,1)
        self.assertEqual(SmartDealRequestCode.STALE,expired.code);self.assert_reopened(before)
        self.assertIsNotNone(result.request_id)

    def test_new_package_cannot_overdraw_unreleased_expired_supply(self):
        self.create()
        # Different incoming package but same giver's already held outgoing.
        fresh=self.package('fresh')
        from services.smartdeal_identity import SmartDealIdentityService
        different=replace(fresh,side_a_pieces=self.suggestion.side_a_pieces,
            opportunity_identity=SmartDealIdentityService.from_view(1,2,self.suggestion.side_a_pieces,fresh.side_b_pieces))
        before=self.all_rows()
        result=self.service(now=planning_fixtures.NOW+timedelta(hours=24)).create_from_suggestion(different,1)
        self.assertEqual(SmartDealRequestCode.STALE,result.code);self.assert_reopened(before)

    def race(self, first, second):
        """First owns write lock before second attempts BEGIN; no sleeps."""
        held,attempted=Event(),Event();start=Barrier(2)
        path=self.path
        def worker(index,action):
            class Connection(sqlite3.Connection):
                def execute(conn,sql,*args):
                    if sql=='BEGIN IMMEDIATE':
                        if index==1:
                            if not held.wait(10):raise AssertionError('first did not lock')
                            attempted.set()
                        result=super().execute(sql,*args)
                        if index==0:
                            held.set()
                            if not attempted.wait(10):raise AssertionError('second did not attempt')
                        return result
                    return super().execute(sql,*args)
            db=sqlite3.connect(path,factory=Connection);db.row_factory=sqlite3.Row
            try:
                db.execute('PRAGMA foreign_keys=ON');start.wait(10)
                return action(db)
            finally:db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(worker,0,first);b=pool.submit(worker,1,second)
            result=(a.result(timeout=20),b.result(timeout=20))
        self.assertEqual([],self.db.execute('pragma foreign_key_check').fetchall())
        return result

    def test_x_identical_concurrent_creation_once(self):
        action=lambda db:self.service(db).create_from_suggestion(self.suggestion,1)
        a,b=self.race(action,action)
        self.assertEqual((SmartDealRequestCode.CREATED,SmartDealRequestCode.ALREADY_CREATED),(a.code,b.code))
        self.assertEqual(a.request_id,b.request_id)
        self.assertEqual(10,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])

    def test_y_competing_outgoing_copy_only_one_wins(self):
        from services.smartdeal_identity import SmartDealIdentityService
        other=self.package('other')
        side=(self.suggestion.side_a_pieces[0],)+other.side_a_pieces[1:]
        other=replace(other,side_a_pieces=side,opportunity_identity=SmartDealIdentityService.from_view(1,2,side,other.side_b_pieces))
        a,b=self.race(lambda db:self.service(db).create_from_suggestion(self.suggestion,1),lambda db:self.service(db).create_from_suggestion(other,1))
        self.assertEqual((SmartDealRequestCode.CREATED,SmartDealRequestCode.STALE),(a.code,b.code))
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='smartdeal_v1'").fetchone()[0])

    def test_z_competing_incoming_need_with_spare_giver_copies(self):
        from services.smartdeal_identity import SmartDealIdentityService
        other=self.package('other')
        side=(self.suggestion.side_b_pieces[0],)+other.side_b_pieces[1:]
        self.quantity(2,side[0].album_id,side[0].sticker_code,3);self.db.commit()
        other=replace(other,side_b_pieces=side,opportunity_identity=SmartDealIdentityService.from_view(1,2,other.side_a_pieces,side))
        a,b=self.race(lambda db:self.service(db).create_from_suggestion(self.suggestion,1),lambda db:self.service(db).create_from_suggestion(other,1))
        self.assertEqual((SmartDealRequestCode.CREATED,SmartDealRequestCode.STALE),(a.code,b.code))
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='smartdeal_v1'").fetchone()[0])

    def test_aa_legacy_accept_wins_race_v1_cannot_double_reserve(self):
        request=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes) VALUES ('vfl',1,2,?,?)",
            (json.dumps([self.outgoing[0][1]]),json.dumps([self.incoming[0][1]]))).lastrowid
        self.db.commit()
        a,b=self.race(lambda db:TradeReservationService(db).accept(request,2),lambda db:self.service(db).create_from_suggestion(self.suggestion,1))
        self.assertTrue(a.accepted);self.assertEqual(SmartDealRequestCode.STALE,b.code)
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])

    def test_aa_reverse_v1_wins_race_legacy_cannot_double_reserve(self):
        request=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes) VALUES ('vfl',1,2,?,?)",
            (json.dumps([self.outgoing[0][1]]),json.dumps([self.incoming[0][1]]))).lastrowid
        self.db.commit()
        a,b=self.race(lambda db:self.service(db).create_from_suggestion(self.suggestion,1),lambda db:TradeReservationService(db).accept(request,2))
        self.assertEqual(SmartDealRequestCode.CREATED,a.code);self.assertFalse(b.accepted)
        self.assertEqual(10,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])

    def test_concurrent_counterpart_does_not_create_or_accept(self):
        a,b=self.race(lambda db:self.service(db).create_from_suggestion(self.suggestion,1),
                      lambda db:self.service(db).create_from_suggestion(self.suggestion,2))
        self.assertEqual((SmartDealRequestCode.CREATED,SmartDealRequestCode.EXISTING_COUNTERPART_REQUEST),(a.code,b.code))
        self.assertEqual(a.request_id,b.request_id)
        self.assertIsNone(self.db.execute('SELECT accepted_at FROM trade_requests WHERE id=?',(a.request_id,)).fetchone()[0])

    def test_concurrent_third_quota_slot_only_one_creation(self):
        packages=[self.package(str(i)) for i in range(4)]
        for package in packages[:2]:self.assertEqual(SmartDealRequestCode.CREATED,self.create(package).code)
        a,b=self.race(lambda db:self.service(db).create_from_suggestion(packages[2],1),
                      lambda db:self.service(db).create_from_suggestion(packages[3],1))
        self.assertEqual((SmartDealRequestCode.CREATED,SmartDealRequestCode.LIMIT_REACHED),(a.code,b.code))
        self.assertEqual(3,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE contract_type='smartdeal_v1'").fetchone()[0])

    def test_high_id_actor_is_requester_without_reversing_package(self):
        result=self.create(actor=2)
        self.assertEqual(SmartDealRequestCode.CREATED,result.code)
        self.assertEqual((2,1),tuple(self.db.execute('SELECT from_user_id,to_user_id FROM trade_requests WHERE id=?',(result.request_id,)).fetchone()))
        self.assertEqual(self.suggestion.opportunity_identity,self.service().identity_for_request(result.request_id))
        for user in (1,2):self.assertEqual((),self.plan(user).deals)

    def test_remaining_physical_copies_are_not_erased_by_binding(self):
        for user,keys in ((1,self.outgoing),(2,self.incoming)):
            for album,code in keys:self.quantity(user,album,code,3)
        self.db.commit();self.create()
        for user in (1,2):
            self.assertTrue(all(p.quantity==1 for p in self.state(user).outgoing_supply))
            self.assertEqual((),self.plan(user).deals)  # Needs, not spare supply, block reuse.

    def test_lock_exhaustion_reports_busy_without_any_write(self):
        before=self.all_rows()
        self.db.execute('BEGIN IMMEDIATE')
        other=sqlite3.connect(self.path,timeout=0);other.row_factory=sqlite3.Row
        try:
            self.assertEqual(SmartDealRequestCode.BUSY,self.service(other).create_from_suggestion(self.suggestion,1).code)
            self.assertFalse(other.in_transaction)
            self.assertTrue(self.db.in_transaction)
        finally:other.close();self.db.rollback()
        self.assert_reopened(before)

    def test_commit_failure_rolls_back_all(self):
        class FailedCommit(sqlite3.Connection):
            def commit(self):raise sqlite3.OperationalError('injected before commit')
        before=self.all_rows();other=sqlite3.connect(self.path,factory=FailedCommit);other.row_factory=sqlite3.Row
        try:
            with self.assertRaises(sqlite3.OperationalError):self.service(other).create_from_suggestion(self.suggestion,1)
            self.assertFalse(other.in_transaction)
        finally:other.close()
        self.assert_reopened(before)

    def test_terminal_prior_occurrence_does_not_permanently_block_identity(self):
        first=self.create()
        # Fixture represents a future completed release, not a new T5b service.
        self.db.execute("UPDATE trade_reservations SET state='released',released_at='2026-09-10 12:00:00',release_reason='fixture' WHERE trade_id=?",(first.trade_id,))
        self.db.execute("UPDATE trades SET lifecycle_state='cancelled' WHERE id=?",(first.trade_id,))
        self.db.execute("UPDATE trade_requests SET status='cancelled' WHERE id=?",(first.request_id,));self.db.commit()
        second=self.create()
        self.assertEqual(SmartDealRequestCode.CREATED,second.code);self.assertNotEqual(first.request_id,second.request_id)
        self.assertEqual(self.service().identity_for_request(first.request_id),self.service().identity_for_request(second.request_id))
