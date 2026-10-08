"""Four authenticated browser flows, exclusively synthetic /private/tmp data."""
from pathlib import Path
import io,json,sqlite3,sys,tempfile,threading
from contextlib import closing
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]


def main():
    if not ROOT.is_relative_to(Path('/private/tmp')):raise RuntimeError('Isolated source checkout required')
    def guard(event,args):
        if event=='sqlite3.connect':
            from urllib.parse import urlparse,unquote
            name=str(args[0]);p=Path(unquote(urlparse(name).path) if name.startswith('file:') else name)
            if name!=':memory:' and not p.resolve().is_relative_to(Path('/private/tmp')):raise RuntimeError('Protected SQLite path')
    sys.addaudithook(guard)
    from tests.test_integration01_trade_shell import fixture
    from App.Database.migration_runner import migrate
    from services.trade_lifecycle_requests import LifecycleRequests
    from services.trade_lifecycle_acceptance import LifecycleAcceptance
    from services.smartdeal_optimizer import SmartDealPiece as Piece
    from tests.research.check_sap01 import configure
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    from PIL import Image,ImageDraw
    image=Image.new('RGB',(600,400),'#ddd6be');draw=ImageDraw.Draw(image)
    for i in range(6):
        x=30+(i%3)*190;y=25+(i//3)*185
        draw.rectangle((x,y,x+160,y+150),fill='#faf7ee',outline='black',width=2)
        draw.text((x+15,y+25),'SYNTHETIC\nCONTROL PHOTO\nSticker '+str(i+1),fill='black')
    blob=io.BytesIO();image.save(blob,format='PNG');picture=blob.getvalue()
    out=Path('/private/tmp/lifecycle04/browser');out.mkdir(exist_ok=True)
    temp=tempfile.TemporaryDirectory(prefix='browser-',dir='/private/tmp/lifecycle04')
    def database(label,quantity=1):
        path=Path(temp.name)/(label+'.db');fixture(path)
        with closing(sqlite3.connect(path)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');migrate(db,26)
            for user,code,need in ((1,'1','6'),(2,'6','1')):
                db.execute('UPDATE stickers SET quantity=?,duplicates=? WHERE user_id=? AND sticker_code=?',(quantity+1,quantity,user,code))
                db.execute("INSERT INTO lifecycle_need_targets VALUES (?,'vfl',?,?)",(user,need,quantity))
            db.commit()
            t=LifecycleRequests(db).create(1,2,(Piece('vfl','1',quantity),),(Piece('vfl','6',quantity),),'browser')
            rev=db.execute('SELECT current_revision_id FROM lifecycle_contracts WHERE trade_id=?',(t,)).fetchone()[0]
            LifecycleAcceptance(db).accept(t,2,rev,'accept')
        return path,t
    path,trade=database('A');app=configure(path)
    app.app.config['LIFECYCLE_PHOTO_DIR']=str(Path(temp.name)/'photos')
    server=make_server('127.0.0.1',0,app.app,threaded=True);base=f'http://127.0.0.1:{server.server_port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();errors=[];results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();pages=[]
            for user in (1,2):
                c=browser.new_context(viewport={'width':390,'height':844})
                cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':user,'auth_version':1})
                c.add_cookies([dict(name='session',value=cookie,url=base)])
                p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));pages.append(p)
            a,b=pages
            def visit(p):p.goto(base+f'/tauschen/vorbereitung/{trade}')
            def upload(p):
                form=p.locator('form[action$="/upload"]').first
                form.locator('input[type=file]').set_input_files(dict(name='synthetic.png',mimeType='image/png',buffer=picture))
                form.get_by_role('button',name='Foto hochladen',exact=True).click();p.wait_for_load_state()
            def complete(p):p.get_by_role('button',name='Vorbereitung abschließen',exact=True).click();p.wait_for_load_state()
            def both():
                for p in (a,b):visit(p);upload(p);complete(p)
                for p in (a,b):visit(p)
            def approved():
                for p in (a,b):visit(p);p.get_by_role('button',name='Alles passt',exact=True).click();p.wait_for_load_state()
                visit(a);assert a.locator('[data-preparation-state]').get_attribute('data-preparation-state')=='ready_for_address_release'
                assert a.locator('input[name*=address],input[name*=shipping]').count()==0
            visit(a);upload(a);complete(a);visit(b)
            assert b.locator('img[src*="/fotos/"]').count()==0
            b.screenshot(path=str(out/'A-blind.png'),full_page=True)
            upload(b);complete(b);visit(a)
            assert a.locator('img[src*="/fotos/"]').count()==2
            a.screenshot(path=str(out/'A-reveal.png'),full_page=True);approved()
            a.screenshot(path=str(out/'A-ready.png'),full_page=True);results.append('A: own packlists, blind barrier, reveal, bilateral review, ready without addresses')
            path,trade=database('B');app.DB=str(path);both()
            a.locator('select[name=reason]').select_option('NOT_RECOGNIZABLE');a.get_by_role('button',name='Problem melden',exact=True).click()
            visit(b);b.screenshot(path=str(out/'B-problem.png'),full_page=True)
            b.get_by_role('button',name='Fotokorrektur beginnen',exact=True).click();upload(b);complete(b);approved()
            a.screenshot(path=str(out/'B-corrected-ready.png'),full_page=True);results.append('B: structured photo problem, new frozen package and fresh review')
            path,trade=database('C',23);app.DB=str(path);visit(a)
            a.get_by_role('button',name='Fehlmenge verbindlich melden',exact=True).click()
            for control in a.locator('input[name^="quantity_"]').all():control.fill('22')
            a.get_by_role('button',name='Reduzierten Deal vorschlagen',exact=True).click();visit(b)
            assert b.locator('body').inner_text().count('23 → 22')==2
            b.screenshot(path=str(out/'C-reduction-review.png'),full_page=True)
            b.get_by_role('button',name='Reduktion zustimmen',exact=True).click()
            with closing(sqlite3.connect(path)) as db:
                assert db.execute("SELECT SUM(quantity) FROM trade_reservations WHERE state='active'").fetchone()[0]==44
                assert db.execute('SELECT quantity,overlap_quantity,resolved_at FROM physical_missing_holds').fetchone()==(1,0,None)
                assert db.execute('SELECT SUM(quantity) FROM lifecycle_revision_positions WHERE revision_id=1').fetchone()[0]==46
            both();approved();a.screenshot(path=str(out/'C-reduced-ready.png'),full_page=True);results.append('C: 23→22, bilateral activation, missing quarantine retained, new photos/reviews')
            path,trade=database('D',23);app.DB=str(path);visit(a)
            for control in a.locator('input[name^="quantity_"]').all():control.fill('22')
            a.get_by_role('button',name='Reduzierten Deal vorschlagen',exact=True).click();visit(b)
            b.get_by_role('button',name='Reduktion ablehnen',exact=True).click();visit(a)
            assert a.locator('[data-preparation-state]').get_attribute('data-preparation-state')=='reduction_rejected'
            with closing(sqlite3.connect(path)) as db:assert db.execute("SELECT SUM(quantity) FROM trade_reservations WHERE state='active'").fetchone()[0]==46
            a.screenshot(path=str(out/'D-rejected.png'),full_page=True);results.append('D: rejection retains original binding, no cancel or address release')
            for width in (375,390,430,1280):
                a.set_viewport_size(dict(width=width,height=900));visit(a)
                assert a.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                a.screenshot(path=str(out/f'D-{width}.png'),full_page=True)
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown();thread.join();temp.cleanup()
    (out/'results.json').write_text(json.dumps(dict(flows=results,js_errors=errors,widths=[375,390,430,1280]),indent=2))
    print(json.dumps(results))

if __name__=='__main__':main()
