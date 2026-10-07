"""Runtime exact-plan differential gate; T1–T3a artifacts stay unchanged."""
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from services.smartdeal_optimizer import SmartDealOptimizer, SmartDealOptimizationError
from services.smartdeal_planning import (
    PairwisePlanningInputs, PartnerPlanningInventory, PlanningAlbum, PlanningPartner,
    PlanningPiece, PlanningState, SmartDealPlanningService,
)
from services.smartdeal_pairwise import SmartDealPairwiseService
from tests import test_sd_t3a_optimization as t3a
from tests import test_sd_t2a_planning_state as fixtures
from tests.research import smartdeal_oracle as oracle


def snapshot(value):
    """Lossless synthetic oracle graph → canonical T2a inputs → real T2b."""
    all_keys = {k for k, _ in value.supply} | {k for p in value.partners for k in p.incoming}
    albums = tuple(sorted({k[0] for k in all_keys}))
    membership = {(user, album): index + 1 for index, (user, album) in enumerate(
        (user, album) for user in (1, *sorted(p.partner_id for p in value.partners)) for album in albums)}
    supply = tuple(PlanningPiece(*k, membership[(1,k[0])], n) for k,n in value.supply)
    need_keys = sorted({k for p in value.partners for k in p.incoming})
    needs = tuple(PlanningPiece(*k, membership[(1,k[0])], 1) for k in need_keys)
    subject = PlanningState(1, needs, needs, supply, (),
        tuple(PlanningPartner(p.partner_id, albums) for p in value.partners),
        tuple(PlanningAlbum(a, membership[(1,a)], tuple(sorted(k[1] for k in all_keys if k[0]==a))) for a in albums), ())
    partners = tuple(PartnerPlanningInventory(p.partner_id,
        tuple(PlanningPiece(*k, membership[(p.partner_id,k[0])], 1) for k in p.outgoing),
        tuple(PlanningPiece(*k, membership[(p.partner_id,k[0])], 1) for k in p.incoming)) for p in value.partners)
    inputs = PairwisePlanningInputs(subject, partners)
    return inputs, SmartDealPairwiseService.from_planning_inputs(inputs)


def logical(plan):
    return tuple(oracle.Deal(d.partner_id,
        tuple((p.album_id,p.sticker_code) for p in d.incoming_pieces),
        tuple((p.album_id,p.sticker_code) for p in d.outgoing_pieces)) for d in plan.deals)


def runtime(value):
    inputs, opportunities = snapshot(value)
    return SmartDealOptimizer.optimize(inputs.subject, opportunities)


def seeded_problem(seed):
    """0–239 are byte-for-byte equivalent graph generation to locked T3a."""
    rng = random.Random(seed)
    if seed < 200:
        width = 8 if seed < 100 else 12
        out = t3a.keys('O',width//2,'em24')+t3a.keys('O',width//2)
        inc = t3a.keys('I',width//2,'em24')+t3a.keys('I',width//2)
        partners = tuple(oracle.Partner(pid,tuple(rng.sample(out,rng.randint(4,6))),
                                       tuple(rng.sample(inc,rng.randint(4,6)))) for pid in range(2,rng.randint(3,5)))
        value = t3a.problem(*partners)
        return replace(value,supply=tuple((k,rng.randint(1,3)) for k,_ in value.supply))
    partners = []
    ids = (2,3,4) if seed < 240 else (2,10,17)
    for pid in ids:
        p = t3a.partner(pid,4)
        partners.append(replace(p,outgoing=p.outgoing+tuple(rng.sample(t3a.keys('sharedO',4),rng.randint(1,2))),
                               incoming=p.incoming+tuple(rng.sample(t3a.keys('sharedI',4),rng.randint(1,2)))))
    value = t3a.problem(*partners)
    if seed >= 240:
        value = replace(value, supply=tuple((k,rng.randint(1,2)) for k,_ in value.supply))
    return value


class RuntimeOptimizerTests(unittest.TestCase):
    def check(self, value):
        expected = oracle.solve(value)
        actual = runtime(value)
        oracle.validate_plan(value, logical(actual))
        self.assertEqual(expected, logical(actual))
        self.assertEqual(oracle.plan_key(expected), actual.objective.comparison_key)
        return logical(actual)

    # Reuse exact fixtures and assertions, substituting the runtime oracle gate.
    test_a_single_partner = t3a.OptimizationProofTests.test_a_single_partner
    test_b_two_disjoint_partners = t3a.OptimizationProofTests.test_b_two_disjoint_partners
    test_c_shared_outgoing = t3a.OptimizationProofTests.test_c_shared_outgoing
    test_d_shared_incoming = t3a.OptimizationProofTests.test_d_shared_incoming
    test_e_largest_first_is_strictly_suboptimal = t3a.OptimizationProofTests.test_e_largest_first_is_strictly_suboptimal
    test_f_two_smaller_deals_win = t3a.OptimizationProofTests.test_f_two_smaller_deals_win
    test_g_chained_three_partners = t3a.OptimizationProofTests.test_g_chained_three_partners
    test_h_more_than_five_global_selection = t3a.OptimizationProofTests.test_h_more_than_five_global_selection
    test_i_four_not_top = t3a.OptimizationProofTests.test_i_four_not_top
    test_j_five_is_top = t3a.OptimizationProofTests.test_j_five_is_top
    test_k_multi_album_merge = t3a.OptimizationProofTests.test_k_multi_album_merge
    test_l_numeric_partner_tie = t3a.OptimizationProofTests.test_l_numeric_partner_tie
    test_m_shipping_changes_competing_plan_choice = t3a.OptimizationProofTests.test_m_shipping_changes_competing_plan_choice
    test_n_canonical_positions_and_permutations = t3a.OptimizationProofTests.test_n_canonical_positions_and_permutations
    test_p_large_incoming_limited_by_outgoing = t3a.OptimizationProofTests.test_p_large_incoming_limited_by_outgoing
    test_q_large_outgoing_limited_by_incoming = t3a.OptimizationProofTests.test_q_large_outgoing_limited_by_incoming
    test_global_size_vector_and_partner_assignment = t3a.OptimizationProofTests.test_global_size_vector_and_partner_assignment
    test_three_free_copies_fill_three_distinct_partner_needs = t3a.OptimizationProofTests.test_three_free_copies_fill_three_distinct_partner_needs

    def test_differential_500_exact_seeds_and_permutations(self):
        for seed in range(500):
            value = seeded_problem(seed)
            with self.subTest(seed=seed):
                expected = self.check(value)
                inputs, opportunities = snapshot(value)
                reordered = replace(inputs.subject,needs=inputs.subject.needs[::-1],missing=inputs.subject.missing[::-1],
                    outgoing_supply=inputs.subject.outgoing_supply[::-1],eligible_partners=inputs.subject.eligible_partners[::-1],
                    album_context=tuple(replace(a,catalog_codes=a.catalog_codes[::-1]) for a in inputs.subject.album_context[::-1]))
                reversed_opps = tuple(replace(p,outgoing_candidates=p.outgoing_candidates[::-1],
                    incoming_candidates=p.incoming_candidates[::-1],involved_albums=p.involved_albums[::-1]) for p in opportunities[::-1])
                self.assertEqual(expected,logical(SmartDealOptimizer.optimize(reordered,reversed_opps)))
                self.assertEqual(runtime(value),SmartDealOptimizer.optimize(reordered,reversed_opps))

    def test_six_shipping_boundaries_from_runtime_objectives(self):
        # The six accepted T3a boundaries compare alternatives, not fictitious
        # complete global fixtures. Both objectives are now produced by runtime.
        for low_sizes, high_sizes in (((20,),(11,5,5,5)),((18,17),(11,10,10,5,5))):
            low = runtime(t3a.problem(*(t3a.partner(2+i,n) for i,n in enumerate(low_sizes))))
            for delta,wins in ((-1,False),(0,True),(1,True)):
                sizes=(high_sizes[0]+delta,)+high_sizes[1:]
                high=runtime(t3a.problem(*(t3a.partner(2+i,n) for i,n in enumerate(sizes))))
                with self.subTest(low=low_sizes,delta=delta):
                    self.assertEqual(wins,high.objective.comparison_key<low.objective.comparison_key)
                    self.assertEqual(oracle.plan_key(logical(high)),high.objective.comparison_key)
                    self.assertEqual(oracle.plan_key(logical(low)),low.objective.comparison_key)

    def test_shipping_thresholds_in_actual_competing_global_inputs(self):
        for size,expected in ((9,((2,9),)),(8,((2,5),(3,5))),(7,((2,5),(3,5)))):
            b=t3a.partner(3)
            a=oracle.Partner(2,b.outgoing[:size-5]+t3a.keys('OA',5),b.incoming[:size-5]+t3a.keys('IA',5))
            with self.subTest(size=size):
                self.assertEqual(expected,tuple((d.partner_id,d.size) for d in self.check(t3a.problem(a,b))))

    def test_empty_and_unilateral_and_small_opportunities(self):
        for value in (t3a.problem(),t3a.problem(t3a.partner(2,4)),
                      t3a.problem(replace(t3a.partner(2),incoming=()))):
            plan=runtime(value)
            self.assertEqual((),plan.deals)
            self.assertEqual((0,0,0),(plan.objective.total_gain,plan.objective.trade_count,plan.objective.efficiency))
            self.assertEqual(oracle.solve(value),logical(plan))

    def test_large_28_multi_album_and_150_without_maximum(self):
        p=oracle.Partner(2,t3a.keys('O',17,'wm26')+t3a.keys('O',8,'buli')+t3a.keys('O',3,'em24'),
                         t3a.keys('I',9,'wm26')+t3a.keys('I',11,'em04')+t3a.keys('I',8,'buli'))
        plan=runtime(t3a.problem(p))
        self.assertEqual(28,plan.deals[0].piece_count)
        self.assertEqual(('buli','em04','em24','wm26'),plan.deals[0].involved_albums)
        plan=runtime(t3a.problem(t3a.partner(2,150)))
        self.assertEqual(150,plan.deals[0].piece_count)
        self.assertTrue(all(p.quantity==1 for d in plan.deals for side in (d.incoming_pieces,d.outgoing_pieces) for p in side))

    def test_immutable_complete_output_and_unchanged_inputs(self):
        inputs,opps=snapshot(t3a.greedy_trap())
        before=repr((inputs,opps))
        plan=SmartDealOptimizer.optimize(inputs.subject,opps)
        self.assertEqual(before,repr((inputs,opps)))
        for value,field,new in ((plan,'deals',()),(plan.objective,'total_gain',99),
                                (plan.deals[0],'piece_count',99),(plan.deals[0].incoming_pieces[0],'quantity',99),
                                (plan.diagnostics,'subsets',99)):
            with self.assertRaises(FrozenInstanceError):setattr(value,field,new)
        self.assertEqual(plan,SmartDealOptimizer.optimize(inputs.subject,opps))

    def test_malformed_inputs_fail_closed_without_fallback(self):
        inputs,opps=snapshot(t3a.problem(t3a.partner(2)))
        state=inputs.subject;p=opps[0];c=p.outgoing_candidates[0]
        bad_opps=((p,p),(replace(p,partner_id=99),),(replace(p,max_equal_piece_count=4),),
                  (replace(p,outgoing_candidates=p.outgoing_candidates+(c,)),),
                  (replace(p,outgoing_candidates=(replace(c,available_quantity=2),)+p.outgoing_candidates[1:]),),
                  (replace(p,outgoing_candidates=(replace(c,quantity=2),)+p.outgoing_candidates[1:]),),
                  (replace(p,involved_albums=('unknown',)),))
        for invalid in bad_opps:
            with self.assertRaises(SmartDealOptimizationError):SmartDealOptimizer.optimize(state,invalid)
        for invalid in (replace(state,outgoing_supply=()),replace(state,eligible_partners=()),
                        replace(state,needs=()),replace(state,outgoing_supply=state.outgoing_supply*2)):
            with self.assertRaises(SmartDealOptimizationError):SmartDealOptimizer.optimize(invalid,opps)
        with patch('services.smartdeal_optimizer.allocate',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):SmartDealOptimizer.optimize(state,opps)

    def test_deterministic_across_python_hash_seeds(self):
        code='''import json
from dataclasses import asdict
from tests.test_sd_t3b_optimizer import runtime, seeded_problem
print(json.dumps(asdict(runtime(seeded_problem(210))),sort_keys=True))
'''
        results=[subprocess.check_output([sys.executable,'-B','-c',code],cwd=ROOT,
                 env={**os.environ,'PYTHONHASHSEED':seed},text=True) for seed in ('0','1','731')]
        self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

    def test_runtime_never_imports_research_code(self):
        code='''import sys
sys.path.insert(0,'App')
import services.smartdeal_optimizer
assert not any(n.startswith('tests') for n in sys.modules)
'''
        subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,check=True)


class RuntimeSnapshotTests(unittest.TestCase):
    setUp=fixtures.PlanningStateTests.setUp
    quantity=fixtures.PlanningStateTests.quantity
    bind=fixtures.PlanningStateTests.bind

    def test_o_real_t2a_binding_exclusion_zero_sql_and_zero_writes(self):
        catalog={'vfl':tuple(str(i) for i in range(1,13)),'em24':()}
        for i in range(1,7):self.quantity(1,'vfl',str(i),2)
        for i in range(7,13):self.quantity(2,'vfl',str(i),2)
        self.db.execute("DELETE FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='2'")
        self.quantity(2,'vfl','2',2)
        planner=SmartDealPlanningService(self.db,lambda a:catalog[a],lambda:fixtures.NOW)
        before=planner.build_pairwise_inputs(1)
        old=SmartDealPairwiseService.from_planning_inputs(before)
        self.assertEqual(5,SmartDealOptimizer.optimize(before.subject,old).objective.total_gain)
        self.bind();self.db.commit()
        current=planner.build_pairwise_inputs(1)
        opps=SmartDealPairwiseService.from_planning_inputs(current)
        digest=hashlib.sha256(self.path.read_bytes()).hexdigest();changes=self.db.total_changes
        statements=[];self.db.set_trace_callback(statements.append)
        plan=SmartDealOptimizer.optimize(current.subject,opps)
        self.assertEqual((),plan.deals)
        self.assertEqual(oracle.solve(oracle.from_snapshot(current,opps)),logical(plan))
        with self.assertRaises(SmartDealOptimizationError):SmartDealOptimizer.optimize(current.subject,old)
        with patch('services.smartdeal_optimizer.allocate',side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError):SmartDealOptimizer.optimize(current.subject,opps)
        self.db.set_trace_callback(None)
        self.assertEqual([],statements);self.assertEqual(changes,self.db.total_changes)
        self.assertEqual(digest,hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(self.db.in_transaction)


class BranchOrderAcceptanceTests(unittest.TestCase):
    def test_complete_plan_independent_of_ideal_probe_and_reverse_traversal(self):
        from itertools import combinations
        from services import _smartdeal_flow as engine
        from tests.research.benchmark_smartdeal_runtime import workloads

        def original(partners, supply, upper, needs):
            for count in range(1, min(5, len(partners), upper // 5) + 1):
                for subset in combinations(partners, count):
                    yield count, subset

        def reverse(partners, supply, upper, needs):
            for count in range(min(5, len(partners), upper // 5), 0, -1):
                for subset in combinations(tuple(reversed(partners)), count):
                    # Subset identity stays canonical; only traversal reverses.
                    yield count, tuple(sorted(subset, key=lambda p: p.partner_id))

        values = [seeded_problem(seed) for seed in range(30)]
        values.append(dict(workloads())['E-20-mixed'])
        for value in values:
            expected = runtime(value)
            for traversal in (original, reverse):
                with patch.object(engine, '_search_subsets', traversal):
                    actual = runtime(value)
                self.assertEqual(expected.deals, actual.deals)
                self.assertEqual(expected.objective, actual.objective)
