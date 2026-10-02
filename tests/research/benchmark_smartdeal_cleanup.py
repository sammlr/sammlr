"""CG-1 lazy cleanup overhead, synthetic fixtures only; setup excluded."""
import json
from datetime import timedelta
from statistics import mean
from time import perf_counter
from tests.research.benchmark_smartdeal_release import fixture
from tests.test_sd_t5b_release_expiry import ReleaseTests, NOW
from services.smartdeal_runtime import cleanup


def run():
    for count in (0,3,30):
        samples=[]
        for _ in range(10):
            if count:
                case,_=fixture(5,count)
            else:
                case=ReleaseTests('test_withdraw_full_cycle');case.setUp()
            try:
                start=perf_counter();result=cleanup(case.db,lambda:NOW+timedelta(days=100))
                samples.append((perf_counter()-start)*1000)
                assert len(result)==count
            finally:case.doCleanups()
        print(json.dumps({'due':count,'runs':10,'mean_ms':mean(samples),'min_ms':min(samples),'max_ms':max(samples)}))

if __name__=='__main__':run()
