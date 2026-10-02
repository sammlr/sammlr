"""Research-only instrumentation; never change the runtime for measurements."""
import ast
from collections import Counter
from dataclasses import asdict
import inspect
import json
from time import perf_counter
from unittest.mock import patch

from services import _smartdeal_flow as engine
from services.smartdeal_optimizer import _inputs
from tests.research.benchmark_smartdeal_runtime import workloads
from tests.test_sd_t3b_optimizer import snapshot


def investigate(value):
    inputs, opps = snapshot(value)
    supply, partners = _inputs(inputs.subject, opps)
    reasons = Counter()
    phases = {p: {'calls':0,'hits':0,'misses':0,'seconds':0.0} for p in ('EG','DJ','C')}
    states = set()
    prescan = Counter()
    bounds = Counter()
    finishes = Counter()

    def probe(scope):
        if 'upper' not in scope:
            return
        count = scope['count']
        if scope['upper'] < 5 * count:
            reasons['minimum_capacity'] += 1
        elif scope.get('optimistic', ()) >= scope['winner_key']:
            for index, label in enumerate(('E','G','D','J')):
                if scope['optimistic'][index] != scope['winner_key'][index]:
                    reasons['bound_' + label] += 1
                    break
            else:
                reasons['bound_equal_EGDJ'] += 1
        elif 'gain' in scope and (-(scope['gain']-2*count),-scope['gain']) > scope['winner_key'][:2]:
            reasons['after_gain_EG'] += 1
        else:
            reasons['infeasible_subset'] += 1

    class ContinueProbe(ast.NodeTransformer):
        def visit_Continue(self, node):
            return [ast.Expr(ast.Call(ast.Name('_probe',ast.Load()),
                                     [ast.Call(ast.Name('locals',ast.Load()),[],[])],[])),node]
    source = ast.parse(inspect.getsource(engine.allocate))
    source = ContinueProbe().visit(source)
    ast.fix_missing_locations(source)
    namespace = {**engine.__dict__, '_probe':probe}
    # C's forced-zero continue is not a subset prune; probe checks scope below.
    original_probe = probe
    namespace['_probe'] = lambda scope: original_probe(scope) if 'fixed' not in scope else None

    class Network(engine._SubsetNetwork):
        def __init__(self, subset, supply, counters):
            super().__init__(subset, supply, counters)
            self.ids = tuple(p.partner_id for p in subset)
            upper = min(sum(min(len(p.outgoing),len(p.incoming)) for p in subset),
                        sum(supply[k] for k in {k for p in subset for k in p.outgoing}),
                        len({k for p in subset for k in p.incoming}))
            bounds[(len(subset),upper)] += 1

        def feasible(self, sizes, total_bounds, fixed=None):
            caller = inspect.currentframe().f_back.f_code
            phase = 'C' if fixed is not None else ('DJ' if caller.co_name == '<lambda>' and 'd' in caller.co_varnames else 'EG')
            key=(tuple(sizes[p.partner_id] for p in self.subset),total_bounds)
            hit=fixed is None and key in self.cache
            phases[phase]['calls'] += 1
            phases[phase]['hits' if hit else 'misses'] += 1
            states.add((self.ids,key,tuple(sorted(fixed.items())) if fixed is not None else None))
            start=perf_counter()
            result=super().feasible(sizes,total_bounds,fixed)
            phases[phase]['seconds'] += perf_counter()-start
            if phase=='EG' and total_bounds[0]==0:
                finishes['initial_feasible' if result else 'initial_infeasible'] += 1
            return result
    if hasattr(engine, '_search_subsets'):
        helper = inspect.getsource(engine._search_subsets).replace(
            'for subset in combinations(partners, count):',
            "for subset in combinations(partners, count):\n                _prescan['subsets'] += 1", 1)
        namespace['_prescan'] = prescan
        exec(compile(helper, '<research-prescan>', 'exec'), namespace)
    namespace['_SubsetNetwork']=Network
    exec(compile(source,'<research-instrumented-allocate>','exec'),namespace)
    start=perf_counter();plan,counters=namespace['allocate'](supply,partners);elapsed=perf_counter()-start
    reference,_=engine.allocate(supply,partners)
    assert plan==reference

    graph={p.partner_id:set() for p in partners}
    for p in partners:
        for q in partners:
            if p.partner_id<q.partner_id and (set(p.outgoing)&set(q.outgoing) or set(p.incoming)&set(q.incoming)):
                graph[p.partner_id].add(q.partner_id);graph[q.partner_id].add(p.partner_id)
    unseen=set(graph);components=[]
    while unseen:
        start=min(unseen);stack=[start];component=set()
        while stack:
            node=stack.pop()
            if node in component:continue
            component.add(node);stack.extend(graph[node]-component)
        unseen-=component;components.append(len(component))
    equivalent=Counter((p.outgoing,p.incoming) for p in partners)
    return {'prescan':dict(prescan),'counters':counters,'instrumented_seconds':elapsed,'phases':phases,'pruning':dict(reasons),
            'unique_feasibility_states':len(states),'survivor_upper_bounds':{str(k):v for k,v in sorted(bounds.items())},
            'initial_feasibility':dict(finishes),'overlap_edges':sum(map(len,graph.values()))//2,
            'components':components,'duplicate_candidate_signatures':sum(n-1 for n in equivalent.values())}


if __name__=='__main__':
    for name,value in workloads():
        if name[0] in 'CDEF':
            print(json.dumps({'case':name,**investigate(value)},sort_keys=True),flush=True)
