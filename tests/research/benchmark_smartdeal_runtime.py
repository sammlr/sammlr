"""SD-T3b synthetic A–F timing gate. No application database or HTTP route."""
from dataclasses import asdict
import json
import platform
import random
from time import perf_counter
from tests import test_sd_t3a_optimization as fixtures
from tests import test_sd_t3b_optimizer as adapters
from tests.research.smartdeal_oracle import Partner, validate_plan
from services.smartdeal_optimizer import SmartDealOptimizer


def workloads():
    rng=random.Random(31001)
    out=fixtures.keys('O',15,'em24')+fixtures.keys('O',15,'vfl')
    inc=fixtures.keys('I',15,'em24')+fixtures.keys('I',15,'vfl')
    dense=fixtures.problem(*(Partner(p,tuple(rng.sample(out,8)),tuple(rng.sample(inc,8))) for p in range(2,12)))
    mixed_rng=random.Random(32001)
    shared_out=fixtures.keys('SO',40,'wm26')
    shared_in=fixtures.keys('SI',40,'em24')
    mixed=fixtures.problem(*(Partner(p,fixtures.keys(f'O{p}',4,'vfl')+tuple(mixed_rng.sample(shared_out,4)),
                                       fixtures.keys(f'I{p}',4,'buli')+tuple(mixed_rng.sample(shared_in,4))) for p in range(2,22)))
    stress_rng=random.Random(33001)
    stress=fixtures.problem(*(Partner(p,tuple(stress_rng.sample(out,8)),tuple(stress_rng.sample(inc,8))) for p in range(2,27)))
    return (
        ('A-small-normal',fixtures.problem(fixtures.partner(2,8),fixtures.partner(3,6))),
        ('B-medium-normal',fixtures.problem(*(fixtures.partner(p,8+p) for p in range(2,7)))),
        ('C-20-disjoint',fixtures.problem(*(fixtures.partner(p,10) for p in range(2,22)))),
        ('D-10-overlapping-T3a',dense),
        ('E-20-mixed',mixed),
        ('F-25-dense-stress',stress),
        ('G-single-150',fixtures.problem(fixtures.partner(2,150))),
    )


def run(repeats=3):
    print(json.dumps({'python':platform.python_version(),'platform':platform.platform(),
                      'seeds':[31001,32001,33001],'repeats':repeats,'timing':'optimizer only; fixture/T2a/T2b construction excluded'}),flush=True)
    for name,value in workloads():
        inputs,opportunities=adapters.snapshot(value)
        previous=None
        for repetition in range(repeats):
            start=perf_counter()
            plan=SmartDealOptimizer.optimize(inputs.subject,opportunities)
            elapsed=perf_counter()-start
            validate_plan(value,adapters.logical(plan))
            if previous is not None:
                assert plan==previous
            previous=plan
            print(json.dumps({'case':name,'repeat':repetition+1,'partners':len(value.partners),
                              'outgoing':len(value.supply),'incoming':len({k for p in value.partners for k in p.incoming}),
                              'gain':plan.objective.total_gain,'deals':len(plan.deals),'seconds':round(elapsed,6),
                              **asdict(plan.diagnostics)},sort_keys=True),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=3)
    run(parser.parse_args().repeats)
