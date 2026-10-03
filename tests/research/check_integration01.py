"""Production shell on synthetic SQLite only; browser gates and pixel geometry."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'App'))
BASE = 'http://127.0.0.1:18081'
OUT = ROOT / 'tests/research/artifacts/integration-01'


def configure(database):
    path = Path(database).resolve()
    if not path.is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Synthetic test database must be under /private/tmp')
    os.environ.update(SAMMLR_ENV='testing', SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret',
                      DATABASE_PATH=str(path), TMPDIR='/private/tmp')
    import webapp
    webapp.DB = str(path)
    webapp.app.testing = True
    return webapp


def serve(database):
    path = Path(database).resolve()
    if not path.is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Synthetic test database must be under /private/tmp')
    if path.exists():
        raise FileExistsError('Never reuse a database as browser fixture input')
    from tests.test_integration01_trade_shell import fixture
    fixture(path)
    with closing(sqlite3.connect(path)) as db, db:
        for i in range(5):
            for user, code in [(1, str(101+i)), (2, str(106+i))]:
                db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'vfl',?,2,1)", (user, code))
    configure(database).app.run(host='127.0.0.1', port=18081, debug=False)


def check(database):
    from playwright.sync_api import sync_playwright
    webapp = configure(database)
    # Only a synthetic session, signed by the same explicit testing configuration.
    cookie = webapp.app.session_interface.get_signing_serializer(webapp.app).dumps(
        {'user_id': 1, 'auth_version': 1, 'csrf_token': 'synthetic-browser-csrf'})
    baseline = hashlib.sha256(Path(database).read_bytes()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    props = ['width', 'height', 'padding', 'borderRadius', 'borderWidth', 'boxSizing',
             'fontFamily', 'fontSize', 'aspectRatio']
    errors, writes = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (375, 390, 430, 1280):
            context = browser.new_context(viewport={'width': width, 'height': 900}, has_touch=True)
            context.add_cookies([{'name': 'session', 'value': cookie, 'url': BASE}])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda r: writes.append(r.url) if r.method not in ('GET', 'HEAD') else None)
            page.goto(BASE+'/album/vfl');page.evaluate('document.fonts.ready')
            reference = page.locator('.wall .slot').first.evaluate('(e,ps)=>Object.fromEntries(ps.map(p=>[p,getComputedStyle(e)[p]]))', props)
            page.goto(BASE+'/tauschen');page.evaluate('document.fonts.ready')
            assert page.locator('.trade-proposal').count() == 3
            actual = page.locator('.trade-proposal .slot').first.evaluate('(e,ps)=>Object.fromEntries(ps.map(p=>[p,getComputedStyle(e)[p]]))', props)
            assert actual == reference, (width, actual, reference)
            assert page.locator('.bottom-nav-link.active').get_attribute('href') == '/tauschen'
            page.screenshot(path=str(OUT/f'home-{width}.png'), full_page=True)
            page.locator('.trade-proposal .slot').first.click()
            page.wait_for_url('**/tauschen/vorschlag/*')
            summaries = page.locator('.trade-group summary')
            summaries.first.focus();page.keyboard.press('Enter')
            assert page.locator('.trade-group details[open]').count() == 1
            page.locator('[data-open-groups]').tap()
            assert page.locator('.trade-group details[open]').count() == page.locator('.trade-group').count()
            for tile in page.locator('.trade-fan .slot').all():
                face = tile.evaluate('(e,ps)=>Object.fromEntries(ps.map(p=>[p,getComputedStyle(e)[p]]))', props)
                assert face == reference, (width, face, reference)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, 'deal-open')
            page.screenshot(path=str(OUT/f'deal-open-{width}.png'), full_page=True)
            page.locator('[data-close-groups]').click()
            assert page.locator('.trade-group details[open]').count() == 0
            assert page.locator('[data-visible-stack-layers="10"]').count() > 0
            page.emulate_media(reduced_motion='reduce')
            page.locator('[data-open-groups]').click()
            assert page.evaluate('document.getAnimations().length') == 0
            for path in ('/tauschen', '/tauschen/sammlr', '/tauschen/sammlr/2', '/tauschen/laufend'):
                page.goto(BASE+path)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path)
            page.screenshot(path=str(OUT/f'active-{width}.png'), full_page=True)
            results.append({'viewport':width,'card_parity':actual,'touch_mouse_keyboard':True,
                            'groups_independent':True,'all_open_close':True,'reduced_motion':True,'no_overflow':True})
            context.close()
        browser.close()
    assert not errors, errors
    assert not writes, writes
    # /album/vfl is the existing canonical reference route; assert the complete run is read-only.
    assert hashlib.sha256(Path(database).read_bytes()).hexdigest() == baseline
    (OUT/'browser-checks.json').write_text(json.dumps({'results':results,'errors':errors,'writes':writes,'db_unchanged':True},indent=2)+'\n')
    print('PASS production shell: four viewports, actual wall parity, independent groups, pointer/keyboard, reduced motion, DB unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--database', required=True);parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    if args.serve: serve(args.database)
    else: check(args.database)
