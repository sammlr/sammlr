"""Read-only runtime investigation; all servers and data stay in a temporary candidate.

Canonical runs invoke the unchanged R4 CLI. Warm diagnostics keep a route process
alive for two extra waves; these are reported separately, never substituted for R4.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import urlopen


ROUTES = ('album', 'stickerwall_missing', 'home', 'collection', 'album_trade_hub', 'profile')


def context():
    return {'utc': datetime.now(timezone.utc).isoformat(), 'load_average': os.getloadavg(),
            'logical_cpus': os.cpu_count()}


def load_runner(candidate):
    path = candidate / 'Scripts/r4_v20_performance_gate.py'
    spec = importlib.util.spec_from_file_location('b12_r4', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical(args):
    for number in range(1, 4):
        name = f'canonical-{number}'
        metadata = {'before': context()}
        with (args.output / f'{name}.log').open('x') as log:
            completed = subprocess.run([
                str(args.python), str(args.candidate / 'Scripts/r4_v20_performance_gate.py'),
                '--database', str(args.output / f'{name}.db'),
                '--output', str(args.output / f'{name}.json'),
                '--python', str(args.python), '--port', str(args.port + (number - 1) * 20),
            ], cwd=args.candidate, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                stdout=log, stderr=subprocess.STDOUT)
        metadata.update(after=context(), exit_code=completed.returncode)
        (args.output / f'{name}-context.json').write_text(json.dumps(metadata, indent=2))
        print(json.dumps({'completed': name, 'exit_code': completed.returncode}), flush=True)
        if completed.returncode:
            raise RuntimeError(f'Canonical runner failed: {name}')


def stop(server):
    if server.poll() is None:
        os.killpg(server.pid, signal.SIGTERM)
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)
            server.wait(timeout=5)
    server.stderr.close()


def start(args, database, port):
    environment = {**os.environ, 'SAMMLR_ENV': 'production',
        'SAMMLR_SECRET_KEY': 'r4-isolated-performance-secret',
        'SAMMLR_R4_PERFORMANCE_GATE': '1', 'DATABASE_PATH': str(database),
        'PORT': str(port), 'PYTHONDONTWRITEBYTECODE': '1'}
    base = f'http://127.0.0.1:{port}'
    server = subprocess.Popen([
        str(args.python), '-m', 'gunicorn', '--workers', '1', '--threads', '20',
        '--bind', f'127.0.0.1:{port}', '--access-logfile', '/dev/null',
        '--error-logfile', '-', 'performance_wsgi:app',
    ], cwd=args.candidate / 'App', env=environment, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, text=True, start_new_session=True)
    for _ in range(60):
        try:
            if urlopen(base + '/healthz', timeout=30).status == 200:
                return server, base
        except OSError:
            if server.poll() is not None:
                break
            time.sleep(.25)
    stop(server)
    raise RuntimeError('Diagnostic server did not become healthy')


def wave(runner, pool, url, method):
    typical = [runner._single_request(pool[0], url, method) for _ in range(5)]
    intervals = []

    def measured(opener):
        begin = time.perf_counter()
        result = runner._single_request(opener, url, method)
        intervals.append((begin, time.perf_counter()))
        return result

    with ThreadPoolExecutor(max_workers=20) as executor:
        samples = list(executor.map(measured, pool))
    events = sorted([(a, 1) for a, _ in intervals] + [(b, -1) for _, b in intervals])
    active = peak = 0
    for _, delta in events:
        active += delta
        peak = max(peak, active)
    return {'typical': runner._summarize(typical), 'concurrent_20': runner._summarize(samples),
            'peak_client_overlap': peak,
            'launch_spread_ms': round((max(a for a, _ in intervals) - min(a for a, _ in intervals)) * 1000, 3)}


def warm(args):
    runner = load_runner(args.candidate)
    port = args.port
    for number in range(1, 4):
        database = args.output / f'warm-{number}.db'
        report = {'before': context(), 'dataset': runner.prepare_database(database), 'routes': {}}
        runner.inspect_query_plans(database)
        runner.sqlite_lock_probe(database)
        server, base = start(args, database, port)
        port += 1
        try:
            pool = [runner._csrf_login(base, f'perf_user_{i:03d}') for i in range(1, 21)]
        finally:
            stop(server)
        for name in ROUTES:
            path, method, _ = runner.FLOWS[name]
            server, base = start(args, database, port)
            port += 1
            try:
                # This first request is the canonical warm-up, recorded separately.
                cold = runner._single_request(pool[0], base + path, method)
                report['routes'][name] = {'process_cold_request': {
                    'ms': round(cold[0], 3), 'status': cold[1], 'error': cold[2]},
                    'canonical_first_wave': wave(runner, pool, base + path, method),
                    'warm_wave_2': wave(runner, pool, base + path, method),
                    'warm_wave_3': wave(runner, pool, base + path, method)}
            finally:
                stop(server)
        report.update(after=context(), final_database=runner.verify_database(database))
        (args.output / f'warm-{number}.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({'completed': f'warm-{number}'}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('canonical', 'warm'), required=True)
    parser.add_argument('--port', type=int, default=19000)
    args = parser.parse_args()
    args.candidate = args.candidate.resolve()
    args.output = args.output.resolve()
    args.python = args.python.absolute()
    if not all(path.is_relative_to(Path('/private/tmp')) for path in (args.candidate, args.output)):
        raise ValueError('Candidate and all measurements must be under /private/tmp')
    args.output.mkdir(parents=True, exist_ok=True)
    (canonical if args.mode == 'canonical' else warm)(args)


if __name__ == '__main__':
    main()
