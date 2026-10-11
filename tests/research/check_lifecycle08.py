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
    out=Path('/private/tmp/lifecycle08/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle08')
    def database(label,n=1,systemic=False,late=False):
        path=Path(temp.name)/(label+'.db');fixture(path)
        with closing(sqlite3.connect(path)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');migrate(db,30)
            for owner,code in ((1,'1'),(2,'6')):InventoryWriteService(db).set_quantity(owner,'vfl',code,n+1)
            for owner,code in ((2,'1'),(1,'6')):db.execute('INSERT INTO lifecycle_need_targets VALUES (?,\'vfl\',?,?)',(owner,code,n))
            db.commit();now=datetime.now(timezone.utc)-(timedelta(days=22) if late else timedelta())
            t=LifecycleRequests(db,lambda:now).create(1,2,(Piece('vfl','1',n),),(Piece('vfl','6',n),),'offer')
            rev=db.execute('SELECT current_revision_id FROM lifecycle_contracts WHERE trade_id=?',(t,)).fetchone()[0]
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
    from services.trade_lifecycle_foundation import lifecycle_availability
    path,trade=database('complete');app=configure(path)
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
            def check(page,label):
                for width in (375,390,430,1280):
                    page.set_viewport_size(dict(width=width,height=900))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(label,width)
                    page.screenshot(path=str(out/f'{label}-{width}.png'),full_page=True)
                results.append(label)
            def visit(page):page.goto(base+f'/tauschen/abschluss/{trade}')
            def receive(page,partial=False):
                page.goto(base+f'/tauschen/empfang/{trade}')
                if partial:
                    page.get_by_role('button',name='Problem mit Lieferung',exact=True).click()
                    page.locator('[name^="correct_"]').first.fill('2')
                    page.locator('[name^="missing_"]').first.fill('1')
                    page.get_by_role('button',name='Zusammenfassung prüfen',exact=True).click()
                else:page.get_by_role('button',name='Alles angekommen',exact=True).click()
                page.get_by_role('button',name='Empfang verbindlich buchen',exact=True).click()
                page.wait_for_load_state()
            receive(receiver);visit(receiver);check(receiver,'one-direction-rating-eligible')
            receiver.select_option('[name=stars]','4');receiver.check('[value=well_packed]')
            receiver.get_by_role('button',name='Bewertung verbindlich abgeben',exact=True).click()
            visit(sender);assert sender.locator('[data-visible-rating]').count()==0
            assert '4 von 5 Sternen' not in sender.content();check(sender,'blind-rating')
            receive(sender);visit(sender);check(sender,'automatic-completion')
            assert 'Tausch erfolgreich abgeschlossen' in sender.locator('body').inner_text()
            sender.select_option('[name=stars]','5')
            sender.get_by_role('button',name='Bewertung verbindlich abgeben',exact=True).click()
            assert sender.locator('[data-visible-rating]').count()==2;check(sender,'both-ratings-revealed')
            assert foreign.goto(base+f'/tauschen/abschluss/{trade}').status==404
            path,trade=database('partial',3);app.DB=str(path)
            receive(sender);receive(receiver,partial=True);visit(receiver);check(receiver,'partial-problem')
            receiver.get_by_role('button',name='Problem akzeptieren und Empfang abschließen',exact=True).click()
            check(receiver,'problem-confirmation')
            receiver.get_by_role('button',name='Ja, endgültig abschließen',exact=True).click();check(receiver,'problem-completion')
            with closing(sqlite3.connect(path)) as db:
                db.row_factory=sqlite3.Row
                a=lifecycle_availability(db,2,'vfl','1');assert (a.physical,a.committed,a.free_need)==(2,0,1)
                assert db.execute('SELECT outcome FROM lifecycle_completions').fetchone()[0]=='closed_with_problem'
            path,trade=database('nonarrival',late=True);app.DB=str(path)
            with closing(sqlite3.connect(path)) as db:
                db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
                now=datetime.now(timezone.utc)-timedelta(days=15)
                rev=db.execute('SELECT accepted_revision_id FROM lifecycle_contracts').fetchone()[0]
                service=LifecycleCompletion(db,lambda:now)
                problem=service.report_non_arrival(trade,2,1,rev,'not-arrived')['problem']
                service.respond(trade,1,1,rev,problem,'sent_correctly','response')
            receive(sender);visit(receiver);check(receiver,'after-fourteen-days')
            assert receiver.get_by_role('button',name='Problem akzeptieren und Empfang abschließen',exact=True).count()==0
            receiver.get_by_role('button',name='Problem endgültig abschließen',exact=True).click()
            assert 'später auftauchender Brief' in receiver.locator('body').inner_text()
            check(receiver,'nonarrival-warning')
            receiver.get_by_role('button',name='Ja, endgültig abschließen',exact=True).click();check(receiver,'nonarrival-completed')
            assert receiver.locator('[name=stars]').count()==1
            with closing(sqlite3.connect(path)) as db:
                db.row_factory=sqlite3.Row
                db.execute('PRAGMA foreign_keys=ON')
                assert lifecycle_availability(db,2,'vfl','1').physical==0
                assert db.execute('SELECT COUNT(*) FROM lifecycle_receipts WHERE from_user_id=1').fetchone()[0]==0
                assert db.execute('SELECT outcome FROM lifecycle_completions').fetchone()[0]=='closed_with_problem'
                try:LifecycleCompletion(db).confirm_receipt(trade,2,1,rev,'late',None)
                except ValueError:pass
                else:raise AssertionError('Final nonarrival accepted late receipt')
            assert not errors,errors
            browser.close()
    finally:server.shutdown();thread.join();temp.cleanup()
    report=dict(flows=results,js_errors=errors,widths=[375,390,430,1280])
    (out/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
