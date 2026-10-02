"""PAX-04b counter: direct opening, quantity depth and preserved detail layout."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8094'
OUT = Path(__file__).parent / 'artifacts/pax-04c'
ORDER = ['fatima', 'justus', 'marek', 'luca', 'amadou']


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (375, 390, 430):
            page = browser.new_page(viewport={'width': width, 'height': 844})
            errors, failures, writes = [], [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: failures.append(r.url) if r.status >= 400 else None)
            page.on('request', lambda r: writes.append(r.url) if r.method not in ('GET', 'HEAD') else None)

            def geometry():
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                for selector in ('.pax-receive-album', '.pax-fan-grid .sticker-slot-frame'):
                    assert page.locator(selector).evaluate_all('''es=>{const rs=es.filter(e=>e.checkVisibility()).map(e=>e.getBoundingClientRect());return rs.every((a,i)=>rs.slice(i+1).every(b=>a.right<=b.left+.1||b.right<=a.left+.1||a.bottom<=b.top+.1||b.bottom<=a.top+.1))}'''), selector
                assert page.locator('.sticker-list-review-codes').evaluate_all('es=>es.filter(e=>e.checkVisibility()).every(e=>e.scrollWidth<=e.clientWidth && e.scrollHeight<=e.clientHeight)')
                assert page.locator('.pending-review-row').evaluate_all('es=>es.filter(e=>e.checkVisibility()).every(e=>e.scrollWidth<=e.clientWidth)')

            def shot(name, selector=None):
                geometry()
                if width == 390:
                    if selector:
                        page.locator(selector).screenshot(path=str(OUT / f'{name}-390.png'))
                    else:
                        page.evaluate('scrollTo(0,0)')
                        page.screenshot(path=str(OUT / f'{name}-390.png'), full_page=True)

            page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
            packs=page.locator('.pax-counter-pack')
            assert packs.count()==5
            assert page.locator('.pax-kiosk,.pax-register,#pax-next,#pax-previous,.pax-summary,.ceoklaue-run').count()==0
            for pack in packs.all():
                box=pack.bounding_box()
                assert box['x']>=0 and box['x']+box['width']<=width and box['y']+box['height']<=844,box
                for selector in ('.pj-pack-title','.pj-pack-partner','.pj-pack-footer strong','.pj-pack-footer small'):
                    assert pack.locator(selector).evaluate("e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('a')===e.closest('a')}")
                assert 'CEO' not in pack.evaluate('e=>getComputedStyle(e).fontFamily')
            geometry()
            page.screenshot(path=str(OUT/f'01-discovery-{width}.png'),full_page=True)
            for name in ORDER:
                page.locator(f'[data-candidate={name}]').click()
                page.wait_for_url('**/pax/'+name)
                page.wait_for_function('document.body.dataset.screen==="board"');geometry()
                assert name in page.locator('section[data-screen=board] h1').inner_text().lower()
                page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
            page.locator('[data-candidate=justus]').click()
            page.wait_for_url('**/pax/justus')
            page.wait_for_function('document.body.dataset.screen==="board"')
            assert 'Justus' in page.locator('section[data-screen=board] h1').inner_text()
            assert page.locator('#pax-open').count() == 0
            assert page.locator('.pax-give-album').first.locator('.trade-postit').evaluate_all('es=>es.map(e=>e.querySelectorAll(".pending-review-row").length)') == [16,20,1]
            assert page.locator('.is-continuation h3').count() == 0
            assert page.locator('.pax-give button,.pax-give input,.sticker-selection-marker').count() == 0
            # Overlap may touch paper margins only, never previous text.
            assert page.locator('.pax-give-album').first.evaluate('''g=>{const ns=[...g.children];return ns.slice(1).every((n,i)=>{const prev=ns[i], text=prev.querySelector('.sticker-list-review-codes').getBoundingClientRect();return n.getBoundingClientRect().top>text.bottom && n.getBoundingClientRect().top<prev.getBoundingClientRect().bottom;});}''')
            shot('03-large-receive', '.pax-receive')
            shot('07-continuation-16-20-rest', '.pax-give')
            page.locator('.pax-album-toggle').first.click();geometry()
            assert page.locator('.pax-album-fan:visible .slot').count() == 37
            page.locator('.pax-album-fan:visible button').click()
            page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
            page.locator('[data-candidate=fatima]').focus();page.keyboard.press('Enter')
            page.wait_for_url('**/pax/fatima');page.wait_for_function('document.body.dataset.screen==="board"')
            albums=page.locator('.pax-receive-album')
            assert albums.count()==6
            rects=albums.evaluate_all('es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY}})')
            assert rects[0]['x']<rects[1]['x'] and abs(rects[0]['y']-rects[1]['y'])<1
            assert page.locator('#pax-receive-albums').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns').count('px')==2
            shot('04-fatima-receive', '.pax-receive')
            before=albums.evaluate_all('es=>es.slice(1).map(e=>e.innerHTML)')
            page.locator('.pax-album-toggle').first.click();geometry()
            assert albums.evaluate_all('es=>es.slice(1).map(e=>e.innerHTML)')==before
            shot('05-album-fan', '.pax-receive')
            page.locator('.pax-album-fan:visible button').click()
            assert albums.evaluate_all('es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY}})')==rects
            for toggle in page.locator('.pax-album-toggle').all():
                toggle.click();geometry();page.locator('.pax-album-fan:visible button').click()
            shot('06-give-albums', '.pax-give')
            page.locator('#pax-request').scroll_into_view_if_needed()
            if width==390:page.screenshot(path=str(OUT/'08-cta-390.png'))
            assert page.locator('#pax-request').is_enabled()
            page.locator('#pax-request').click();assert page.locator('section[data-screen=waiting]').is_visible()
            boundary=page.evaluate('''async()=>{const {splitReviewItems}=await import('/static/pax/pax.js');return [0,8,9,16,17,36,37,56,57].map(n=>splitReviewItems(Array.from({length:n},(_,i)=>i)).map(c=>c.items.length));}''')
            assert boundary==[[],[8],[9],[16],[16,1],[16,20],[16,20,1],[16,20,20],[16,20,20,1]]
            # Remaining candidates also open their own exact data.
            for name in ('marek','luca','amadou'):
                page.goto(BASE+'/pax/'+name);page.wait_for_function('document.body.dataset.screen==="board"');geometry()
                assert name.lower() in page.locator('section[data-screen=board] h1').inner_text().lower()
            assert not errors and not failures and not writes,(errors,failures,writes)
            results.append(dict(width=width,direct_open='PASS',five_visible='PASS',overflow=False,collisions=False,posts=0))
            page.close()
        # Native touch, tab order, Enter/Space and reduced motion for every pack.
        context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
        page=context.new_page()
        for name in ORDER:
            page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
            assert page.locator('.pax-counter-pack').first.evaluate('e=>getComputedStyle(e).transitionDuration')=='0s'
            page.locator(f'[data-candidate={name}]').tap();page.wait_for_url('**/pax/'+name)
            for key in ('Enter','Space'):
                page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
                page.locator('.pax-counter-pack').first.focus()
                for _ in range(ORDER.index(name)):page.keyboard.press('Tab')
                assert page.locator(':focus').get_attribute('data-candidate')==name
                assert page.locator(':focus').evaluate('e=>getComputedStyle(e).outlineStyle')=='solid'
                page.keyboard.press(key);page.wait_for_url('**/pax/'+name)
        for width in (375,390,430):
            page.set_viewport_size({'width':width,'height':844})
            page.goto(BASE+'/pax/layer-comparison');page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('.pax-cap-sample').count()==7
            for count in (1,2,5,6,10,15,37):
                sample=page.locator(f'[data-layers="{count}"]')
                assert sample.locator('.sticker-wall-stack-layer').count()==min(count,10)-1
                assert sample.locator('.slot').evaluate('e=>getComputedStyle(e).transform')==f'matrix(1, 0, 0, 1, {-2*(min(count,10)-1)}, {-2*(min(count,10)-1)})'
                assert sample.locator('.slot').evaluate('e=>getComputedStyle(e).zIndex')==str(min(count,10))
            page.screenshot(path=str(OUT/f'layer-comparison-{width}.png'),full_page=True)
        page.goto(BASE+'/pax/justus');page.wait_for_function('document.body.dataset.screen==="board"')
        notes=page.locator('.pax-loose-note').evaluate_all('es=>es.map(e=>e.style.cssText)')
        page.locator('.pax-album-toggle').first.click()
        poses=page.locator('.pax-loose-card').evaluate_all('es=>es.map(e=>e.style.cssText)')
        page.reload();page.wait_for_function('document.body.dataset.screen==="board"')
        assert notes==page.locator('.pax-loose-note').evaluate_all('es=>es.map(e=>e.style.cssText)')
        assert poses==page.locator('.pax-loose-card').evaluate_all('es=>es.map(e=>e.style.cssText)')
        context.close();browser.close()
    (OUT/'checks.json').write_text(json.dumps({'mobile':results,'touch':'PASS','keyboard':'PASS','reduced_motion':'PASS'},indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
