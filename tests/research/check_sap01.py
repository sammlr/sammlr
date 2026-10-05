"""SAP browser acceptance on a fresh synthetic V20 database; never real user data."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]
BASE='http://127.0.0.1:18081'
OUT=ROOT/'tests/research/artifacts/sap-01a'


def configure(path):
    if not path.resolve().is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Synthetic test database must be under /private/tmp')
    os.environ.update(SAMMLR_ENV='testing',SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret',DATABASE_PATH=str(path),TMPDIR='/private/tmp')
    import webapp
    webapp.DB=str(path);webapp.app.testing=True
    return webapp


def serve(path,album_count=3):
    if not ROOT.is_relative_to(Path('/private/tmp')) or path.exists():
        raise RuntimeError('Fresh synthetic database in isolated checkout required')
    configure_path=path.resolve()
    if not configure_path.is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Outside test directory')
    from tests.test_integration01_trade_shell import fixture
    fixture(path,60)
    with closing(sqlite3.connect(path)) as db,db:
        db.execute('DELETE FROM stickers')
        for user in range(1,62):
            for album in ('wm26','em24'):
                db.execute('INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,?,1)',(user,album))
            for code in (['1','2','3','4','5','6','7','8'] if user==1 else ['31','32','33','34','35']):
                db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'vfl',?,2,1)",(user,code))
            codes=['FWC1','FWC2','FWC3'] if user==1 else (['POR17','GER14','ARG3'] if user%2==0 else ['POR17'])
            for code in codes:
                db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'wm26',?,3,2)",(user,code))
        db.execute("UPDATE users SET username='Demo Jens' WHERE id=2")
        db.execute("UPDATE users SET username='Demo Moni' WHERE id=3")
        db.execute("UPDATE users SET username='Demo ohne Gegentausch' WHERE id=61")
        db.execute('DELETE FROM stickers WHERE user_id=61')
        db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (61,'wm26','POR17',2,1)")
        for code in ['FWC1','FWC2','FWC3']:
            db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (61,'wm26',?,1,0)",(code,))
        db.execute("UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=61 AND album_id='vfl'")
        db.execute("UPDATE users SET favorite_album_id='wm26' WHERE id=1")
        db.execute("UPDATE user_albums SET visibility='public'")
    if album_count>3:
        with closing(sqlite3.connect(path)) as db,db:
            for index in range(4,album_count+1):
                album=f"fixture{index}"
                db.execute("INSERT INTO albums(id,name,total,complete) VALUES (?,?,728,0)",(album,f"Synthetisches Testalbum {index:02}"))
                for user in (1,2):
                    db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,?,1)",(user,album))
    app=configure(path)
    # Test-only entry route, only in this synthetic harness; no production bypass.
    @app.app.get('/sap-fixture-login')
    def fixture_login():
        from flask import session,redirect
        session['user_id']=1;session['auth_version']=1
        return redirect('/tauschen')
    from flask import request
    app.app.before_request_funcs.setdefault(None, []).insert(0,
        lambda: fixture_login() if request.path == '/sap-fixture-login' else None)
    app.app.run(host='127.0.0.1',port=18081,debug=False)


def check(path,album_count=3):
    from playwright.sync_api import sync_playwright
    app=configure(path)
    cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':1,'auth_version':1})
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True)
    results=[];errors=[];writes=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch()
        for width in (375,390,430,1280):
            c=b.new_context(viewport={'width':width,'height':900})
            c.add_cookies([{'name':'session','value':cookie,'url':BASE}])
            p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
            p.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
            def go(url='/tauschen/sammlr'):
                response=p.goto(BASE+url);assert response.status==200
                p.evaluate('document.fonts.ready')
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            go()
            assert p.locator('[name="album"]:checked').count()==album_count
            assert p.locator('.sap-results a').count()==50
            assert p.locator('[name="sort"]').count()==0
            assert 'Doppelte' not in p.locator('main').inner_text()
            assert not p.locator('.sap-album-picker').evaluate('e=>e.open')
            assert p.locator('[name="q"]').get_attribute('placeholder')=='Sticker, Album oder Sammlr suchen …'
            p.screenshot(path=str(OUT/f'default-{width}.png'),full_page=False)
            p.locator('.sap-more').click();assert p.locator('.sap-results a').count()==59
            p.locator('.sap-album-picker summary').click()
            p.locator('[data-albums="none"]').click();assert p.locator('.sap-results a').count()==0
            p.locator('.sap-album-picker summary').click()
            p.locator('[data-albums="all"]').click();assert p.locator('[name="album"]:checked').count()==album_count
            p.locator('[name="q"]').fill('POR17, GER14 / ARG3')
            p.locator('.sap-filters [type="submit"]').click()
            assert '8 Sticker' in p.locator('.sap-results a').first.inner_text()
            assert p.locator('[name="q"]').input_value()=='POR17, GER14 / ARG3'
            p.locator('.sap-more').click();assert 'Weitere Sammlr mit diesem Sticker' in p.locator('main').inner_text()
            assert 'Demo ohne Gegentausch' in p.locator('.sap-additional').inner_text()
            p.screenshot(path=str(OUT/f'search-{width}.png'),full_page=False)
            p.locator('.sap-album-picker summary').click()
            with p.expect_navigation():
                p.locator('[name="album"][value="wm26"]').uncheck()
            assert p.locator('.sap-results a').count()==0
            go('/tauschen/sammlr?q=Demo+Jens')
            assert p.locator('.sap-results a').count()==1
            p.locator('.sap-results a').click();assert '/profil/Demo%20Jens' in p.url
            go('/tauschen/sammlr?filtered=1&album=wm26&q=POR17&sort=duplicates')
            more=p.locator('.sap-more');more.scroll_into_view_if_needed()
            assert more.evaluate('e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===e}')
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            results.append({'width':width,'default_all':True,'initial_limit':50,'more_preserves_query':True,'search_and_filters':True,'extra_isolated':True,'partner_navigation':True,'overflow':False,'more_not_covered':True})
            c.close()
        b.close()
    assert not errors,errors
    assert not writes,writes
    assert before==hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT/'browser-results.json').write_text(json.dumps({'results':results,'errors':errors,'writes':writes,'database_unchanged':True},indent=2)+'\n')
    print('PASS: SAP interaction, pagination, four widths, read-only database')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['serve','check']);parser.add_argument('database',type=Path)
    args=parser.parse_args();(serve if args.mode=='serve' else check)(args.database)
