"""Startscreen-only checks; all fixtures SQL-generated under /private/tmp."""
import argparse
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'App')]
OUT = ROOT/'tests/research/artifacts/integration-01a1'
BASE = 'http://127.0.0.1:18081'


def serve():
    from tests.test_integration01_trade_shell import fixture
    from flask import request
    temp = tempfile.TemporaryDirectory(prefix='integration01a1-', dir='/private/tmp')
    paths = [Path(temp.name)/f'synthetic-{n}.db' for n in range(4)]
    for n, path in enumerate(paths):
        fixture(path, n)
        with closing(sqlite3.connect(path)) as db, db:
            for partner in range(n):
                for offset in range(5):
                    for user, code in [(1, str(101+partner*10+offset)), (partner+2, str(106+partner*10+offset))]:
                        db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'vfl',?,2,1)", (user,code))
    os.environ.update(SAMMLR_ENV='testing', SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret', DATABASE_PATH=str(paths[3]))
    import webapp
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    @webapp.app.before_request
    def synthetic_fixture_only():
        # Test harness only; no fixture controls in the productive application.
        webapp.DB = str(paths[int(request.cookies.get('fixture_count', '3'))])
    @webapp.app.after_request
    def unchanged(response):
        assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        return response
    webapp.app.run(host='127.0.0.1', port=18081, threaded=False)


def check():
    from flask import Flask
    from playwright.sync_api import sync_playwright
    signer = Flask(__name__); signer.secret_key = 'sammlr-explicit-testing-secret'
    cookie = signer.session_interface.get_signing_serializer(signer).dumps({'user_id':1,'auth_version':1})
    OUT.mkdir(parents=True, exist_ok=True)
    results=[]; errors=[]; writes=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (375,390,430,1280):
            context=browser.new_context(viewport={'width':width,'height':900},has_touch=True)
            context.add_cookies([{'name':'session','value':cookie,'url':BASE}])
            page=context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
            page.goto(BASE+'/album/vfl');page.evaluate('document.fonts.ready')
            dims="e=>[getComputedStyle(e).width,getComputedStyle(e).height]"
            wall=page.locator('.wall .slot').first.evaluate(dims)
            for n in (3,2,1,0):
                context.add_cookies([{'name':'fixture_count','value':str(n),'url':BASE}])
                page.goto(BASE+'/tauschen');page.evaluate('document.fonts.ready');page.wait_for_timeout(80)
                assert page.locator('.trade-proposal').count()==n
                assert page.locator('text=Laufende Tausche').count()==0
                assert page.get_by_role('button',name='Meine Anfragen').is_disabled()
                assert page.get_by_role('link',name='Alle Sammlr').get_attribute('href')=='/tauschen/sammlr'
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if n:
                    assert page.locator('.trade-proposal [data-visible-stack-layers="10"]').count()==n
                    expected=f'{n} vielversprechende Tauschvorschläge für dich.' if n>1 else '1 vielversprechender Tauschvorschlag für dich.'
                    assert page.get_by_text(expected,exact=True).count()==1
                    assert page.locator('.trade-proposal').first.locator('p').count()==1
                    assert 'VfL Osnabrück' not in page.locator('.trade-top').inner_text()
                    for face in page.locator('.trade-proposal .slot,.trade-proposal .sticker-wall-stack-layer').all():
                        size=face.evaluate(dims)
                        assert size[0]=='72px' and abs(float(size[1][:-2])-82.08)<.02,(width,n,size)
                    bounds=page.evaluate('''()=>{const t=document.querySelector('.trade-table').getBoundingClientRect();const r=[...document.querySelectorAll('.trade-top .slot,.trade-top .sticker-wall-stack-layer')].map(e=>e.getBoundingClientRect());return {left:Math.min(...r.map(x=>x.left)),right:Math.max(...r.map(x=>x.right)),top:Math.min(...r.map(x=>x.top)),bottom:Math.max(...r.map(x=>x.bottom)),table:{left:t.left,right:t.right,top:t.top,bottom:t.bottom}}}''')
                    t=bounds['table'];assert abs((bounds['left']+bounds['right'])/2-(t['left']+t['right'])/2)<.1,bounds
                    assert bounds['left']>=t['left']+8 and bounds['right']<=t['right']-8,(width,n,bounds)
                    assert bounds['top']>=t['top']+8 and bounds['bottom']<=t['bottom']-8
                else:
                    assert page.get_by_text('Im Moment gibt es keine passenden Tauschvorschläge.',exact=True).count()==1
                    assert 'vielversprechend' not in page.locator('main').inner_text()
                if n:page.screenshot(path=str(OUT/f'home-{width}-{n}.png'),full_page=True)
                results.append({'width':width,'count':n,'wall_dimensions':wall,'fixed_trade_dimensions':['72px','82.08px'],'center_containment_overflow':True})
                if n:
                    page.locator('.trade-proposal .slot').first.tap();page.wait_for_url('**/tauschen/vorschlag/*')
                    assert page.locator('.trade-group').count()>0
                    for face in page.locator('summary .slot,summary .sticker-wall-stack-layer').all():
                        size=face.evaluate(dims)
                        assert size[0]=='72px' and abs(float(size[1][:-2])-82.08)<.02,size
                    summary=page.locator('.trade-group summary').first
                    summary.focus();page.keyboard.press('Enter')
                    assert page.locator('.trade-group details[open]').count()==1
                    page.locator('[data-open-groups]').click()
                    for face in page.locator('.trade-fan .slot').all():
                        size=face.evaluate(dims)
                        assert size[0]=='72px' and abs(float(size[1][:-2])-82.08)<.02,size
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    if width==390 and n==3:page.screenshot(path=str(OUT/'deal-open-390.png'),full_page=True)
                    page.locator('[data-close-groups]').tap()
                    assert page.locator('.trade-group details[open]').count()==0
                    page.emulate_media(reduced_motion='reduce')
                    assert page.evaluate('document.getAnimations().length')==0
                    page.goto(BASE+'/album/vfl');page.evaluate('document.fonts.ready')
                    assert page.locator('.wall .slot').first.evaluate(dims)==wall
            context.close()
        browser.close()
    assert not errors and not writes,(errors,writes)
    (OUT/'checks.json').write_text(json.dumps({'cases':results,'errors':errors,'writes':writes},indent=2)+'\n')
    print('PASS: 16 cases, fixed Trade sizes across top/album/fan/receive/give, unchanged wall, centering/containment, wording, navigation, read-only')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--serve',action='store_true');args=p.parse_args()
    if args.serve:serve()
    else:check()
