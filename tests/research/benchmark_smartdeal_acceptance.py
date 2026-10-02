"""Synthetic V21 acceptance timings; setup and T5a binding are excluded."""
import json
import platform
import sqlite3
from statistics import mean
from time import perf_counter

from tests.test_sd_t6b_accept_mutual_go import AcceptTests, Code


def fixture(mode,size):
    case=AcceptTests('test_explicit_accept_and_exact_mutation_set');case.setUp()
    try:
        case.configure(size,('vfl',) if size==5 else ('vfl','em24'))
        if mode=='lookup6':
            packages=[case.package(str(i)) for i in range(6)]
            for i,p in enumerate(packages):assert case.go(1 if i<3 else 2,p).code==Code.CREATED
            action=lambda:case.core()._transaction(lambda now:case.core()._lookup(packages[-1].opportunity_identity))
        else:
            deal=case.bound()
            action=(lambda:case.core().accept(deal.request_id,2)) if mode=='accept' else (lambda:case.go(2))
        return case,action
    except BaseException:
        case.doCleanups();raise


def run():
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'platform':platform.platform(),
                      'timing':'BEGIN through COMMIT; fixture/binding excluded','series':3,'samples_per_series':10}))
    for mode,size in (('accept',5),('mutual',5),('mutual',25),('mutual',150),('lookup6',5)):
        for series in range(1,4):
            samples=[]
            for i in range(10):
                case,action=fixture(mode,size)
                try:
                    if i==0:
                        trace=[];case.db.set_trace_callback(trace.append)
                    start=perf_counter();result=action();samples.append((perf_counter()-start)*1000)
                    if i==0:case.db.set_trace_callback(None)
                    if mode=='lookup6':assert result['id']>0
                    else:assert result.code==Code.ACCEPTED
                finally:case.doCleanups()
            print(json.dumps({'mode':mode,'size_per_side':size,'series':series,'trace_including_triggers':len(trace),
                              'mean_ms':mean(samples),'min_ms':min(samples),'max_ms':max(samples)}),flush=True)


if __name__=='__main__':run()
