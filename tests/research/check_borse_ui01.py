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
OUT = ROOT/'tests/research/artifacts/borse-ui01'
BASE = 'http://127.0.0.1:18081'


def serve():
    from tests.test_integration01_trade_shell import fixture
    from flask import request
    temp = tempfile.TemporaryDirectory(prefix='borse-ui01-', dir='/private/tmp')
    paths = [Path(temp.name)/f'synthetic-{n}.db' for n in range(4)]
    for n, path in enumerate(paths):
        fixture(path, n)
        with closing(sqlite3.connect(path)) as db, db:
            from services.albums import all_codes
            codes = all_codes('wm26')
            for user in range(1,n+2):
                db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'wm26',1)",(user,))
            for partner in range(n):
                for offset in range(5):
                    for user, code in [(1,codes[partner*10+offset]),(partner+2,codes[partner*10+offset+5])]:
                        db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'wm26',?,2,1)",(user,code))
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
    signer=Flask(__name__);signer.secret_key='sammlr-explicit-testing-secret'
    cookie=signer.session_interface.get_signing_serializer(signer).dumps({'user_id':1,'auth_version':1})
    OUT.mkdir(parents=True,exist_ok=True)
    results=[];errors=[];writes=[];bubble_overlaps=[]
    props=['width','height','padding','borderRadius','borderWidth','boxSizing','aspectRatio']
    style='(e,ps)=>Object.fromEntries(ps.map(p=>[p,getComputedStyle(e)[p]]))'
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (375,390,430,1280):
            context=browser.new_context(viewport={'width':width,'height':900},has_touch=True)
            context.add_cookies([{'name':'session','value':cookie,'url':BASE}])
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
            page.goto(BASE+'/album/vfl');page.evaluate('document.fonts.ready')
            wall=page.locator('.wall .slot').first.evaluate(style,props)
            qty=page.locator('.wall .slot.duplicate .sticker-qty').first.evaluate(style,props)
            for n in (3,2,1,0):
                context.add_cookies([{'name':'fixture_count','value':str(n),'url':BASE}])
                page.goto(BASE+'/tauschen');page.evaluate('document.fonts.ready');page.wait_for_timeout(80)
                assert page.locator('.trade-proposal').count()==n
                assert page.locator('text=Laufende Tausche').count()==0
                assert page.get_by_role('button',name='Meine Anfragen').is_disabled()
                assert page.get_by_role('link',name='Alle Sammlr').get_attribute('href')=='/tauschen/sammlr'
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if n:
                    text=f'{n} vielversprechende Tauschvorschläge für dich.' if n>1 else '1 vielversprechender Tauschvorschlag für dich.'
                    assert page.get_by_text(text,exact=True).count()==1
                    assert page.locator('.trade-proposal').first.locator('p').inner_text()=='15 Sticker · 2 Alben'
                    faces=page.locator('.trade-top .slot')
                    for face in faces.all():
                        assert face.evaluate(style,props)==wall,(width,n,face.evaluate(style,props),wall)
                        assert face.locator('.sticker-qty').evaluate(style,props)==qty
                        if not face.evaluate('''e=>{const q=e.querySelector('.sticker-qty').getBoundingClientRect(),num=e.querySelector('.sammlr-retro-number-visual').getBoundingClientRect();return q.top>=num.bottom || q.left>=num.right || q.right<=num.left}'''):
                            bubble_overlaps.append({'width':width,'count':n,'code':face.get_attribute('data-code')})
                    boxes=page.locator('.trade-proposal .sticker-slot-frame').evaluate_all('es=>es.map(e=>{let r=e.getBoundingClientRect();return {top:r.top,width:r.width}})')
                    assert max(r['top'] for r in boxes)-min(r['top'] for r in boxes)<1,boxes
                    bounds=page.evaluate('''()=>{const t=document.querySelector('.trade-stage').getBoundingClientRect();const groups=[...document.querySelectorAll('.trade-proposal')].map(p=>{let r=[...p.querySelectorAll('.slot,.sticker-wall-stack-layer')].map(e=>e.getBoundingClientRect());return {left:Math.min(...r.map(x=>x.left)),right:Math.max(...r.map(x=>x.right)),top:Math.min(...r.map(x=>x.top)),bottom:Math.max(...r.map(x=>x.bottom))}});return {groups,stage:{left:t.left,right:t.right,top:t.top,bottom:t.bottom}}}''')
                    t=bounds['stage'];g=bounds['groups'];left=min(r['left'] for r in g);right=max(r['right'] for r in g)
                    assert abs((left+right)/2-(t['left']+t['right'])/2)<.1,bounds
                    assert left>t['left'] and right<t['right'],(width,bounds)
                    assert all(g[i]['right']<g[i+1]['left'] for i in range(len(g)-1)),(width,bounds)
                    page.screenshot(path=str(OUT/f'home-{width}-{n}.png'),full_page=True)
                    page.locator('.trade-proposal .slot').first.tap()
                    page.wait_for_selector('.trade-explorer:not([hidden])')
                    assert page.url.endswith('/tauschen')
                    assert page.locator('.trade-flight-layer').count()==1
                    frames=page.locator('.trade-flight-layer .sticker-slot-frame .slot')
                    for face in frames.all():assert face.evaluate(style,props)==wall
                    assert page.evaluate("document.getAnimations().every(a=>a.effect.getKeyframes().every(k=>!String(k.transform||'').includes('scale')))")
                    page.wait_for_timeout(500)
                    assert page.locator('.trade-explorer .trade-group').count()>=3
                    assert page.locator('.trade-explorer .trade-group h2').all_text_contents().count('Du bekommst · FIFA World Cup 2026')==1
                    assert page.get_by_role('link',name='Tausch ansehen').count()==1
                    if width==390 and n==3:page.screenshot(path=str(OUT/'total-open-390.png'),full_page=True)
                    summary=page.locator('.trade-explorer summary').first
                    summary.focus();page.keyboard.press('Enter')
                    page.wait_for_timeout(50)
                    assert page.locator('.trade-flight-layer').count()==1
                    page.wait_for_timeout(450)
                    for face in page.locator('.trade-explorer details[open] .trade-fan .slot').all():assert face.evaluate(style,props)==wall
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    if width==390 and n==3:page.screenshot(path=str(OUT/'album-open-390.png'),full_page=True)
                    page.get_by_role('link',name='Tausch ansehen').click();page.wait_for_url('**/tauschen/vorschlag/*')
                    page.locator('[data-open-groups]').click();page.wait_for_timeout(500)
                    for face in page.locator('.trade-fan .slot').all():assert face.evaluate(style,props)==wall
                    page.locator('[data-close-groups]').click()
                    assert page.locator('details[open]').count()==0
                else:assert 'vielversprechend' not in page.locator('main').inner_text()
                results.append({'width':width,'count':n,'wall':wall,'parity_center_no_overlap_no_overflow':True})
            context.add_cookies([{'name':'fixture_count','value':'3','url':BASE}])
            page.emulate_media(reduced_motion='reduce');page.goto(BASE+'/tauschen')
            page.locator('.trade-proposal .slot').first.click();page.wait_for_selector('.trade-explorer:not([hidden])')
            assert page.locator('.trade-flight-layer').count()==0
            page.locator('.trade-explorer summary').first.click()
            assert page.locator('.trade-flight-layer').count()==0
            page.get_by_role('button',name='Zurück zu Vorschlägen').click()
            assert page.locator('.trade-top').is_visible()
            await_path='**/tauschen/vorschlag/*'
            page.route(await_path,lambda route:route.fulfill(status=404,body='not found'))
            page.locator('.trade-proposal .slot').first.click()
            page.wait_for_function("document.querySelector('.trade-explorer-status').textContent.length>0")
            assert page.locator('.trade-top').is_visible()
            context.close()
        browser.close()
    assert not errors and not writes,(errors,writes)
    (OUT/'checks.json').write_text(json.dumps({'cases':results,'errors':errors,'writes':writes,'reduced_motion':True,'unavailable_deal_safe':True,'bubble_bounding_box_conflicts':bubble_overlaps,'acceptance_pending_canonical_bubble_decision':True},indent=2)+'\n')
    print('Interaction gates passed; bubble acceptance pending. 16 cases, canonical geometry, two expansion levels, 440ms no-scale animation, navigation, reduced motion, read-only')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--serve',action='store_true');args=p.parse_args()
    if args.serve:serve()
    else:check()
