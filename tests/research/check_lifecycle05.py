"""Real browser address flows; synthetic-only isolated source candidate."""
from pathlib import Path
import json,sqlite3,sys,tempfile,threading
from contextlib import closing
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]


def main():
    if not ROOT.is_relative_to(Path('/private/tmp')):raise RuntimeError('Isolated candidate required')
    def guard(event,args):
        if event=='sqlite3.connect':
            from urllib.parse import urlparse,unquote
            name=str(args[0]);p=Path(unquote(urlparse(name).path) if name.startswith('file:') else name)
            if name!=':memory:' and not p.resolve().is_relative_to(Path('/private/tmp')):raise RuntimeError('Protected SQLite path')
    sys.addaudithook(guard)
    from tests.test_integration01_trade_shell import fixture
    from tests.test_lifecycle04_preparation import PNG
    from tests.test_lifecycle05_addresses import address
    from App.Database.migration_runner import migrate
    from services.trade_lifecycle_requests import LifecycleRequests
    from services.trade_lifecycle_acceptance import LifecycleAcceptance
    from services.trade_lifecycle_preparation import LifecyclePreparation
    from services.trade_lifecycle_addresses import LifecycleAddresses
    from services.smartdeal_optimizer import SmartDealPiece as Piece
    from tests.research.check_sap01 import configure
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    out=Path('/private/tmp/lifecycle05/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle05')
    def database(label):
        path=Path(temp.name)/(label+'.db');fixture(path)
        with closing(sqlite3.connect(path)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');migrate(db,27)
            t=LifecycleRequests(db).create(1,2,(Piece('vfl','1'),),(Piece('vfl','6'),),'offer')
            rev=db.execute('SELECT current_revision_id FROM lifecycle_contracts WHERE trade_id=?',(t,)).fetchone()[0]
            LifecycleAcceptance(db).accept(t,2,rev,'accept');prep=LifecyclePreparation(db)
            for user in (1,2):
                v=prep.view(t,user);prep.upload(t,user,rev,v['basis'],'photo',PNG,Path(temp.name)/'photos')
                prep.command(t,user,rev,v['basis'],'complete','complete')
            for user in (1,2):
                v=prep.view(t,user);prep.command(t,user,rev,v['basis'],'approve','approve')
            LifecycleAddresses(db).book_command(1,'existing','create',data=address('A'))
        return path,t
    path,trade=database('A');app=configure(path)
    app.app.config['LIFECYCLE_PHOTO_DIR']=str(Path(temp.name)/'photos')
    server=make_server('127.0.0.1',0,app.app,threaded=True);base=f'http://127.0.0.1:{server.server_port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();errors=[];results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();pages=[]
            for user in (1,2,3):
                c=browser.new_context(viewport={'width':390,'height':844})
                cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':user,'auth_version':1})
                c.add_cookies([dict(name='session',value=cookie,url=base)])
                p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));pages.append(p)
            a,b,c=pages
            def visit(p):p.goto(base+f'/tauschen/adressen/{trade}')
            def create(p,tag):
                p.goto(base+f'/tauschen/adressbuch?trade={trade}')
                form=p.locator('form[action="/tauschen/adressbuch/create"]')
                for field,value in address(tag).items():form.locator('[name="'+field+'"]').fill(value)
                form.get_by_role('button',name='Adresse speichern',exact=True).click();p.wait_for_url('**/tauschen/adressen/*')
            def confirm(p,index=0):
                p.get_by_role('button',name='Diese Adresse verbindlich bestätigen',exact=True).nth(index).click();p.wait_for_load_state()
            visit(a);a.screenshot(path=str(out/'A-selection.png'),full_page=True);confirm(a)
            assert a.locator('[data-address-state]').get_attribute('data-address-state')=='address_waiting'
            visit(b);assert 'Fixture Road A' not in b.content();b.screenshot(path=str(out/'A-partner-blind.png'),full_page=True)
            create(b,'B');confirm(b);visit(a)
            assert 'Fixture Road B' in a.locator('body').inner_text();assert 'Private B' not in a.content()
            assert 'Fixture Road A' in b.locator('body').inner_text()
            assert a.locator('[data-address-state]').get_attribute('data-address-state')=='ready_to_ship'
            assert a.get_by_role('button',name='Versendet',exact=True).count()==0
            a.screenshot(path=str(out/'A-released.png'),full_page=True);results.append('A: existing/new selection, blind waiting, bilateral release, no shipping controls')
            path,trade=database('B');app.DB=str(path);visit(a);confirm(a);create(a,'Replacement');confirm(a,1)
            visit(b);assert 'Fixture Road A' not in b.content();assert 'Fixture Road Replacement' not in b.content()
            create(b,'Partner');confirm(b)
            assert 'Fixture Road Replacement' in b.content();assert 'Fixture Road A' not in b.content()
            b.screenshot(path=str(out/'B-latest-only.png'),full_page=True);results.append('B: pre-release replacement, only latest snapshot disclosed')
            a.goto(base+'/tauschen/adressbuch')
            form=a.locator('form[action="/tauschen/adressbuch/edit"]').nth(1)
            form.locator('[name=street]').fill('Changed synthetic street');form.get_by_role('button',name='Änderungen speichern',exact=True).click()
            visit(b);assert 'Fixture Road Replacement' in b.content();assert 'Changed synthetic street' not in b.content()
            b.screenshot(path=str(out/'C-snapshot-stable.png'),full_page=True);results.append('C: address-book edit leaves released snapshot unchanged')
            with closing(sqlite3.connect(path)) as db:
                released=db.execute('SELECT requester_snapshot_id FROM lifecycle_address_releases').fetchone()[0]
                payloads=json.dumps(db.execute('SELECT payload_json FROM trade_events').fetchall())+json.dumps(db.execute('SELECT title,body FROM notifications').fetchall())
                assert 'Fixture Road' not in payloads and 'Private Replacement' not in payloads
            for url in (f'/tauschen/adressen/{trade}',f'/tauschen/adressen/{trade}/snapshots/{released}',f'/tauschen/adressen/999/snapshots/{released}'):
                response=c.goto(base+url);assert response.status==404;assert 'Fixture Road' not in c.content()
            c.goto(base+'/tauschen/adressbuch?user_id=1');assert 'Fixture Road' not in c.content()
            results.append('D: third-party and manipulated direct routes denied; no address in events/notifications')
            for width in (375,390,430,1280):
                a.set_viewport_size(dict(width=width,height=900));visit(a)
                assert a.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                a.screenshot(path=str(out/f'released-{width}.png'),full_page=True)
            assert not errors,errors
            browser.close()
    finally:server.shutdown();thread.join();temp.cleanup()
    (out/'results.json').write_text(json.dumps(dict(flows=results,js_errors=errors,widths=[375,390,430,1280]),indent=2))
    print(json.dumps(results))

if __name__=='__main__':main()
