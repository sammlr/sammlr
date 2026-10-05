"""Profile → existing auto/manual paths, real application on synthetic fixtures."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'App')]
from tests.research.check_sap01 import configure
BASE='http://127.0.0.1:18081'
OUT=ROOT/'tests/research/artifacts/profile-trade-01'


def main(path):
    from playwright.sync_api import sync_playwright
    app=configure(path);cookie=app.app.session_interface.get_signing_serializer(app.app).dumps({'user_id':1,'auth_version':1})
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True);results=[];errors=[];posts=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch()
        for width in (375,390,430,1280):
            c=b.new_context(viewport={'width':width,'height':900});c.add_cookies([dict(name='session',value=cookie,url=BASE)])
            p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
            p.on('response',lambda r:errors.append(str(r.status)+' '+r.url) if r.status>=400 else None)
            p.on('request',lambda r:posts.append(r.url) if r.method=='POST' else None)
            def go(url):
                assert p.goto(BASE+url).status==200;p.evaluate('document.fonts.ready')
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            go('/tauschen/sammlr?filtered=1&album=wm26&q=Demo+Jens')
            row=p.locator('.sap-results a').first
            assert '3 Sticker' in row.inner_text();row.click()
            assert '/profil/Demo%20Jens?' in p.url
            assert p.locator('.profile-trade-potential').inner_text()=='Bis zu 3 Sticker · 1 Album'
            assert p.locator('.collector-showcase-album-grid a').count()==3
            assert '/album/vfl' in ' '.join(p.locator('.collector-showcase-album-grid a').evaluate_all('(es)=>es.map(e=>e.href)'))
            p.screenshot(path=str(OUT/f'filtered-profile-{width}.png'),full_page=True)
            go('/profil/Demo%20Jens')
            assert '8 Sticker' in p.locator('.profile-trade-potential').inner_text()
            p.screenshot(path=str(OUT/f'profile-{width}.png'),full_page=True)
            auto=p.get_by_role('link',name='Besten Tausch zusammenstellen');auto.scroll_into_view_if_needed()
            assert auto.evaluate('e=>{let r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}')
            auto.click();assert '/tauschen/sammlr/2/smartdeal' in p.url
            assert p.locator('.trade-group').count()>0
            p.screenshot(path=str(OUT/f'auto-{width}.png'),full_page=True)
            go('/profil/Demo%20Jens')
            p.get_by_role('link',name='Selbst zusammenstellen').click();p.wait_for_function('document.body.dataset.ready==="true"')
            assert '/tauschen/sammlr/2/manual' in p.url
            assert p.locator('.sticker-list-item').count()>0
            p.locator('.sticker-list-item[data-side="receive"]').first.click()
            p.locator('.sticker-list-item[data-side="give"]').first.click()
            p.locator('#manual-review').click();p.wait_for_function('document.querySelector("#manual-status").textContent.includes("Auswahl gültig")')
            assert not p.evaluate('sessionStorage.getItem("sammlr-trade-02")')
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            p.screenshot(path=str(OUT/f'manual-{width}.png'),full_page=True)
            go('/profil/Demo%20ohne%20Gegentausch');assert 'Aktuell kein Tausch möglich.' in p.locator('.profile-trade').inner_text()
            assert p.locator('.collector-showcase-album-grid a').count()==3
            assert p.locator('.profile-trade-actions').count()==0
            p.screenshot(path=str(OUT/f'no-trade-{width}.png'),full_page=True)
            go('/profil');assert p.locator('.profile-trade').count()==0
            results.append(dict(width=width,sap_context=True,collection_unchanged=True,auto=True,manual_existing_ui=True,server_validated=True,no_requests=True,no_deal=True,own_unchanged=True,no_overflow=True))
            c.close()
        b.close()
    assert not errors,errors
    assert all(url.endswith('/manual/check') for url in posts),posts
    assert len(posts)==4
    assert before==hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(dict(results=results,errors=errors,validation_posts=len(posts),database_unchanged=True),indent=2)+'\n')
    print('PASS profile/auto/manual/context/privacy/read-only at four widths')

if __name__=='__main__':main(Path(sys.argv[1]))
