"""Productive HTTP routes on fresh synthetic V20/V22 databases, isolated checkout only."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if not ROOT.is_relative_to(Path('/private/tmp')):
    raise RuntimeError('Run in the isolated synthetic test checkout under /private/tmp')
sys.path[:0] = [str(ROOT), str(ROOT / 'App')]

def guard(event, args):
    if event != 'sqlite3.connect':
        return
    from urllib.parse import unquote, urlparse
    name = str(args[0])
    if name == ':memory:' or name.startswith('file::memory:'):
        return
    path = Path(unquote(urlparse(name).path) if name.startswith('file:') else name)
    if not path.resolve().is_relative_to(Path('/private/tmp')):
        raise AssertionError('Database outside synthetic test area')

sys.addaudithook(guard)
from tests.test_integration02a_trade_preferences import TradeV2PreferencesTests, CROSS

case = TradeV2PreferencesTests()
case.setUp()
try:
    case.populate({'vfl':7}, {'wm26':7})
    os.environ.update(SAMMLR_ENV='testing', SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret',
                      DATABASE_PATH=str(case.path), TMPDIR='/private/tmp')
    import webapp
    webapp.DB = str(case.path)
    webapp.app.testing = True
    client = webapp.app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['auth_version'] = 1
    results = []
    for schema, expected in [(20,0), (22,1)]:
        if schema == 22:
            case.modes(dict.fromkeys(('vfl','wm26'),CROSS), dict.fromkeys(('vfl','wm26'),CROSS))
        before = hashlib.sha256(case.path.read_bytes()).hexdigest()
        response = client.get('/tauschen')
        assert response.status_code == 200
        assert response.text.count('class="trade-proposal"') == expected
        for route in ['/healthz','/tauschen/sammlr','/tauschen/laufend']:
            assert client.get(route).status_code == 200, route
        assert client.get('/tauschen/sammlr/2').status_code == (200 if expected else 404)
        if expected:
            assert client.get('/tauschen/vorschlag/2').status_code == 200
        assert before == hashlib.sha256(case.path.read_bytes()).hexdigest()
        results.append(dict(schema=schema, proposals=expected, routes_ok=True, database_unchanged=True))
    print(json.dumps(results, indent=2))
finally:
    case.doCleanups()
