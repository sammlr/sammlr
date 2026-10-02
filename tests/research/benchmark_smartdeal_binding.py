"""Synthetic committed V21 creates; each measurement starts on a fresh fixture."""
import json
import platform
import sqlite3
from statistics import mean
from time import perf_counter

from tests.test_sd_t5a_atomic_binding import AtomicBindingTests
from services.smartdeal_requests import SmartDealRequestCode


def run():
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,
        'platform':platform.platform(),'series':3,'creates_per_series':10,
        'timing':'create including BEGIN IMMEDIATE, revalidation, binding verification and COMMIT; setup excluded'}))
    for size,albums in ((5,('vfl',)),(25,('vfl','em24')),(150,('vfl','em24'))):
        case=AtomicBindingTests('test_a_exact_open_v1_request')
        try:
            case.setUp();case.configure(size,albums);sql=[];case.db.set_trace_callback(sql.append)
            result=case.create();case.db.set_trace_callback(None)
            assert result.code==SmartDealRequestCode.CREATED
            # SQLite trace includes repeated parent statements for triggers.
            count=len(sql)
        finally:case.doCleanups()
        for series in range(1,4):
            samples=[]
            for _ in range(10):
                case=AtomicBindingTests('test_a_exact_open_v1_request')
                try:
                    case.setUp();case.configure(size,albums)
                    start=perf_counter();result=case.create();samples.append((perf_counter()-start)*1000)
                    assert result.code==SmartDealRequestCode.CREATED
                finally:case.doCleanups()
            print(json.dumps({'size_per_side':size,'albums':len(albums),'series':series,
                'sqlite_trace_statements_including_triggers':count,
                'mean_ms':mean(samples),'min_ms':min(samples),'max_ms':max(samples)}),flush=True)


if __name__=='__main__':run()
