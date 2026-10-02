"""Synthetic SD-T3a reproducible workloads; timings are evidence, not acceptance."""
import json
import platform
import random
from time import perf_counter
from tests.research import smartdeal_flow_prototype as flow
from tests.research import smartdeal_oracle as oracle
from tests.test_sd_t3a_optimization import keys, partner, problem, greedy_trap


def run():
    rng = random.Random(31001)
    out = keys('O',15,'em24')+keys('O',15,'vfl')
    inc = keys('I',15,'em24')+keys('I',15,'vfl')
    dense = problem(*(oracle.Partner(p,tuple(rng.sample(out,8)),tuple(rng.sample(inc,8))) for p in range(2,12)))
    workloads = [('greedy-trap',greedy_trap()),('one-150',problem(partner(2,150))),
                 ('20-disjoint-5',problem(*(partner(p) for p in range(2,22)))),
                 ('10-overlapping-8',dense),
                 ('100-identical-5',problem(*(replace_partner(p) for p in range(2,102))))]
    print(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'seed':31001}),flush=True)
    for label,value in workloads:
        stats = {}
        start = perf_counter()
        plan = flow.solve(value,stats)
        record = {'case':label,'partners':len(value.partners),'outgoing_identities':len(value.supply),
                  'incoming_needs':len({k for p in value.partners for k in p.incoming}),
                  'seconds':round(perf_counter()-start,6),'gain':sum(d.size for d in plan),
                  'deals':len(plan),**stats}
        if label == 'greedy-trap':
            start=perf_counter();exact=oracle.solve(value,stats={})
            record['oracle_seconds']=round(perf_counter()-start,6)
            assert exact==plan
        print(json.dumps(record,sort_keys=True),flush=True)


def replace_partner(pid):
    p=partner(2)
    return oracle.Partner(pid,p.outgoing,p.incoming)


if __name__=='__main__':
    run()
