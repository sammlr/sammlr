"""AC24 direction-independent exact packages, collision safety and no IO."""
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from services.smartdeal_identity import SmartDealIdentityService as Identity
from services.smartdeal_identity import SmartDealIdentityError, SmartDealOpportunityIdentity
from services.smartdeal_optimizer import SmartDealPiece, SmartDealOptimizer
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_pairwise import SmartDealPairwiseService
from tests import test_sd_t3b_optimizer as optimizer
from tests import test_sd_t3a_optimization as graphs
from tests import test_sd_t2a_planning_state as fixtures


def pieces(prefix, size=5, albums=('vfl',)):
    return tuple(SmartDealPiece(albums[i % len(albums)], f'{prefix}{i:03}') for i in range(size))


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.outgoing, self.incoming = pieces('O'), pieces('I')

    def identity(self, user=7, partner=42, outgoing=None, incoming=None):
        return Identity.from_view(user, partner,
            self.outgoing if outgoing is None else outgoing,
            self.incoming if incoming is None else incoming)

    def test_a_five_by_five_stable_full_digest(self):
        value = self.identity()
        self.assertEqual(value, self.identity())
        self.assertEqual(64, len(value.digest))
        self.assertEqual(hashlib.sha256(value.canonical_payload.encode('utf-8')).hexdigest(), value.digest)
        self.assertEqual('smartdeal_v1:sha256:' + value.digest, value.lookup_key)

    def test_b_representative_mirrors(self):
        for size, albums in ((5, ('vfl',)), (28, ('vfl', 'em24', 'wm26')), (150, ('em24', 'vfl'))):
            for a, b in ((7, 42), (42, 7), (2, 10)):
                outgoing, incoming = pieces('O', size, albums), pieces('I', size, albums)
                with self.subTest(size=size, a=a, b=b):
                    first = Identity.from_view(a, b, outgoing, incoming)
                    mirror = Identity.from_view(b, a, incoming[::-1], outgoing[::-1])
                    self.assertEqual(first, mirror)
                    self.assertEqual(first.canonical_payload, mirror.canonical_payload)
                    self.assertEqual(first.lookup_key, mirror.lookup_key)

    def test_c_piece_order_irrelevant(self):
        self.assertEqual(self.identity(), self.identity(outgoing=self.outgoing[::-1], incoming=self.incoming[2:]+self.incoming[:2]))

    def test_d_participants_order_numerical_and_deliveries_preserved(self):
        value = self.identity(user=10, partner=2)
        self.assertEqual((2, 10), (value.low_user_id, value.high_user_id))
        self.assertEqual(tuple((p.album_id, p.sticker_code, 1) for p in self.incoming), value.low_to_high)
        self.assertEqual(value, self.identity(user=2, partner=10, outgoing=self.incoming, incoming=self.outgoing))

    def test_e_multi_album_and_same_code_are_distinct_positions(self):
        outgoing = (SmartDealPiece('vfl', '1'), SmartDealPiece('em24', '1')) + self.outgoing
        value = self.identity(outgoing=outgoing)
        self.assertIn(('em24', '1', 1), value.low_to_high)
        self.assertIn(('vfl', '1', 1), value.low_to_high)
        self.assertEqual(value, self.identity(user=42, partner=7, outgoing=self.incoming, incoming=outgoing))

    def test_f_other_participant_changes_identity(self):
        for user, partner in ((8, 42), (7, 43)):
            self.assertNotEqual(self.identity().lookup_key, self.identity(user, partner).lookup_key)

    def test_g_changed_outgoing_piece(self):
        self.assertNotEqual(self.identity().lookup_key, self.identity(outgoing=(SmartDealPiece('vfl', 'different'),)+self.outgoing[1:]).lookup_key)

    def test_h_changed_incoming_piece(self):
        self.assertNotEqual(self.identity().lookup_key, self.identity(incoming=(SmartDealPiece('vfl', 'different'),)+self.incoming[1:]).lookup_key)

    def test_i_album_is_part_of_identity(self):
        self.assertNotEqual(self.identity().lookup_key, self.identity(outgoing=(replace(self.outgoing[0], album_id='em24'),)+self.outgoing[1:]).lookup_key)

    def test_j_quantity_change_rejected_by_locked_binary_need_contract(self):
        for quantity in (2, 0, -1, True, 1.0, '1'):
            for side in ('outgoing', 'incoming'):
                values = getattr(self, side)
                with self.subTest(quantity=quantity, side=side), self.assertRaises(SmartDealIdentityError):
                    self.identity(**{side: (replace(values[0], quantity=quantity),)+values[1:]})
        self.assertTrue(all(q == 1 for _, _, q in self.identity().low_to_high))

    def test_k_added_piece_changes_identity_without_rebalancing(self):
        for side in ('outgoing', 'incoming'):
            self.assertNotEqual(self.identity().lookup_key, self.identity(**{side:getattr(self, side)+(SmartDealPiece('vfl', 'extra'),)}).lookup_key)

    def test_l_removed_piece_changes_identity_without_rebalancing(self):
        for side in ('outgoing', 'incoming'):
            self.assertNotEqual(self.identity().lookup_key, self.identity(**{side:getattr(self, side)[1:]}).lookup_key)

    def test_m_actual_rank_change_does_not_change_identity(self):
        base = graphs.partner(2, 5)
        first = optimizer.runtime(graphs.problem(base)).deals
        later = optimizer.runtime(graphs.problem(base, graphs.partner(3, 8), graphs.partner(4, 7))).deals
        self.assertEqual(2, first[0].partner_id)
        self.assertEqual(2, later[2].partner_id)
        self.assertEqual(first[0], later[2])
        self.assertEqual(Identity.from_deal(1, first[0]), Identity.from_deal(1, later[2]))

    def test_n_identical_recomputation_no_time_session_or_occurrence(self):
        value = graphs.problem(graphs.partner(2))
        first = Identity.from_deal(1, optimizer.runtime(value).deals[0])
        second = Identity.from_deal(1, optimizer.runtime(value).deals[0])
        self.assertEqual(first, second)
        self.assertEqual({'contract_type','participants','low_to_high','high_to_low'}, set(json.loads(first.canonical_payload)))
        # No process-local registry: a previous occurrence cannot consume identity.
        self.assertEqual(first, Identity.from_deal(1, optimizer.runtime(value).deals[0]))

    def test_o_t3b_adapter_leaves_full_plan_unchanged(self):
        plan = optimizer.runtime(graphs.greedy_trap())
        before = asdict(plan)
        for deal in plan.deals:
            value = Identity.from_deal(1, deal)
            self.assertEqual(value, Identity.from_view(deal.partner_id, 1, deal.incoming_pieces, deal.outgoing_pieces))
            self.assertEqual(deal.piece_count, len(value.low_to_high))
            self.assertEqual(set(deal.involved_albums), {a for a, _, _ in value.low_to_high+value.high_to_low})
        self.assertEqual(before, asdict(plan))

    def test_p_mirrored_confirmation_contents_match_only_exact_package(self):
        # Content equality only, no GO operation, state or persisted request.
        a_content = self.identity()
        b_content = self.identity(user=42, partner=7, outgoing=self.incoming, incoming=self.outgoing)
        other = self.identity(outgoing=self.outgoing[1:])
        self.assertEqual(a_content, b_content)
        self.assertNotEqual(a_content, other)

    def test_simulated_hash_collision_never_equates_different_contracts(self):
        with patch('services.smartdeal_identity.hashlib.sha256') as digest:
            digest.return_value.hexdigest.return_value = '0' * 64
            first = self.identity()
            other = self.identity(outgoing=self.outgoing[1:])
            mirror = self.identity(user=42, partner=7, outgoing=self.incoming, incoming=self.outgoing)
        self.assertEqual(first.lookup_key, other.lookup_key)
        self.assertNotEqual(first, other)
        self.assertNotEqual(first.canonical_payload, other.canonical_payload)
        self.assertEqual(first, mirror)
        self.assertEqual(2, len({first, other, mirror}))

    def test_swapping_deliveries_without_swapping_participants_is_different(self):
        self.assertNotEqual(self.identity(), self.identity(outgoing=self.incoming, incoming=self.outgoing))

    def test_duplicate_lines_cannot_smuggle_multicopy_need(self):
        for side in ('outgoing', 'incoming'):
            values = getattr(self, side)
            with self.assertRaises(SmartDealIdentityError):self.identity(**{side:values+values[:1]})

    def test_invalid_participants_and_noncanonical_text_fail_closed(self):
        for invalid in (True, 7.0, '7', 0, -7, None, 42):
            with self.assertRaises(SmartDealIdentityError):self.identity(user=invalid)
        for piece in (replace(self.outgoing[0], album_id=1), replace(self.outgoing[0], sticker_code=1),
                      replace(self.outgoing[0], sticker_code='\ud800')):
            with self.assertRaises(SmartDealIdentityError):self.identity(outgoing=(piece,))

    def test_unicode_delimiters_and_canonical_order_are_lossless(self):
        values = tuple(SmartDealPiece('ä,"[]', code) for code in ('2','10','A','a','é','e\u0301','\\','\n'))
        first = self.identity(outgoing=values)
        self.assertEqual(sorted(p.sticker_code for p in values), [code for _, code, _ in first.low_to_high])
        decoded = json.loads(first.canonical_payload)
        self.assertEqual([list(p) for p in first.low_to_high], decoded['low_to_high'])
        self.assertNotEqual(self.identity(outgoing=(SmartDealPiece('a|b','c'),)), self.identity(outgoing=(SmartDealPiece('a','b|c'),)))
        self.assertNotEqual(self.identity(outgoing=(SmartDealPiece('a','é'),)), self.identity(outgoing=(SmartDealPiece('a','e\u0301'),)))

    def test_canonical_payload_golden_vector(self):
        value = self.identity(outgoing=(SmartDealPiece('vfl','O'),), incoming=(SmartDealPiece('em24','I'),))
        expected = '{"contract_type":"smartdeal_v1","high_to_low":[["em24","I",1]],"low_to_high":[["vfl","O",1]],"participants":[7,42]}'
        self.assertEqual(expected, value.canonical_payload)

    def test_immutable_snapshot_of_mutable_input(self):
        rows = [['vfl', 'O', 1]]
        value = SmartDealOpportunityIdentity(7, 42, rows, [['vfl','I',1]])
        rows[0][1] = 'changed'
        self.assertEqual((('vfl','O',1),), value.low_to_high)
        with self.assertRaises(FrozenInstanceError):value.low_user_id = 8
        with self.assertRaises(FrozenInstanceError):value.digest = 'forged'

    def test_hash_seed_and_cold_import_without_database_dependencies(self):
        code = '''import sys,json
sys.path.insert(0, 'App')
from services.smartdeal_identity import SmartDealOpportunityIdentity
value=SmartDealOpportunityIdentity(7,42,(('vfl','O',1),),(('em24','I',1),))
assert not any(n in sys.modules for n in ('sqlite3','services.smartdeal_planning','services.smartdeal_optimizer','flask'))
print(json.dumps([value.canonical_payload,value.lookup_key]))
'''
        results = [subprocess.check_output([sys.executable, '-B', '-c', code], cwd=ROOT,
            env={**os.environ, 'PYTHONHASHSEED': seed}, text=True) for seed in ('0','1','731')]
        self.assertEqual(results[0], results[1]);self.assertEqual(results[0], results[2])


class IdentityDatabaseTests(unittest.TestCase):
    setUp = fixtures.PlanningStateTests.setUp
    quantity = fixtures.PlanningStateTests.quantity

    def test_q_r_real_t3b_output_identity_has_no_sql_or_mutation(self):
        catalog = {'vfl': tuple(str(i) for i in range(1,11)), 'em24': ()}
        for i in range(1,6):self.quantity(1,'vfl',str(i),2)
        for i in range(6,11):self.quantity(2,'vfl',str(i),2)
        # Remove original opposite-side seed inventory to make exact 5↔5.
        self.db.execute("DELETE FROM stickers WHERE user_id=2 AND sticker_code='2'")
        self.db.commit()
        planner = SmartDealPlanningService(self.db, lambda a: catalog[a], lambda: fixtures.NOW)
        inputs = planner.build_pairwise_inputs(1)
        plan = SmartDealOptimizer.optimize(inputs.subject, SmartDealPairwiseService.from_planning_inputs(inputs))
        self.assertEqual(5, plan.deals[0].piece_count)
        other_inputs = planner.build_pairwise_inputs(2)
        other_plan = SmartDealOptimizer.optimize(other_inputs.subject,
            SmartDealPairwiseService.from_planning_inputs(other_inputs))
        self.assertEqual(Identity.from_deal(1, plan.deals[0]), Identity.from_deal(2, other_plan.deals[0]))
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        changes = self.db.total_changes
        sql = [];self.db.set_trace_callback(sql.append)
        try:
            with patch('sqlite3.connect', side_effect=AssertionError('Identity opened DB')), \
                 patch.object(SmartDealPlanningService, 'build_pairwise_inputs', side_effect=AssertionError('Replanned')), \
                 patch.object(SmartDealOptimizer, 'optimize', side_effect=AssertionError('Reoptimized')):
                result = Identity.from_deal(1, plan.deals[0])
                self.assertEqual(result, Identity.from_view(2,1,plan.deals[0].incoming_pieces,plan.deals[0].outgoing_pieces))
                with self.assertRaises(SmartDealIdentityError):Identity.from_deal(2, plan.deals[0])
        finally:
            self.db.set_trace_callback(None)
        self.assertEqual([], sql)
        self.assertEqual(changes, self.db.total_changes)
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(self.db.in_transaction)
