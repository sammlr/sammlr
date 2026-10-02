"""Fresh SQLite→T2a→exact revalidation; synthetic fixtures, no production DB."""
import json
import platform
from time import perf_counter

from tests.test_sd_t4_suggestions import SuggestionTests
from services.smartdeal_suggestions import SuggestionStatus


def run():
    print(json.dumps({'python':platform.python_version(),'platform':platform.platform(),
                      'iterations':100,'series':3,'timing':'validate including fresh T2a read transaction; fixture/T3b excluded'}))
    for size,albums in ((5,('vfl',)),(25,('vfl','em24')),(150,('vfl','em24'))):
        case=SuggestionTests('test_a_fresh_five_by_five')
        try:
            case.setUp();case.configure(size,albums)
            sql=[];case.db.set_trace_callback(sql.append)
            result=case.validator.validate(case.suggestion,1)
            case.db.set_trace_callback(None)
            assert result.status==SuggestionStatus.VALID
            count=len(sql)
            for series in range(1,4):
                start=perf_counter()
                for _ in range(100):result=case.validator.validate(case.suggestion,1)
                elapsed=perf_counter()-start
                assert result.status==SuggestionStatus.VALID
                print(json.dumps({'size_per_side':size,'albums':len(albums),'series':series,
                                  'queries_including_transaction':count,'milliseconds':elapsed*10}),flush=True)
        finally:
            case.doCleanups()


if __name__=='__main__':run()
