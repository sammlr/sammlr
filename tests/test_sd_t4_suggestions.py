"""Exact package A–Z contracts against fresh synthetic V21 planning snapshots."""
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import sqlite3
import unittest
from unittest.mock import patch

from tests import test_sd_t2a_planning_state as fixtures
from services.smartdeal_identity import SmartDealIdentityService
from services.smartdeal_optimizer import SmartDealOptimizer, SmartDealPiece
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_suggestions import SmartDealSuggestion, SmartDealSuggestionValidator, SuggestionStatus


class SuggestionTests(unittest.TestCase):
    quantity = fixtures.PlanningStateTests.quantity

    def setUp(self):
        fixtures.PlanningStateTests.setUp(self)
        self.configure()

    def configure(self, size=5, albums=('vfl',)):
        self.db.execute('DELETE FROM stickers')
        self.catalog = {'vfl': [], 'em24': []}
        self.outgoing, self.incoming = [], []
        for i in range(size):
            album = albums[i % len(albums)]
            out, inc = f'O{i:04}', f'I{i:04}'
            self.catalog[album].extend((out, inc))
            self.quantity(1, album, out, 2);self.quantity(2, album, inc, 2)
            self.outgoing.append((album, out));self.incoming.append((album, inc))
        self.db.commit()
        self.validator = SmartDealSuggestionValidator(self.db, lambda a: self.catalog[a], lambda: fixtures.NOW)
        self.suggestion = SmartDealSuggestion.from_deal(1, self.plan(1).deals[0])

    def plan(self, user=1):
        inputs = SmartDealPlanningService(self.db, lambda a: self.catalog[a], lambda: fixtures.NOW).build_pairwise_inputs(user)
        return SmartDealOptimizer.optimize(inputs.subject, SmartDealPairwiseService.from_planning_inputs(inputs))

    def check(self, status=SuggestionStatus.VALID, suggestion=None, actor=1):
        result = self.validator.validate(self.suggestion if suggestion is None else suggestion, actor)
        self.assertEqual(status, result.status, result)
        return result

    def extra_partner(self, size=8):
        user = self.db.execute("INSERT INTO users(username,password,name) VALUES ('sdt4-third','synthetic','Synthetic')").lastrowid
        for album in self.catalog:
            self.db.execute('INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,?,1)', (user, album))
        for i in range(size):
            out, inc = f'otherO{i}', f'otherI{i}'
            self.catalog['vfl'].extend((out, inc))
            self.quantity(1,'vfl',out,2);self.quantity(user,'vfl',inc,2)
        self.db.commit()
        return user

    def binding(self, giver, receiver, album, code):
        # Existing legacy accepted single-sided manual binding: real canonical
        # reservation/position facts, no V1 writer or request implementation.
        request = self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,status) VALUES (?,?,?,'accepted')", (album,giver,receiver)).lastrowid
        trade = self.db.execute("INSERT INTO trades(legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (?,?,?,'accepted')", (request,giver,receiver)).lastrowid
        position = self.db.execute('INSERT INTO trade_positions(trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (?,?,?,?,?,1)',(trade,giver,receiver,album,code)).lastrowid
        self.db.execute('INSERT INTO trade_reservations(trade_id,trade_position_id,user_id,album_id,sticker_code,quantity) VALUES (?,?,?,?,?,1)',(trade,position,giver,album,code))
        self.db.commit()
        return trade

    def release_fixture_bindings(self):
        self.db.execute("UPDATE trade_reservations SET state='released',released_at='2026-09-11 00:00:00',release_reason='synthetic-release'")
        self.db.execute("UPDATE trades SET lifecycle_state='cancelled'")
        self.db.execute("UPDATE trade_requests SET status='cancelled'")
        self.db.commit()

    def test_a_fresh_five_by_five(self):self.check()

    def test_b_multi_album_twenty_five(self):
        self.configure(25, ('vfl','em24'));self.check();self.check(actor=2)
        self.assertEqual(('em24','vfl'), self.suggestion.involved_albums)

    def test_c_actual_mirrored_optimizer_payload_is_identical(self):
        mirror = SmartDealSuggestion.from_deal(2, self.plan(2).deals[0])
        self.assertEqual(self.suggestion, mirror);self.check(suggestion=mirror,actor=2)

    def test_d_rank_changes_but_exact_package_remains_valid(self):
        user = self.extra_partner()
        for album,code in self.outgoing:self.quantity(user,album,code,1)
        for code in self.catalog['vfl']:
            if code.startswith('otherO'):self.quantity(2,'vfl',code,1)
        self.db.commit()
        plan = self.plan()
        self.assertEqual(2, plan.deals[1].partner_id)
        self.assertEqual(self.suggestion, SmartDealSuggestion.from_deal(1,plan.deals[1]))
        self.check()

    def test_e_better_alternative_outside_current_plan_does_not_invalidate(self):
        # New partner can use all old resources plus one extra in each direction.
        user = self.extra_partner(1)
        for album,code in self.incoming:self.quantity(user,album,code,2)
        self.db.commit()
        self.assertNotIn(2, [d.partner_id for d in self.plan().deals])
        self.check()

    def test_f_irrelevant_inventory_change(self):
        self.quantity(1,'vfl','irrelevant',1);self.db.commit();self.check()

    def test_g_additional_free_copies(self):
        for user, keys in ((1,self.outgoing),(2,self.incoming)):
            self.quantity(user,*keys[0],5)
        self.db.commit();self.check()

    def test_h_other_partner_inventory_change(self):
        user = self.extra_partner()
        self.quantity(user,'vfl','unrelated',5);self.db.commit();self.check()

    def test_i_repeated_validation_deterministic_and_input_immutable(self):
        before = asdict(self.suggestion)
        self.assertEqual(self.check(), self.check())
        self.assertEqual(before, asdict(self.suggestion))
        with self.assertRaises(FrozenInstanceError):self.suggestion.piece_count = 9

    def test_j_a_loses_outgoing(self):
        self.db.execute('DELETE FROM stickers WHERE user_id=1 AND album_id=? AND sticker_code=?',self.outgoing[0]);self.db.commit()
        self.check(SuggestionStatus.STALE)

    def test_k_b_loses_outgoing(self):
        self.db.execute('DELETE FROM stickers WHERE user_id=2 AND album_id=? AND sticker_code=?',self.incoming[0]);self.db.commit()
        self.check(SuggestionStatus.STALE)

    def test_l_last_copy_is_not_free_supply(self):
        for user,keys in ((1,self.outgoing),(2,self.incoming)):
            self.quantity(user,*keys[0],1);self.db.commit();self.check(SuggestionStatus.STALE)
            self.quantity(user,*keys[0],2);self.db.commit();self.check()

    def test_m_a_receives_expected_incoming_elsewhere(self):
        self.quantity(1,*self.incoming[0],1);self.db.commit();self.check(SuggestionStatus.STALE)

    def test_n_b_receives_expected_incoming_elsewhere(self):
        self.quantity(2,*self.outgoing[0],1);self.db.commit();self.check(SuggestionStatus.STALE)

    def test_o_expected_need_bound_elsewhere_both_sides(self):
        user = self.extra_partner()
        for receiver,keys in ((1,self.incoming),(2,self.outgoing)):
            self.quantity(user,*keys[0],2)
            self.binding(user,receiver,*keys[0])
            self.assertEqual('need_unavailable', self.check(SuggestionStatus.STALE).reason)
            self.release_fixture_bindings();self.check()

    def test_p_supply_reserved_elsewhere_both_sides(self):
        user = self.extra_partner()
        self.binding(1,user,*self.outgoing[0]);self.check(SuggestionStatus.STALE)
        self.release_fixture_bindings();self.check()
        self.binding(2,user,*self.incoming[0]);self.check(SuggestionStatus.STALE)

    def test_q_blocks_both_directions(self):
        for a,b in ((1,2),(2,1)):
            self.db.execute('INSERT INTO blocks(blocker_user_id,blocked_user_id) VALUES (?,?)',(a,b));self.db.commit()
            self.check(SuggestionStatus.STALE);self.check(SuggestionStatus.STALE,actor=2)
            self.db.execute('DELETE FROM blocks');self.db.commit()

    def test_r_tradepool_or_account_gate_lost(self):
        for user in (1,2):
            self.db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=?',(user,));self.db.commit();self.check(SuggestionStatus.STALE)
            self.db.execute('UPDATE user_albums SET trade_pool_enabled=1 WHERE user_id=?',(user,));self.db.commit()
            self.db.execute("UPDATE users SET account_state='deactivated' WHERE id=?",(user,));self.db.commit();self.check(SuggestionStatus.STALE)
            self.db.execute("UPDATE users SET account_state='active' WHERE id=?",(user,));self.db.commit();self.check()

    def test_s_piece_changed_old_identity(self):
        for side in ('side_a_pieces','side_b_pieces'):
            old = getattr(self.suggestion,side)
            self.check(SuggestionStatus.INVALID_PAYLOAD, replace(self.suggestion,**{side:(replace(old[0],sticker_code='changed'),)+old[1:]}))

    def test_t_piece_added_old_identity(self):
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,side_a_pieces=self.suggestion.side_a_pieces+(SmartDealPiece('vfl','extra'),)))

    def test_u_piece_removed_old_identity(self):
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,side_a_pieces=self.suggestion.side_a_pieces[1:]))

    def test_v_manipulated_participant_or_actor(self):
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,participant_b=999))
        for actor in (999,True,'1'):self.check(SuggestionStatus.INVALID_PAYLOAD,actor=actor)

    def test_w_wrong_contract_type(self):
        for kind in ('legacy','smartdeal_v2',None):self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,contract_type=kind))

    def test_x_quantity_manipulation(self):
        for quantity in (2,0,-1,True,1.0,'1'):
            values = self.suggestion.side_a_pieces
            self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,side_a_pieces=(replace(values[0],quantity=quantity),)+values[1:]))

    def test_y_unbalanced_even_with_recomputed_identity(self):
        values = self.suggestion.side_a_pieces+(SmartDealPiece('vfl','extra'),)
        identity = SmartDealIdentityService.from_view(1,2,values,self.suggestion.side_b_pieces)
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,side_a_pieces=values,opportunity_identity=identity))

    def test_z_duplicate_need_representation(self):
        values = self.suggestion.side_a_pieces
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,side_a_pieces=values[:-1]+values[:1]))

    def test_valid_is_not_reserved_next_read_can_be_stale(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest();changes=self.db.total_changes
        self.check()
        self.assertEqual(changes,self.db.total_changes)
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())
        writer=sqlite3.connect(self.path)
        try:
            writer.execute('DELETE FROM stickers WHERE user_id=1 AND album_id=? AND sticker_code=?',self.outgoing[0]);writer.commit()
        finally:writer.close()
        self.check(SuggestionStatus.STALE)

    def test_no_reoptimization_pairwise_or_payload_repair(self):
        before = asdict(self.suggestion)
        with patch.object(SmartDealOptimizer,'optimize',side_effect=AssertionError('reoptimized')), patch.object(SmartDealPairwiseService,'from_planning_inputs',side_effect=AssertionError('pairwise')):
            self.check()
            self.quantity(1,*self.outgoing[0],1);self.db.commit();self.check(SuggestionStatus.STALE)
        self.assertEqual(before,asdict(self.suggestion))

    def test_private_pool_members_remain_eligible(self):
        self.db.execute("UPDATE users SET profile_privacy='private'")
        self.db.execute("UPDATE user_albums SET visibility='private'");self.db.commit();self.check()

    def test_insufficient_supply_not_fixed_by_unused_alternatives(self):
        self.quantity(1,*self.outgoing[0],1)
        self.catalog['vfl'].append('replacement');self.quantity(1,'vfl','replacement',2);self.db.commit()
        self.assertEqual(5,self.plan().deals[0].piece_count)
        self.check(SuggestionStatus.STALE)

    def test_newly_bound_copy_with_spare_supply_still_valid(self):
        user=self.extra_partner();self.quantity(1,*self.outgoing[0],3)
        self.binding(1,user,*self.outgoing[0]);self.check()

    def test_bad_metadata_and_minimum_are_invalid(self):
        for changes in ({'piece_count':True},{'piece_count':6},{'involved_albums':('wrong',)}, {'side_a_pieces':list(self.suggestion.side_a_pieces)}):
            self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,**changes))
        a,b=self.suggestion.side_a_pieces[:4],self.suggestion.side_b_pieces[:4]
        identity=SmartDealIdentityService.from_view(1,2,a,b)
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,side_a_pieces=a,side_b_pieces=b,opportunity_identity=identity,piece_count=4))

    def test_piece_order_irrelevant(self):
        self.check(suggestion=replace(self.suggestion,side_a_pieces=self.suggestion.side_a_pieces[::-1],side_b_pieces=self.suggestion.side_b_pieces[::-1]))

    def test_current_canonical_catalog_required(self):
        self.catalog['vfl'].remove(self.outgoing[0][1]);self.check(SuggestionStatus.STALE)

    def test_invalid_payload_needs_no_database_read(self):
        sql=[];self.db.set_trace_callback(sql.append)
        try:self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,contract_type='legacy'))
        finally:self.db.set_trace_callback(None)
        self.assertEqual([],sql)

    def test_no_mutation_or_caller_transaction_commit(self):
        self.quantity(1,'vfl','irrelevant',2)
        before=self.db.total_changes;self.assertTrue(self.db.in_transaction)
        self.check();self.assertTrue(self.db.in_transaction);self.assertEqual(before,self.db.total_changes)
        self.db.rollback()

    def test_same_read_snapshot_during_concurrent_change(self):
        self.db.execute('PRAGMA journal_mode=WAL');fired=[]
        def trace(sql):
            if sql.startswith('SELECT user_id,album_id,sticker_code,quantity') and not fired:
                fired.append(True)
                writer=sqlite3.connect(self.path)
                try:
                    writer.execute('DELETE FROM stickers WHERE user_id=2 AND album_id=? AND sticker_code=?',self.incoming[0]);writer.commit()
                finally:writer.close()
        self.db.set_trace_callback(trace)
        try:self.check()
        finally:self.db.set_trace_callback(None)
        self.assertTrue(fired);self.check(SuggestionStatus.STALE)

    def test_injected_read_failure_no_writes_or_open_transaction(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest();changes=self.db.total_changes
        with patch.object(SmartDealPlanningService,'_binding_rows',side_effect=RuntimeError('read failure')):
            with self.assertRaises(RuntimeError):self.validator.validate(self.suggestion,1)
        self.assertFalse(self.db.in_transaction);self.assertEqual(changes,self.db.total_changes)
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_full_identity_checked_even_under_digest_collision(self):
        with patch('services.smartdeal_identity.hashlib.sha256') as digest:
            digest.return_value.hexdigest.return_value='0'*64
            original=SmartDealSuggestion.from_deal(1,self.plan().deals[0])
            values=original.side_a_pieces
            tampered=replace(original,side_a_pieces=(replace(values[0],sticker_code='other'),)+values[1:])
            self.check(SuggestionStatus.INVALID_PAYLOAD,tampered)
            self.check(suggestion=original)

    def test_invalid_identity_digest_and_untyped_payload(self):
        identity=replace(self.suggestion.opportunity_identity)
        object.__setattr__(identity,'digest','0'*64)
        self.check(SuggestionStatus.INVALID_PAYLOAD,replace(self.suggestion,opportunity_identity=identity))
        self.assertEqual(SuggestionStatus.INVALID_PAYLOAD,self.validator.validate(asdict(self.suggestion),1).status)

    def test_missing_participants_cannot_validate(self):
        values=self.suggestion
        identity=SmartDealIdentityService.from_view(1,999,values.side_a_pieces,values.side_b_pieces)
        missing=replace(values,participant_b=999,opportunity_identity=identity)
        self.check(SuggestionStatus.STALE,missing)
        self.check(SuggestionStatus.STALE,missing,actor=999)

    def test_query_count_constant_for_five_twenty_five_and_one_fifty(self):
        counts=[]
        for size in (5,25,150):
            self.configure(size,('vfl','em24'));sql=[];self.db.set_trace_callback(sql.append)
            try:self.check()
            finally:self.db.set_trace_callback(None)
            counts.append(len(sql))
        self.assertEqual([counts[0]]*3,counts)
        self.assertLessEqual(counts[0],21)
