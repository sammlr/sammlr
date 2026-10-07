"""Real browser request journey; isolated source checkout and synthetic DB only."""
from pathlib import Path
import json,os,sqlite3,sys,tempfile,threading
from contextlib import closing
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]


def main():
    if not ROOT.is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Run only in synthetic source checkout under /private/tmp')
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
    out=Path('/private/tmp/lifecycle02/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle02')
    path=Path(temp.name)/'synthetic.db';fixture(path)
    with closing(sqlite3.connect(path)) as db:migrate(db,24)
    app=configure(path)
    server=make_server('127.0.0.1',0,app.app,threaded=True)
    base=f'http://127.0.0.1:{server.server_port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    errors=[];results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            contexts=[]
            for user in (1,2):
                context=browser.new_context(viewport={'width':390,'height':844})
                cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':user,'auth_version':1})
                context.add_cookies([dict(name='session',value=cookie,url=base)])
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                contexts.append((context,page))
            sender=contexts[0][1];recipient=contexts[1][1]
            sender.goto(base+'/tauschen/sammlr/2/smartdeal')
            sender.get_by_role('button',name='Tausch anfragen',exact=True).click()
            sender.wait_for_url('**/tauschen/anfragen/*')
            request_url=sender.url
            assert 'Anfrage offen' in sender.locator('body').inner_text()
            assert '72 Stunden' in sender.locator('body').inner_text()
            sender.screenshot(path=str(out/'01-sender-open.png'),full_page=True)
            recipient.goto(base+'/tauschen/laufend')
            assert 'Anfrage von synthetic_1' in recipient.locator('body').inner_text()
            assert recipient.get_by_role('button',name='Annehmen').count()==0
            recipient.screenshot(path=str(out/'02-recipient-open.png'),full_page=True)
            recipient.get_by_role('button',name='Anfrage ablehnen',exact=True).click()
            recipient.wait_for_url('**/tauschen/anfragen/*')
            assert 'Anfrage abgelehnt' in recipient.locator('body').inner_text()
            sender.goto(request_url);assert 'Anfrage abgelehnt' in sender.locator('body').inner_text()
            results.append('SmartDeal send / recipient reject / released deal available')
            sender.goto(base+'/tauschen/sammlr/2/manual');sender.wait_for_function('document.body.dataset.ready==="true"')
            sender.locator('.sticker-list-item[data-side="receive"]').first.click()
            sender.locator('.sticker-list-item[data-side="give"]').first.click()
            sender.locator('#manual-review').click();sender.wait_for_url('**/tauschen/anfragen/entwurf?*')
            sender.get_by_role('button',name='Tausch anfragen',exact=True).click()
            sender.wait_for_url('**/tauschen/anfragen/*')
            sender.get_by_role('button',name='Anfrage zurückziehen',exact=True).click()
            assert 'Anfrage zurückgezogen' in sender.locator('body').inner_text()
            sender.screenshot(path=str(out/'03-manual-withdrawn.png'),full_page=True)
            results.append('Manual selection / review / send / withdraw')
            from datetime import datetime,timedelta,timezone
            from services.trade_lifecycle_requests import LifecycleRequests
            from services.smartdeal_optimizer import SmartDealPiece
            with closing(sqlite3.connect(path)) as db:
                db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
                service=LifecycleRequests(db,lambda:datetime.now(timezone.utc)-timedelta(hours=73))
                expired=service.create(1,2,(SmartDealPiece('vfl','1'),),(SmartDealPiece('vfl','6'),),'browser-expiry')
            sender.goto(base+f'/tauschen/anfragen/{expired}')
            assert 'Anfrage abgelaufen' in sender.locator('body').inner_text()
            assert sender.get_by_role('button',name='Anfrage zurückziehen').count()==0
            sender.goto(base+'/tauschen/sammlr/2/smartdeal')
            assert sender.get_by_role('button',name='Tausch anfragen',exact=True).count()==1
            results.append('Lazy expiry visible / no terminal action / full deal available again')
            for width in (375,390,430,1280):
                sender.set_viewport_size({'width':width,'height':900})
                sender.goto(base+'/tauschen/laufend')
                assert sender.evaluate('document.documentElement.scrollWidth<=innerWidth')
                sender.screenshot(path=str(out/f'04-requests-{width}.png'),full_page=True)
            results.append('No horizontal overflow at 375/390/430/1280')
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown();thread.join();temp.cleanup()
    (out/'results.json').write_text(json.dumps(dict(passed=results,errors=errors),indent=2)+'\n')
    print(json.dumps(results))

if __name__=='__main__':main()
