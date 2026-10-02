"""Start the assembled app on loopback against a new user-free database."""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.request import urlopen

from Scripts.bootstrap_database import bootstrap


def smoke(database: Path, port: int) -> None:
    root = Path(__file__).resolve().parents[1]
    if not root.is_relative_to(Path('/private/tmp')):
        raise ValueError('Smoke requires an isolated candidate')
    if not database.resolve().is_relative_to(Path('/private/tmp')):
        raise ValueError('Smoke DB must be isolated')
    bootstrap(database)
    environment = {
        'PATH': os.defpath,
        'SAMMLR_ENV': 'development',
        'SAMMLR_SECRET_KEY': secrets.token_hex(32),
        'DATABASE_PATH': str(database.resolve()),
        'PROFILE_PORTRAIT_DIR': str(database.parent / 'smoke-portraits'),
        'PYTHONDONTWRITEBYTECODE': '1',
    }
    server = subprocess.Popen(
        [sys.executable, '-m', 'gunicorn', '--workers', '1',
         '--bind', f'127.0.0.1:{port}', 'webapp:app'],
        cwd=root / 'App', env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        base = f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                with urlopen(base + '/healthz', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError('Server exited before readiness')
                time.sleep(.1)
        else:
            raise RuntimeError('Server readiness timeout')
        result = {}
        for route in ('/healthz', '/login', '/register', '/static/style.css',
                      '/static/sticker_wall_read_only.js', '/static/profile_sticker.css'):
            with urlopen(base + route, timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError('Smoke route failed')
                result[route] = response.status
        print(json.dumps(result, sort_keys=True))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18453)
    args = parser.parse_args()
    smoke(args.database, args.port)
