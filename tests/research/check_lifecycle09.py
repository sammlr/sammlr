"""Completion, final problems and blind ratings, synthetic DBs only, four responsive widths."""
from pathlib import Path
import json,sqlite3,sys,tempfile,threading
from datetime import datetime,timezone,timedelta
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
    from services.trade_lifecycle_shipping import LifecycleShipping
    from services.trade_lifecycle_addresses import LifecycleAddresses
    from services.inventory_write import InventoryWriteService
    from services.smartdeal_optimizer import SmartDealPiece as Piece
    from tests.research.check_sap01 import configure
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    out=Path('/private/tmp/lifecycle09/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle09')
    def database(label,n=1,systemic=False,late=False,pending=False):
        path=Path(temp.name)/(label+'.db');fixture(path)
        with closing(sqlite3.connect(path)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');migrate(db,30)
            for owner,code in ((1,'1'),(2,'6')):InventoryWriteService(db).set_quantity(owner,'vfl',code,n+1)
            for owner,code in ((2,'1'),(1,'6')):db.execute('INSERT INTO lifecycle_need_targets VALUES (?,\'vfl\',?,?)',(owner,code,n))
            db.commit();now=datetime.now(timezone.utc)-(timedelta(days=22) if late else timedelta())
            t=LifecycleRequests(db,lambda:now).create(1,2,(Piece('vfl','1',n),),(Piece('vfl','6',n),),'offer')
            rev=db.execute('SELECT current_revision_id FROM lifecycle_contracts WHERE trade_id=?',(t,)).fetchone()[0]
            if pending:return path,t
            LifecycleAcceptance(db,lambda:now).accept(t,2,rev,'accept')
            prep=LifecyclePreparation(db,lambda:now)
            for user in (1,2):
                v=prep.view(t,user);prep.upload(t,user,rev,v['basis'],'photo',PNG,Path(temp.name)/'photos')
                prep.command(t,user,rev,v['basis'],'complete','complete')
            for user in (1,2):
                v=prep.view(t,user);prep.command(t,user,rev,v['basis'],'approve','approve')
            a=LifecycleAddresses(db,lambda:now)
            for user in (1,2):
                entry=a.book_command(user,'book','create',data=address(str(user)))['address'];v=a.view_address(t,user)
                a.confirm(t,user,rev,v['basis'],v['generation'],entry,1,'address')
            if not systemic:LifecycleShipping(db,lambda:now).send_direction(t,1,rev,'sent')
        return path,t
    from services.trade_lifecycle_completion import LifecycleCompletion
    path,trade=database('pending',pending=True);app=configure(path)
    server=make_server('127.0.0.1',0,app.app,threaded=True);base=f'http://127.0.0.1:{server.server_port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();errors=[];results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();pages=[]
            for user in (1,2,3):
                context=browser.new_context(viewport={'width':390,'height':900})
                cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':user,'auth_version':1})
                context.add_cookies([dict(name='session',value=cookie,url=base)])
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));pages.append(page)
            sender,receiver,foreign=pages
            def check(page,label,center=True):
                for width in (375,390,430,1280):
                    page.set_viewport_size(dict(width=width,height=900))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(label,width)
                    if center:
                        assert page.locator('.center-actions a,.center-all,.center-links a,.center-pagination a').evaluate_all('(els)=>els.every(e=>e.getBoundingClientRect().height>=44)')
                        page.evaluate('scrollTo(0,document.documentElement.scrollHeight)')
                        assert page.evaluate('''()=>{let a=[...document.querySelectorAll('.center-all,.center-detail,.center-pagination a')].at(-1),n=document.querySelector('.bottom-nav');return !a||!n||getComputedStyle(n).display==='none'||a.getBoundingClientRect().bottom<=n.getBoundingClientRect().top}'''),label
                        page.evaluate('scrollTo(0,0)')
                    page.screenshot(path=str(out/f'{label}-{width}.png'),full_page=True)
                results.append(label)
            receiver.goto(base+'/tauschen/laufend');assert receiver.locator('[data-status=open]').count()==1
            receiver.goto(base+f'/tauschen/anfragen/{trade}')
            receiver.get_by_role('button',name='Annehmen',exact=True).click()
            assert f'/tauschen/vorbereitung/{trade}' in receiver.url
            receiver.set_viewport_size(dict(width=390,height=900))
            receiver.locator('.bottom-nav a[href="/zentrale"]').click();check(receiver,'A-navigation-B-todos')
            assert receiver.locator('[data-action=prepare]').count()>=1
            receiver.locator('[data-action=prepare]').first.click();check(receiver,'E-preparation-deep-link',False)
            receiver.goto(base+'/tauschen/laufend');assert receiver.locator('[data-status=accepted]').count()==0
            sender.goto(base+'/zentrale/sendungen');check(sender,'C-sendungen')
            receiver.goto(base+'/zentrale/eingaenge');check(receiver,'D-eingaenge')
            path,trade=database('complete');app.DB=str(path)
            def receive(page):
                page.goto(base+f'/tauschen/empfang/{trade}')
                page.get_by_role('button',name='Alles angekommen',exact=True).click()
                page.get_by_role('button',name='Empfang verbindlich buchen',exact=True).click()
            receive(receiver);receive(sender)
            sender.goto(base+'/zentrale');check(sender,'G-archived-H-rating-todo')
            assert sender.locator('.center-sendungen [data-trade]').count()==0
            assert sender.locator('.center-eingaenge [data-trade]').count()==0
            sender.locator('[data-action=rate]').click()
            sender.select_option('[name=stars]','4');sender.check('[value=well_packed]')
            sender.get_by_role('button',name='Bewertung verbindlich abgeben',exact=True).click()
            receiver.goto(base+'/zentrale/archiv');check(receiver,'I-blind-archive')
            assert '4 von 5 Sternen' not in receiver.content()
            receiver.locator('.center-detail').click();assert '4 von 5 Sternen' not in receiver.content()
            receiver.select_option('[name=stars]','5');receiver.get_by_role('button',name='Bewertung verbindlich abgeben',exact=True).click()
            assert receiver.locator('[data-visible-rating]').count()==2;check(receiver,'I-revealed-detail',False)
            assert foreign.goto(base+f'/tauschen/abschluss/{trade}').status==404
            path,trade=database('many');app.DB=str(path)
            with closing(sqlite3.connect(path)) as db:
                db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
                for owner,code in ((1,'1'),(2,'6')):InventoryWriteService(db).set_quantity(owner,'vfl',code,40)
                db.execute('UPDATE lifecycle_need_targets SET quantity=40');db.commit()
                for i in range(29):
                    t=LifecycleRequests(db).create(1,2,(Piece('vfl','1',1),),(Piece('vfl','6',1),),'many-'+str(i))
                    rev=db.execute('SELECT current_revision_id FROM lifecycle_contracts WHERE trade_id=?',(t,)).fetchone()[0]
                    LifecycleAcceptance(db).accept(t,2,rev,'accept-many')
            sender.goto(base+'/zentrale');check(sender,'J-many-preview')
            assert sender.locator('.center-sendungen [data-trade]').count()==3
            sender.goto(base+'/zentrale/sendungen');check(sender,'J-pagination-first')
            first=sender.locator('[data-trade]').evaluate_all('(els)=>els.map(e=>e.dataset.trade)');assert len(first)==12
            sender.get_by_role('link',name='Weiter',exact=True).click();check(sender,'J-pagination-second')
            second=sender.locator('[data-trade]').evaluate_all('(els)=>els.map(e=>e.dataset.trade)');assert len(second)==12 and not set(first)&set(second)
            assert not errors,errors
            browser.close()
    finally:server.shutdown();thread.join();temp.cleanup()
    report=dict(flows=results,js_errors=errors,widths=[375,390,430,1280])
    (out/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
