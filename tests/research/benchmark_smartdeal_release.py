"""Synthetic V21 release and sweep timings; fixture creation is excluded."""
from datetime import timedelta
import json
import platform
import sqlite3
from statistics import mean
from time import perf_counter

from tests.test_sd_t5b_release_expiry import ReleaseTests, NOW
from services.smartdeal_release import ReleaseCode
from services.smartdeal_requests import SmartDealRequestCode


def fixture(size, sweep):
    case = ReleaseTests('test_withdraw_full_cycle')
    case.setUp()
    try:
        if sweep:
            for i in range(sweep):
                package = case.package(str(i),size=size)
                result = case.service(now=NOW+timedelta(days=i//3)).create_from_suggestion(package,1)
                assert result.code == SmartDealRequestCode.CREATED
            action = case.release(now=NOW+timedelta(days=100)).sweep
        else:
            case.configure(size,('vfl',) if size==5 else ('vfl','em24'))
            deal = case.bound()
            action = lambda: case.release(now=NOW+timedelta(hours=1)).withdraw(deal.request_id,1)
        return case, action
    except BaseException:
        case.doCleanups()
        raise


def run():
    print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,
                      'platform':platform.platform(),'timing':'BEGIN through COMMIT; setup excluded'}))
    for size,sweep in ((5,0),(25,0),(150,0),(5,30)):
        for series in range(1,4):
            samples=[];count=None
            for index in range(5 if sweep else 10):
                case,action=fixture(size,sweep)
                try:
                    if index==0:
                        trace=[];case.db.set_trace_callback(trace.append)
                    start=perf_counter();result=action();elapsed=(perf_counter()-start)*1000
                    if index==0:
                        case.db.set_trace_callback(None);count=len(trace)
                    samples.append(elapsed)
                    if sweep:
                        assert len(result)==sweep and all(r.code==ReleaseCode.RELEASED for r in result)
                    else:assert result.code==ReleaseCode.RELEASED
                finally:case.doCleanups()
            print(json.dumps({'size_per_side':size,'sweep_requests':sweep,'series':series,
                              'samples':len(samples),'trace_including_triggers':count,
                              'mean_ms':mean(samples),'min_ms':min(samples),'max_ms':max(samples)}),flush=True)


if __name__=='__main__':run()
