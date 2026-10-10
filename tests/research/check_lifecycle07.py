"""Seven real receipt flows, synthetic DBs only, four responsive widths."""
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
    out=Path('/private/tmp/lifecycle07-final/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle07')
    def database(label,n=1,systemic=False,late=False):
        path=Path(temp.name)/(label+'.db');fixture(path)
        with closing(sqlite3.connect(path)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');migrate(db,29)
            for owner,code in ((1,'1'),(2,'6')):InventoryWriteService(db).set_quantity(owner,'vfl',code,n+1)
            for owner,code in ((2,'1'),(1,'6')):db.execute('INSERT INTO lifecycle_need_targets VALUES (?,\'vfl\',?,?)',(owner,code,n))
            db.commit();now=datetime.now(timezone.utc)-(timedelta(days=8) if late else timedelta())
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
    path,trade=database('A');app=configure(path)
    app.app.config['LIFECYCLE_PHOTO_DIR']=str(Path(temp.name)/'photos')
    server=make_server('127.0.0.1',0,app.app,threaded=True);base=f'http://127.0.0.1:{server.server_port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();errors=[];results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();pages=[]
            for user in (1,2,3):
                context=browser.new_context(viewport={'width':390,'height':844})
                cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':user,'auth_version':1})
                context.add_cookies([dict(name='session',value=cookie,url=base)])
                p=context.new_page();p.on('pageerror',lambda e:errors.append(str(e)));pages.append(p)
            sender,receiver,foreign=pages
            def check(p,label):
                for width in (375,390,430,1280):
                    p.set_viewport_size(dict(width=width,height=900))
                    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),(label,width)
                    p.screenshot(path=str(out/f'{label}-{width}.png'),full_page=True)
            def visit():receiver.goto(base+f'/tauschen/empfang/{trade}')
            def confirm():
                receiver.get_by_role('button',name='Empfang verbindlich buchen',exact=True).click()
                receiver.wait_for_load_state()
            for label,n,fields in [('A',1,None),('B',3,{'correct':2,'missing':1}),
                                    ('C',1,{'damaged_accepted':1}),('D',1,{'wrong':1,'wrong_code':'2'}),
                                    ('E',1,None),('F',1,None)]:
                if label!='A':path,trade=database(label,n,systemic=label=='F',late=label=='E');app.DB=str(path)
                visit();check(receiver,label+'-start')
                if label=='E':
                    receiver.get_by_role('button',name='Brief nicht angekommen',exact=True).click()
                    check(receiver,'E-nonarrival');receiver.get_by_text('Doch angekommen',exact=True).click()
                if fields:
                    receiver.get_by_role('button',name='Problem mit Lieferung',exact=True).click();check(receiver,label+'-inspect')
                    for k,value in fields.items():receiver.locator(f'[name^="{k}_"]').first.fill(str(value))
                    receiver.get_by_role('button',name='Zusammenfassung prüfen',exact=True).click()
                else:receiver.get_by_role('button',name='Alles angekommen',exact=True).click()
                check(receiver,label+'-confirm')
                with closing(sqlite3.connect(path)) as db:assert db.execute('SELECT COUNT(*) FROM lifecycle_receipts').fetchone()[0]==0
                confirm();check(receiver,label+'-booked')
                with closing(sqlite3.connect(path)) as db:
                    quantity=db.execute("SELECT quantity FROM stickers WHERE user_id=2 AND album_id='vfl' AND sticker_code='1'").fetchone()
                    assert (quantity[0] if quantity else 0)==(2 if label=='B' else 0 if label=='D' else n)
                    assert db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0]=='accepted'
                    if label=='F':assert db.execute('SELECT source,sender_confirmed_at FROM lifecycle_shipping').fetchone()==('RECEIPT_EVIDENCE',None)
                    if label=='E':assert db.execute("SELECT COUNT(*) FROM trade_events WHERE event_type IN ('NonArrivalReported','LateArrivalReported')").fetchone()[0]==2
                if label=='F':
                    receiver.goto(base+f'/tauschen/versand/{trade}')
                    receiver.get_by_role('button',name='Versendet',exact=True).click()
                    receiver.get_by_role('button',name='Ja, versendet',exact=True).click()
                    check(receiver,'H-counter-sent')
                    sender.goto(base+f'/tauschen/empfang/{trade}')
                    sender.get_by_role('button',name='Alles angekommen',exact=True).click()
                    check(sender,'H-counter-confirm')
                    sender.get_by_role('button',name='Empfang verbindlich buchen',exact=True).click()
                    check(sender,'H-both-received')
                    with closing(sqlite3.connect(path)) as db:
                        assert db.execute("SELECT COUNT(*) FROM lifecycle_directions WHERE receipt_state='received_complete'").fetchone()[0]==2
                        assert db.execute('SELECT state FROM lifecycle_contracts').fetchone()[0]=='accepted'
                        assert db.execute("SELECT COUNT(*) FROM lifecycle_movements WHERE movement_kind='debit'").fetchone()[0]==2
                        assert db.execute("SELECT COUNT(*) FROM lifecycle_movements WHERE movement_kind='credit'").fetchone()[0]==2
                    results.append('H-counter-direction')
                results.append(label)
                if label=='B':
                    sender.goto(base+f'/tauschen/empfang/{trade}');sender.get_by_role('button',name='Problem anerkennen',exact=True).click()
                    check(sender,'G-response');assert 'Problem anerkannt' in sender.locator('body').inner_text();results.append('G')
            assert foreign.goto(base+f'/tauschen/empfang/{trade}').status==404
            assert not errors,errors
            browser.close()
    finally:server.shutdown();thread.join();temp.cleanup()
    (out/'results.json').write_text(json.dumps(dict(flows=results,js_errors=errors,widths=[375,390,430,1280]),indent=2))
    print(json.dumps(results))

if __name__=='__main__':main()
