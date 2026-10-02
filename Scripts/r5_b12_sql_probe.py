"""Instrument two album GETs in a temporary candidate, without changing runtime files.

Timings here include instrumentation and are diagnostic, not the HTTP R4 gate.
Only SQL templates/plans and aggregate counters are emitted; bind values are not.
"""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import cProfile
import json
import os
from pathlib import Path
import pstats
import re
import resource
import sqlite3
import sys
import threading
import time


original_connect = sqlite3.connect
local = threading.local()


class Cursor(sqlite3.Cursor):
    def execute(self, sql, parameters=()):
        start = time.perf_counter()
        result = super().execute(sql, parameters)
        self.query = ' '.join(sql.split())
        if hasattr(local, 'queries'):
            record = local.queries[self.query]
            record['count'] += 1
            record['sqlite_ms'] += (time.perf_counter() - start) * 1000
            record.setdefault('parameters', parameters)
        return result

    def fetchone(self):
        return self.measured_fetch(super().fetchone)

    def fetchall(self):
        return self.measured_fetch(super().fetchall)

    def fetchmany(self, *args):
        return self.measured_fetch(lambda: super(Cursor, self).fetchmany(*args))

    def measured_fetch(self, function):
        start = time.perf_counter()
        result = function()
        if hasattr(local, 'queries') and hasattr(self, 'query'):
            local.queries[self.query]['sqlite_ms'] += (time.perf_counter() - start) * 1000
        return result


class Connection(sqlite3.Connection):
    def cursor(self, *args, **kwargs):
        return super().cursor(factory=Cursor)

    def execute(self, sql, parameters=()):
        return self.cursor().execute(sql, parameters)


def connect(*args, **kwargs):
    kwargs['factory'] = Connection
    return original_connect(*args, **kwargs)


def usage():
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {key: getattr(value, key) for key in (
        'ru_utime', 'ru_stime', 'ru_inblock', 'ru_oublock', 'ru_nvcsw', 'ru_nivcsw')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.candidate, args.database, args.output):
        if not path.resolve().is_relative_to(Path('/private/tmp')):
            raise ValueError('All inputs and output must be isolated')
    sys.path[:0] = [str(args.candidate.resolve()), str(args.candidate.resolve() / 'App')]
    os.environ.update(SAMMLR_ENV='production', SAMMLR_SECRET_KEY='r4-isolated-performance-secret',
        SAMMLR_R4_PERFORMANCE_GATE='1', DATABASE_PATH=str(args.database.resolve()), PORT='1')
    import performance_wsgi
    app = performance_wsgi.app
    app.config.update(TESTING=True)
    sqlite3.connect = connect

    def request(path, user):
        client = app.test_client()
        with client.session_transaction() as session:
            session['user_id'] = user
            session['auth_version'] = 1
            session['csrf_token'] = 'r4-diagnostic-only'
        local.queries = defaultdict(lambda: {'count': 0, 'sqlite_ms': 0})
        started = time.perf_counter()
        response = client.get(path)
        return {'status': response.status_code, 'wall_ms': (time.perf_counter() - started) * 1000,
                'response_bytes': len(response.data), 'queries': dict(local.queries)}

    report = {'note': 'Instrumented Flask test-client diagnostic, not HTTP gate timing', 'routes': {}}
    for path in ('/album/perf01', '/album/perf01?filter=missing'):
        profiler = cProfile.Profile()
        before = usage()
        profiler.enable()
        cold = request(path, 1)
        profiler.disable()
        after = usage()
        hot = request(path, 1)
        before_parallel = usage()
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            parallel = list(executor.map(lambda user: request(path, user), range(1, 21)))
        parallel_ms = (time.perf_counter() - started) * 1000
        after_parallel = usage()
        plans = []
        with original_connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
            for sql, record in cold['queries'].items():
                plan = []
                if sql.upper().startswith(('SELECT ', 'WITH ')):
                    try:
                        plan = [row[3] for row in connection.execute('EXPLAIN QUERY PLAN ' + sql, record['parameters'])]
                    except sqlite3.Error as error:
                        plan = [type(error).__name__]
                plans.append({'sql': re.sub(r"'[^']*'", "'…'", sql), 'count': record['count'],
                              'sqlite_ms': round(record['sqlite_ms'], 3), 'plan': plan})
        profile = []
        for (filename, line, name), (_, calls, own, cumulative, _) in sorted(
                pstats.Stats(profiler).stats.items(), key=lambda item: item[1][3], reverse=True)[:35]:
            try:
                filename = str(Path(filename).relative_to(args.candidate))
            except ValueError:
                filename = Path(filename).name
            profile.append({'file': filename, 'line': line, 'function': name, 'calls': calls,
                            'own_ms': round(own * 1000, 3), 'cumulative_ms': round(cumulative * 1000, 3)})

        def summary(sample):
            return {key: value for key, value in sample.items() if key != 'queries'} | {
                'sql_count': sum(q['count'] for q in sample['queries'].values()),
                'sqlite_ms': sum(q['sqlite_ms'] for q in sample['queries'].values())}

        report['routes'][path] = {'profiled_first': summary(cold), 'warm': summary(hot),
            'query_plans': plans, 'cpu_profile': profile,
            'profiled_usage_delta': {key: after[key] - before[key] for key in before},
            'parallel': {'wall_ms': parallel_ms,
                'usage_delta': {key: after_parallel[key] - before_parallel[key] for key in before_parallel},
                'requests': [summary(sample) for sample in parallel]}}
    sqlite3.connect = original_connect
    args.output.write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
