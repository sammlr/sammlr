"""Three real HTTP/browser handshake flows with exclusively synthetic databases."""
from pathlib import Path
import json,sqlite3,sys,tempfile,threading
from contextlib import closing
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]


def main():
    if not ROOT.is_relative_to(Path('/private/tmp')):raise RuntimeError('Isolated source checkout required')
    def guard(event,args):
        if event=='sqlite3.connect':
            from urllib.parse import urlparse,unquote
            name=str(args[0])
            if name==':memory:' or name.startswith('file::memory:'):return
            path=Path(unquote(urlparse(name).path) if name.startswith('file:') else name)
            if not path.resolve().is_relative_to(Path('/private/tmp')):raise RuntimeError('Protected SQLite path')
    sys.addaudithook(guard)
    from tests.test_integration01_trade_shell import fixture
    from App.Database.migration_runner import migrate
    from tests.research.check_sap01 import configure
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    out=Path('/private/tmp/lifecycle03/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle03')
    def database(label):
        path=Path(temp.name)/(label+'.db');fixture(path)
        with closing(sqlite3.connect(path)) as db:migrate(db,25)
        return path
    path=database('A');app=configure(path)
    server=make_server('127.0.0.1',0,app.app,threaded=True);base=f'http://127.0.0.1:{server.server_port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    errors=[];results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();pages=[]
            for user in (1,2):
                c=browser.new_context(viewport={'width':390,'height':844})
                cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':user,'auth_version':1})
                c.add_cookies([dict(name='session',value=cookie,url=base)])
                p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));pages.append(p)
            a,b=pages
            def send():
                a.goto(base+'/tauschen/sammlr/2/smartdeal');a.get_by_role('button',name='Tausch anfragen',exact=True).click()
                a.wait_for_url('**/tauschen/anfragen/*');return a.url
            def remove(user,code):
                with closing(sqlite3.connect(path)) as db,db:
                    db.execute('UPDATE stickers SET quantity=1,duplicates=0 WHERE user_id=? AND sticker_code=?',(user,code))
            url=send();b.goto(url);b.get_by_role('button',name='Annehmen',exact=True).click()
            b.wait_for_function('document.body.textContent.includes("Tausch angenommen")')
            a.goto(url)
            for p in (a,b):
                assert 'Tausch angenommen' in p.locator('body').inner_text()
                assert p.get_by_role('button',name='Anfrage zurückziehen',exact=True).count()==0
                assert p.get_by_role('button',name='Anfrage ablehnen',exact=True).count()==0
                assert 'Als Nächstes: Sticker vorbereiten' in p.locator('body').inner_text()
            b.screenshot(path=str(out/'A-accepted.png'),full_page=True)
            results.append('A: send / exact acceptance / no release actions / preparation boundary')
            path=database('B');app.DB=str(path);url=send();remove(2,'6')
            b.goto(url);b.get_by_role('button',name='Annehmen',exact=True).click()
            b.wait_for_function('document.body.textContent.includes("nicht mehr vollständig möglich")')
            b.screenshot(path=str(out/'B-original-invalid.png'),full_page=True)
            b.get_by_role('button',name='Tausch neu berechnen',exact=True).click()
            b.wait_for_function('document.body.textContent.includes("Gegenangebot prüfen")')
            with closing(sqlite3.connect(path)) as db:assert db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0]==1
            b.screenshot(path=str(out/'B-counter-preview.png'),full_page=True)
            b.get_by_role('button',name='Gegenangebot senden',exact=True).click()
            b.wait_for_function('document.body.textContent.includes("Gegenangebot von")')
            a.goto(url);assert a.get_by_role('button',name='Tausch neu berechnen',exact=True).count()==0
            a.screenshot(path=str(out/'B-counter-received.png'),full_page=True)
            a.get_by_role('button',name='Annehmen',exact=True).click()
            a.wait_for_function('document.body.textContent.includes("Tausch angenommen")')
            with closing(sqlite3.connect(path)) as db:
                assert db.execute('SELECT COUNT(*) FROM lifecycle_revision_positions WHERE revision_id=1').fetchone()[0]==10
                assert db.execute('SELECT COUNT(*) FROM lifecycle_revision_positions WHERE revision_id=2').fetchone()[0]==8
                assert db.execute('SELECT accepted_revision_id FROM lifecycle_contracts').fetchone()[0]==2
            results.append('B: invalid original unchanged / explicit counter preview+send / original sender accepts revision 2')
            path=database('C');app.DB=str(path);url=send();remove(2,'6')
            b.goto(url);b.get_by_role('button',name='Tausch neu berechnen',exact=True).click()
            b.get_by_role('button',name='Gegenangebot senden',exact=True).click()
            b.wait_for_function('document.body.textContent.includes("Gegenangebot von")')
            remove(1,'1');a.goto(url);a.get_by_role('button',name='Annehmen',exact=True).click()
            a.wait_for_function('document.body.textContent.includes("Verhandlung beendet")')
            assert a.get_by_role('button',name='Tausch neu berechnen',exact=True).count()==0
            assert a.get_by_role('button',name='Annehmen',exact=True).count()==0
            with closing(sqlite3.connect(path)) as db:
                assert db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0]==0
                assert db.execute("SELECT COUNT(*) FROM lifecycle_need_claims WHERE state<>'released'").fetchone()[0]==0
                assert db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0]==2
            for width in (375,390,430,1280):
                a.set_viewport_size({'width':width,'height':900});a.goto(url)
                assert a.evaluate('document.documentElement.scrollWidth<=innerWidth')
                a.screenshot(path=str(out/f'C-ended-{width}.png'),full_page=True)
            results.append('C: invalid counter terminal / all bindings released / no third offer')
            assert not errors,errors;browser.close()
    finally:server.shutdown();thread.join();temp.cleanup()
    (out/'results.json').write_text(json.dumps(dict(passed=results,errors=errors),indent=2)+'\n')
    print(json.dumps(results))

if __name__=='__main__':main()
