"""Synthetic T6a transformation cost; fixture/optimization excluded from timer."""
import json
import platform
from time import perf_counter

from services.smartdeal_identity import SmartDealIdentityService
from tests.test_sd_t3b_optimizer import runtime
from tests.test_sd_t3a_optimization import problem, partner


def run(iterations=1000, repeats=3):
    print(json.dumps({'python': platform.python_version(), 'platform': platform.platform(),
                      'iterations': iterations, 'repeats': repeats,
                      'timing': 'full from_deal canonicalization + JSON + SHA256; no fixture/optimizer/SQL'}))
    for size in (5, 28, 150, 1500):
        deal = runtime(problem(partner(2, size))).deals[0]
        expected = SmartDealIdentityService.from_deal(1, deal)
        for repeat in range(1, repeats + 1):
            start = perf_counter()
            for _ in range(iterations):
                result = SmartDealIdentityService.from_deal(1, deal)
            elapsed = perf_counter() - start
            assert result == expected and result.lookup_key == expected.lookup_key
            print(json.dumps({'size_per_side': size, 'repeat': repeat,
                              'milliseconds_per_identity': elapsed * 1000 / iterations}), flush=True)


if __name__ == '__main__':
    run()
