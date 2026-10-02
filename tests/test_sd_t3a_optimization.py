"""SD-T3a A–Q adversarial classes and reproducible independent differential proof."""
from dataclasses import replace
import random
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from tests.research import smartdeal_oracle as oracle
from tests.research import smartdeal_flow_prototype as flow
from tests import test_sd_t2a_planning_state as fixtures
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_pairwise import SmartDealPairwiseService


def keys(prefix, count, album='vfl'):
    return tuple((album, f'{prefix}{i:03}') for i in range(count))


def partner(pid, size=5):
    return oracle.Partner(pid, keys(f'O{pid}-', size), keys(f'I{pid}-', size))


def problem(*partners, copies=1):
    return oracle.Problem(tuple((k, copies) for k in sorted({k for p in partners for k in p.outgoing})), tuple(partners))


def greedy_trap():
    b, c = partner(3), partner(4)
    a = oracle.Partner(2, b.outgoing + c.outgoing[:1], c.incoming + b.incoming[:1])
    return problem(a, b, c)


def naive_greedy(value):
    supply = dict(value.supply)
    received = set()
    result = []
    for p in sorted(value.partners, key=lambda p: (-min(len(p.incoming), len(p.outgoing)), p.partner_id)):
        out = sorted(k for k in p.outgoing if supply[k])
        inc = sorted(set(p.incoming) - received)
        size = min(len(out), len(inc))
        if size < 5 or len(result) == 5:
            continue
        for k in out[:size]:
            supply[k] -= 1
        received.update(inc[:size])
        result.append(oracle.Deal(p.partner_id, tuple(inc[:size]), tuple(out[:size])))
    return oracle.canonical(result)


def metric_plan(sizes, first_id=2):
    return oracle.canonical(tuple(oracle.Deal(p.partner_id, p.incoming, p.outgoing)
                                  for p in (partner(first_id+i, n) for i,n in enumerate(sizes))))


class OptimizationProofTests(unittest.TestCase):
    def check(self, value):
        return oracle.differential(value, flow.solve)

    def test_a_single_partner(self):
        result = self.check(problem(partner(2)))
        self.assertEqual((5,), tuple(d.size for d in result))

    def test_b_two_disjoint_partners(self):
        self.assertEqual(10, sum(d.size for d in self.check(problem(partner(2), partner(3)))))

    def test_c_shared_outgoing(self):
        a,b = partner(2),partner(3)
        b = replace(b, outgoing=a.outgoing[:1]+b.outgoing[1:])
        self.assertEqual([2], [d.partner_id for d in self.check(problem(a,b))])
        self.assertEqual(2, len(self.check(problem(a,b,copies=2))))

    def test_d_shared_incoming(self):
        a,b = partner(2),partner(3)
        b = replace(b, incoming=a.incoming[:1]+b.incoming[1:])
        self.assertEqual([2], [d.partner_id for d in self.check(problem(a,b,copies=3))])

    def test_e_largest_first_is_strictly_suboptimal(self):
        value = greedy_trap()
        best = self.check(value)
        greedy = naive_greedy(value)
        self.assertEqual((6,1), (sum(d.size for d in greedy),len(greedy)))
        self.assertEqual((10,2), (sum(d.size for d in best),len(best)))
        self.assertLess(oracle.plan_key(best), oracle.plan_key(greedy))

    def test_f_two_smaller_deals_win(self):
        self.assertEqual([(3,5),(4,5)], [(d.partner_id,d.size) for d in self.check(greedy_trap())])

    def test_g_chained_three_partners(self):
        a,b,c = partner(2),partner(3),partner(4)
        b = replace(b, outgoing=a.outgoing[:1]+b.outgoing[1:])
        c = replace(c, incoming=b.incoming[:1]+c.incoming[1:])
        self.assertEqual([2,4], [d.partner_id for d in self.check(problem(a,b,c))])

    def test_h_more_than_five_global_selection(self):
        value = problem(*(partner(p) for p in range(2,9)))
        self.assertEqual([2,3,4,5,6], [d.partner_id for d in self.check(value)])
        # Global winner must include a partner beyond the five largest isolated.
        trap = greedy_trap()
        value = problem(*trap.partners, partner(5), partner(6), partner(7))
        self.assertEqual({3,4,5,6,7}, {d.partner_id for d in self.check(value)})

    def test_i_four_not_top(self):
        self.assertEqual((),self.check(problem(partner(2,4))))

    def test_j_five_is_top(self):
        self.assertEqual(5,self.check(problem(partner(2,5)))[0].size)

    def test_k_multi_album_merge(self):
        a = oracle.Partner(2,keys('O',3,'em24')+keys('O',3,'vfl'),keys('I',3,'em24')+keys('I',3,'vfl'))
        result = self.check(problem(a))
        self.assertEqual([6],[d.size for d in result])
        for album in ('em24','vfl'):
            self.assertEqual((),self.check(problem(replace(a,outgoing=tuple(k for k in a.outgoing if k[0]==album),
                                                         incoming=tuple(k for k in a.incoming if k[0]==album)))))

    def test_l_numeric_partner_tie(self):
        a = partner(10)
        b = replace(a,partner_id=2)
        self.assertEqual([2],[d.partner_id for d in self.check(problem(a,b))])

    def test_m_shipping_changes_competing_plan_choice(self):
        # A9 alone: E7. B5 leaves A5, so A5+B5: G10 but E6.
        b = partner(3)
        a = oracle.Partner(2,b.outgoing[:4]+keys('OA',5),b.incoming[:4]+keys('IA',5))
        value = problem(a,b)
        result = self.check(value)
        self.assertEqual([(2,9)],[(d.partner_id,d.size) for d in result])
        alternative = (oracle.Deal(2,keys('IA',5),keys('OA',5)),
                       oracle.Deal(3,b.incoming,b.outgoing))
        oracle.validate_plan(value,alternative)
        self.assertGreater(sum(d.size for d in alternative),sum(d.size for d in result))
        self.assertLess(oracle.plan_key(result),oracle.plan_key(alternative))
        low = metric_plan((10,))
        high = metric_plan((6,5))
        self.assertLess(oracle.plan_key(low),oracle.plan_key(high))

    def test_n_canonical_positions_and_permutations(self):
        a = oracle.Partner(2,keys('O',5), (('a','2'),('a','10'),('a','1'),('a','A'),('a','a'),('a','ä')))
        expected = self.check(problem(a))
        self.assertEqual(tuple(sorted(a.incoming))[:5],expected[0].incoming)
        self.assertEqual(expected,self.check(problem(replace(a,outgoing=a.outgoing[::-1],incoming=a.incoming[::-1]))))

    def test_p_large_incoming_limited_by_outgoing(self):
        a = replace(partner(2),incoming=keys('I',10))
        result = self.check(problem(a))
        self.assertEqual(5,result[0].size)
        self.assertEqual(keys('I',5),result[0].incoming)

    def test_q_large_outgoing_limited_by_incoming(self):
        a = replace(partner(2),outgoing=keys('O',10))
        result = self.check(problem(a))
        self.assertEqual(5,result[0].size)
        self.assertEqual(keys('O',5),result[0].outgoing)

    def test_shipping_boundaries_and_contract_cases_four_six(self):
        for low_sizes, high_sizes in (((20,),(11,5,5,5)),((18,17),(11,10,10,5,5))):
            low = metric_plan(low_sizes)
            for delta, high_wins in ((-1,False),(0,True),(1,True)):
                sizes = (high_sizes[0]+delta,)+high_sizes[1:]
                high = metric_plan(sizes)
                with self.subTest(low=low_sizes,delta=delta):
                    # Both alternatives feasible on one synthetic domain.
                    value = problem(*(oracle.Partner(d.partner_id,tuple(sorted(set(d.outgoing)|set(h.outgoing))),
                                                     tuple(sorted(set(d.incoming)|set(h.incoming))))
                                      for d,h in zip(low,high)),
                                    *(oracle.Partner(d.partner_id,d.outgoing,d.incoming) for d in high[len(low):]))
                    oracle.validate_plan(value,low);oracle.validate_plan(value,high)
                    self.assertEqual(high_wins,oracle.plan_key(high)<oracle.plan_key(low))

    def test_size_vector_before_ids_and_ids_in_output_order(self):
        self.assertLess(oracle.plan_key(metric_plan((18,12),10)),oracle.plan_key(metric_plan((15,15),2)))
        a = metric_plan((5,6),2)
        self.assertEqual((3,2),oracle.plan_key(a)[3])
        self.assertLess(oracle.plan_key(metric_plan((6,5),2)),oracle.plan_key(a))

    def test_comparator_total_order_transitivity(self):
        plans = [metric_plan(s,p) for s in ((),(5,),(6,),(5,5),(6,5),(7,5)) for p in (2,10)]
        ordered = sorted(plans,key=oracle.plan_key)
        for a in ordered:
            for b in ordered:
                self.assertEqual(oracle.plan_key(a)==oracle.plan_key(b),oracle.canonical(a)==oracle.canonical(b))
        for a,b,c in zip(ordered,ordered[1:],ordered[2:]):
            self.assertLessEqual(oracle.plan_key(a),oracle.plan_key(b))
            self.assertLessEqual(oracle.plan_key(a),oracle.plan_key(c))

    def test_global_size_vector_and_partner_assignment(self):
        a,b=partner(10,7),partner(2,7)
        b=replace(b,outgoing=a.outgoing[:2]+b.outgoing[2:])
        result=self.check(problem(a,b))
        self.assertEqual([(2,7),(10,5)],[(d.partner_id,d.size) for d in result])

    def test_three_free_copies_fill_three_distinct_partner_needs(self):
        shared=keys('shared',1)
        partners=tuple(replace(partner(p),outgoing=shared+partner(p).outgoing[1:]) for p in (2,3,4))
        value=problem(*partners)
        value=replace(value,supply=tuple((k,3 if k in shared else n) for k,n in value.supply))
        result=self.check(value)
        self.assertEqual([5,5,5],[d.size for d in result])
        self.assertTrue(all(d.outgoing.count(shared[0])==1 for d in result))

    def test_structured_randomized_differential_40_seeds(self):
        for seed in range(200,240):
            rng=random.Random(seed)
            partners=[]
            for pid in (2,3,4):
                p=partner(pid,4)
                partners.append(replace(p,outgoing=p.outgoing+tuple(rng.sample(keys('sharedO',4),rng.randint(1,2))),
                                       incoming=p.incoming+tuple(rng.sample(keys('sharedI',4),rng.randint(1,2)))))
            with self.subTest(seed=seed):self.check(problem(*partners))

    def test_invalid_plans_rejected(self):
        a,b = partner(2),partner(3)
        b = replace(b,outgoing=a.outgoing[:1]+b.outgoing[1:],incoming=a.incoming[:1]+b.incoming[1:])
        value = problem(a,b)
        da,db = oracle.Deal(2,a.incoming,a.outgoing),oracle.Deal(3,b.incoming,b.outgoing)
        for plan in ((da,db),(da,da),(replace(da,incoming=da.incoming[:4]),),
                     (replace(da,partner_id=99),),(replace(da,outgoing=da.outgoing[:-1]+da.outgoing[:1]),)):
            with self.assertRaises(ValueError):oracle.validate_plan(value,plan)

    def test_limit_never_returns_approximation(self):
        with self.assertRaises(oracle.OracleLimit):oracle.solve(greedy_trap(),max_states=1)

    def test_no_artificial_large_deal_maximum(self):
        value = problem(partner(2,150))
        # Exhaustive oracle deliberately unsuitable here; known analytical optimum.
        result = flow.solve(value)
        self.assertEqual((150,1),(sum(d.size for d in result),len(result)))
        oracle.validate_plan(value,result)

    def test_randomized_differential_200_seeds(self):
        for seed in range(200):
            rng = random.Random(seed)
            width = 8 if seed < 100 else 12
            out,inc = keys('O',width//2,'em24')+keys('O',width//2),keys('I',width//2,'em24')+keys('I',width//2)
            partners = tuple(oracle.Partner(pid,tuple(rng.sample(out,rng.randint(4,6))),
                                           tuple(rng.sample(inc,rng.randint(4,6)))) for pid in range(2,rng.randint(3,5)))
            value = problem(*partners)
            value = replace(value,supply=tuple((k,rng.randint(1,3)) for k,_ in value.supply))
            with self.subTest(seed=seed):
                expected=self.check(value)
                shuffled=replace(value,supply=value.supply[::-1],partners=tuple(replace(p,outgoing=p.outgoing[::-1],incoming=p.incoming[::-1]) for p in value.partners[::-1]))
                self.assertEqual(expected,flow.solve(shuffled))
                self.assertEqual(expected,oracle.solve(shuffled))


class SnapshotProtectionTests(unittest.TestCase):
    setUp=fixtures.PlanningStateTests.setUp
    quantity=fixtures.PlanningStateTests.quantity
    bind=fixtures.PlanningStateTests.bind

    def test_o_bound_supply_and_need_do_not_enter_oracle(self):
        catalog={'vfl':tuple(str(i) for i in range(1,13)),'em24':()}
        for i in range(1,7):self.quantity(1,'vfl',str(i),2)
        for i in range(7,13):self.quantity(2,'vfl',str(i),2)
        # Existing fixture binds outgoing1/incoming2; make that incoming physically missing.
        self.db.execute("DELETE FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='2'")
        self.quantity(2,'vfl','2',2)
        planner=SmartDealPlanningService(self.db,lambda a:catalog[a],lambda:fixtures.NOW)
        before=planner.build_pairwise_inputs(1)
        old=SmartDealPairwiseService.from_planning_inputs(before)
        self.bind()
        current=planner.build_pairwise_inputs(1)
        opps=SmartDealPairwiseService.from_planning_inputs(current)
        value=oracle.from_snapshot(current,opps)
        self.assertNotIn(('vfl','1'),dict(value.supply))
        self.assertTrue(all(('vfl','2') not in p.incoming for p in value.partners))
        self.assertEqual((),oracle.differential(value,flow.solve))
        with self.assertRaises(ValueError):oracle.from_snapshot(current,old)
