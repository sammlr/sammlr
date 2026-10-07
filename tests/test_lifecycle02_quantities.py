"""Independent quantity oracle for the existing scoped integer flow kernel."""
import itertools,random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'App'))
from services._smartdeal_flow import PartnerEdges,allocate
from services._trade_v2_flow import ScopedSubsetNetwork


class QuantityFlowTests(unittest.TestCase):
    def test_shared_need_and_supply_across_two_suggestions(self):
        out=('a','give');inc=('a','receive')
        partners=tuple(PartnerEdges(p,(out,),(inc,),None,{('out',out):6,('in',inc):6}) for p in (2,3))
        allocations,_=allocate({out:11},partners,{inc:11})
        self.assertEqual([(2,6),(3,5)],[(p.partner_id,len(p.incoming)) for p in allocations])
        self.assertEqual(11,sum(len(p.outgoing) for p in allocations))

    def test_scoped_quantity_kernel_against_exhaustive_oracle(self):
        rng=random.Random(2002);checks=0
        for _ in range(40):
            keys=(('a','x'),('b','y'))
            supply={k:rng.randint(1,3) for k in keys};needs={k:rng.randint(1,3) for k in keys}
            partners=tuple(PartnerEdges(pid,keys,keys,(('a',),('b',)),
                {(d,k):rng.randint(1,2) for d in ('out','in') for k in keys}) for pid in (2,3))
            sizes={p.partner_id:(n,n) for p in partners for n in [rng.randint(0,4)]}
            edges=[(p,d,k) for p in partners for d in ('out','in') for k in keys]
            possible=False
            for values in itertools.product(*(range(p.capacity(d,k)+1) for p,d,k in edges)):
                chosen={(p.partner_id,d,k):n for (p,d,k),n in zip(edges,values)}
                if any(sum(chosen[p.partner_id,d,k] for p in partners)>limit[k] for d,limit in [('out',supply),('in',needs)] for k in keys):continue
                if any(sum(chosen[p.partner_id,d,k] for k in keys)!=sizes[p.partner_id][0] for p in partners for d in ('out','in')):continue
                if any(chosen[p.partner_id,'out',k]!=chosen[p.partner_id,'in',k] for p in partners for k in keys):continue
                possible=True;break
            counters={'flow_checks':0,'cache_hits':0}
            actual=ScopedSubsetNetwork(partners,supply,counters,needs).feasible(sizes,(0,8))
            self.assertEqual(possible,actual);checks+=1
        self.assertEqual(40,checks)
