"""SAP-02 responsive acceptance; only SQL-generated synthetic fixtures."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]
from tests.research import check_sap01 as sap
from tests.research import check_profile_trade01 as profile
BASE=sap.BASE
OUT=ROOT/'tests/research/artifacts/sap-02'


def check(path):
    from playwright.sync_api import sync_playwright
    sap.OUT=OUT/'sap-regression';sap.check(path,17)
    profile.OUT=OUT/'profile-regression';profile.main(path)
    app=sap.configure(path)
    cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':1,'auth_version':1})
    before=hashlib.sha256(path.read_bytes()).hexdigest();results=[];errors=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch()
        for width in (375,390,430,1280):
            c=b.new_context(viewport={'width':width,'height':900});c.add_cookies([dict(name='session',value=cookie,url=BASE)])
            p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
            def go(url):
                assert p.goto(BASE+url).status==200;p.evaluate('document.fonts.ready')
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            go('/tauschen')
            assert p.locator('.trade-stage').count()==0
            assert p.get_by_role('link',name='Alle Sammlr',exact=True).count()==0
            assert p.locator('input[type=search]').count()==1
            p.screenshot(path=str(OUT/f'sap-{width}.png'),full_page=False)
            p.locator('summary').click()
            boxes=p.locator('.sap-albums label').evaluate_all('(es)=>es.map(e=>{let r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})')
            assert len(boxes)==17
            assert all(44<=r['h']<=80 and r['w']>(width*.65 if width<500 else 400) for r in boxes),boxes
            assert p.locator('.sap-albums input').evaluate_all('(es)=>es.every(e=>e.getBoundingClientRect().width<=24)')
            assert all(boxes[i+1]['y']>=boxes[i]['y']+boxes[i]['h'] for i in range(16))
            p.screenshot(path=str(OUT/f'albums17-{width}.png'),full_page=True)
            p.screenshot(path=str(OUT/f'albums-open-{width}.png'),full_page=False)
            for count in (1,5,17):
                albums=['vfl','wm26','em24']+[f'fixture{i}' for i in range(4,18)]
                go('/tauschen?filtered=1'+''.join('&album='+a for a in albums[:count]))
                assert p.locator('[name=album]:checked').count()==count
                assert p.locator('.sap-results a').count()>0
            for query in ('@Demo%20Jens','wm26','WM26%20POR17','POR17%20GER14%20ARG3'):
                go('/tauschen?q='+query);assert p.locator('.sap-results a').count()>0
            go('/profil/Demo%20Jens')
            p.locator('.profile-trade summary').click()
            assert p.locator('.profile-trade form label').evaluate_all('(es)=>es.every(e=>e.getBoundingClientRect().height<=80)')
            go('/tauschen/sammlr/2/manual')
            p.wait_for_function('document.body.dataset.ready==="true"')
            note=p.locator('.sticker-list-tradebar')
            for pos in (0,400,100000):
                p.evaluate('(y)=>window.scrollTo(0,y)',pos)
                assert note.evaluate('e=>{let r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth}')
                assert p.locator('#manual-review').evaluate('e=>{let r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}')
            p.screenshot(path=str(OUT/f'manual-sticky-{width}.png'),full_page=False)
            results.append(dict(width=width,one_five_seventeen=True,album_rows=17,touch_targets=True,sticky_positions=3,no_overflow=True,search_types=True))
            c.close()
        b.close()
    assert not errors,errors
    assert before==hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(dict(results=results,errors=errors,database_unchanged=True),indent=2)+'\n')
    print('PASS SAP-02 four widths, 17 albums, search, sticky, read-only')


if __name__=='__main__':
    path=Path(sys.argv[2])
    if sys.argv[1]=='serve':sap.serve(path,17)
    else:check(path)
