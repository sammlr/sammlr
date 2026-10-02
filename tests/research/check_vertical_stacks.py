"""Browser geometry gate; run in an isolated release candidate with Playwright.
No server, DB writes or inventory mutations. Uses the actual wall renderer.
"""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'App'))
import webapp


class Inventory:
    def availability_snapshot_for(self, code):
        return SimpleNamespace(incoming_transit=0)


def check_accepted_interactive_stack(browser, initial_quantity=0):
    """PO contract: existing physical cards stay; a complete new copy goes ON TOP.

    Exercise the real album HTML, inline JavaScript and quantity endpoint on a
    synthetic temporary DB. Never point this check at a running user's app.
    """
    import shutil
    import sqlite3
    import tempfile
    from urllib.parse import unquote, urlparse
    from App.Database.migration_runner import migrate

    with tempfile.TemporaryDirectory(prefix='sammlr-accepted-stack-') as directory:
        db = Path(directory) / 'browser.db'
        shutil.copyfile(ROOT / 'App/Database/sammlr_reference_s00.db', db)
        with sqlite3.connect(db) as connection:
            migrate(connection)
            connection.execute("DELETE FROM stickers WHERE user_id=1 AND album_id='wm26'")
            if initial_quantity:
                connection.execute("INSERT INTO stickers (album_id,sticker_code,status,duplicates,quantity,user_id) VALUES ('wm26','FWC1','owned',?,?,1)", (initial_quantity-1,initial_quantity))
        previous_testing = webapp.app.config["TESTING"]
        webapp.app.config["TESTING"] = True
        previous_db = webapp.DB
        webapp.DB = str(db)
        page = browser.new_page(viewport={'width':390, 'height':844})
        try:
            client = webapp.app.test_client()
            with client.session_transaction() as session:
                session['user_id'] = 1
            response = client.get('/album/wm26')
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            def serve(route):
                path = unquote(urlparse(route.request.url).path)
                if route.request.method == 'POST':
                    assert path == '/album/wm26/sticker/FWC1/quantity'
                    response = client.post(path, data=route.request.post_data,
                        content_type='application/x-www-form-urlencoded',
                        headers={'X-CSRF-Token':route.request.headers.get('x-csrf-token','')})
                    assert response.status_code == 200
                    route.fulfill(status=response.status_code, body=response.get_data(), content_type=response.content_type)
                elif path == '/album/wm26':
                    route.fulfill(body=html, content_type='text/html')
                elif path.startswith('/static/') and (ROOT / 'App' / path.lstrip('/')).is_file():
                    route.fulfill(path=str(ROOT / 'App' / path.lstrip('/')))
                else:
                    route.fulfill(status=404, body='')
            page.route('**/*', serve)
            page.goto('http://accepted-stack.test/album/wm26')
            page.wait_for_load_state('networkidle')
            frame = page.locator('.slot[data-code="FWC1"]').locator('..')
            frame.locator('.slot').click()
            initial_frame = frame.bounding_box()
            # PO-approved real album card at the locked 390px viewport.
            assert [initial_frame['width'], initial_frame['height']] == [108, 123.109375]
            frame.evaluate("e=>window.acceptedCards=[...e.querySelectorAll('.sticker-wall-stack-layer,.slot')].map(node=>{const r=node.getBoundingClientRect();return {node,rect:[r.x,r.y,r.width,r.height]}})")
            sequence = (list(range(8)) + list(range(6,-1,-1))) if initial_quantity==0 else list(range(initial_quantity,-1,-1))
            evidence = []
            for q in sequence:
                current = int(frame.get_attribute('data-stack-quantity'))
                if current != q:
                    frame.locator(f'[data-quantity-delta="{1 if q>current else -1}"]').click()
                    page.wait_for_function('(q)=>document.querySelector(".slot[data-code=FWC1]").dataset.quantity===String(q)', arg=q, timeout=5000)
                page.wait_for_timeout(250)  # Existing style transition; no injected animation.
                result = frame.evaluate('''(e,q)=>{
                    const cards=[...e.querySelectorAll('.sticker-wall-stack-layer,.slot')];
                    const base=e.getBoundingClientRect(), top=cards.at(-1), r=top.getBoundingClientRect();
                    const rect=n=>{const b=n.getBoundingClientRect();return [b.x,b.y,b.width,b.height]};
                    const old=window.acceptedCards;
                    const stable=old.every((entry,i)=>i>=cards.length || (entry.node===cards[i] && JSON.stringify(entry.rect)===JSON.stringify(rect(cards[i]))));
                    const added=cards.length>old.length ? cards.filter(n=>!old.some(o=>o.node===n)).length : 0;
                    window.acceptedCards=cards.map(n=>({node:n,rect:rect(n)}));
                    const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                    const appearance=n=>{let s=getComputedStyle(n);return [s.backgroundColor,s.border,s.borderRadius,s.boxShadow]};
                    const collision=[...document.querySelectorAll('[data-sticker-frame]')].filter(n=>n!==e).some(n=>{
                        let b=n.getBoundingClientRect();return b.width>0 && b.height>0 && r.left<b.right && base.right>b.left && r.top<b.bottom && base.bottom>b.top;
                    });
                    return {stable,added,base:rect(e),collision,topHit:top===hit||top.contains(hit),
                        offsets:cards.map(n=>{let b=n.getBoundingClientRect();return [b.x-base.x,b.y-base.y]}),
                        sizes:cards.map(n=>rect(n).slice(2)),z:cards.map(n=>Number(getComputedStyle(n).zIndex)),
                        appearances:cards.map(appearance),
                        faces:cards.map(n=>({prefix:n.querySelector('.sticker-team')?.textContent.trim(),number:n.querySelector('.sammlr-retro-number-text')?.textContent.trim(),bubble:n.querySelector('.sticker-qty')?.textContent.trim()||null})),
                        missing:top.classList.contains('missing'),overflow:document.documentElement.scrollWidth>innerWidth};
                }''', q)
                with sqlite3.connect(db) as connection:
                    row = connection.execute("SELECT quantity FROM stickers WHERE user_id=1 AND album_id='wm26' AND sticker_code='FWC1'").fetchone()
                assert (row[0] if row else 0) == q, ('persisted quantity',initial_quantity,q,row)
                assert frame.locator('[data-inline-quantity]').inner_text() == str(q)
                assert frame.locator('[data-quantity-delta="-1"]').is_disabled() == (q==0)
                status = 'missing' if q==0 else 'owned' if q==1 else 'duplicate'
                assert status in frame.locator('.slot').get_attribute('class').split()
                count = max(1, min(q,5))
                assert result['stable'], (q, 'existing card moved or was replaced')
                assert result['added'] == (1 if 1<q<=5 and current<q else 0), (q,result)
                assert result['offsets'] == [[-2*i,-2*i] for i in range(count)], (q,result)
                assert result['z'] == list(range(1,count+1)), (q,result)
                assert all(size == [initial_frame['width'],initial_frame['height']] for size in result['sizes'])
                assert result['base'] == [initial_frame[k] for k in ('x','y','width','height')]
                assert result['topHit'] and not result['collision'] and not result['overflow']
                assert result['missing'] == (q==0)
                for i, face in enumerate(result['faces']):
                    assert face['prefix']=='FWC' and face['number']=='1', (q,i,face)
                    assert face['bubble'] == (str(q) if q>1 and i==count-1 else None), (q,i,face)
                if q>1:
                    assert all(a[0]=='rgb(255, 255, 255)' for a in result['appearances'])
                    assert all(a[1:3]==result['appearances'][-1][1:3] for a in result['appearances'])
                    assert all(a[3]=='none' for a in result['appearances'])
                if q in (0,1,2,3,4,5):
                    page.screenshot(path=f'/private/tmp/accepted-stack-initial-{initial_quantity}-{q}-390.png')
                evidence.append({'quantity':q,'offsets':result['offsets'],'z':result['z'],'existing_nodes_stable':result['stable']})
            print(json.dumps({'initial_quantity':initial_quantity,'accepted_interactive_390':evidence},indent=2))
        finally:
            page.close()
            webapp.DB = previous_db
            webapp.app.config["TESTING"] = previous_testing


def main():
    assert ROOT.is_relative_to(Path('/private/tmp')), 'Use an isolated release candidate'
    quantities = (0, 1, 2, 3, 4, 5, 6, 7, 20, 89)
    cards = ''.join(webapp.sticker_wall_slot_html(
        'wm26', 'FWC' + str(i+1), {'FWC'+str(i+1): {'quantity':q}}, Inventory(),
        'missing' if q==0 else 'owned' if q==1 else 'duplicate', 'fixture',
        can_edit_inventory=True) for i,q in enumerate(quantities))
    html = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="http://fixture/static/style.css"><body class="s30-album-page"><main style="padding:24px 20px"><h2 style="overflow-wrap:anywhere">Langer Albumkontext und ausführliche Gruppenbezeichnung für die Stackprüfung</h2><div class="wall">'+cards+'</div></main></body>'
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page()
        page.route('http://fixture/static/**', lambda route:route.fulfill(path=str(ROOT/'App/static'/route.request.url.split('/static/')[1])))
        for width in (375,390,430):
            page.set_viewport_size({'width':width,'height':844})
            page.set_content(html);page.wait_for_load_state('networkidle')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            single_shadow = page.locator('.slot.owned').evaluate('el=>getComputedStyle(el).boxShadow')
            for q,frame in zip(quantities,page.locator('.sticker-slot-frame').all()):
                base=frame.bounding_box();front=frame.locator('.slot');f=front.bounding_box()
                count=min(q,5);rise=max(count-1,0)*2
                assert abs((f['x']+f['width'])-(base['x']+base['width']-rise))<.1
                assert abs(f['x']-(base['x']-rise))<.1
                assert abs(f['y']-(base['y']-rise))<.1
                assert abs(f['width']-base['width'])<.1 and abs(f['height']-base['height'])<.1
                layers=frame.locator('.sticker-wall-stack-layer').all()
                assert len(layers)==max(count-1,0)
                for i,layer in enumerate(layers):
                    assert layer.is_visible();r=layer.bounding_box()
                    assert layer.evaluate('el=>getComputedStyle(el).boxShadow')=='none'
                    assert abs((r['x']+r['width'])-(base['x']+base['width']-i*2))<.1
                    assert abs(r['x']-(base['x']-i*2))<.1 and abs(r['y']-(base['y']-i*2))<.1
                    assert abs(r['width']-f['width'])<.1 and abs(r['height']-f['height'])<.1
                # Copies are physically placed ON TOP of the existing stack.
                # The real sticker card is newest/topmost and moves 2px up-left per copy.
                # The bottom stays anchored; every inter-card gap is identical.
                expected = {
                    1: [(0, 0)], 2: [(0, 0), (-2, -2)],
                    3: [(0, 0), (-2, -2), (-4, -4)],
                    4: [(0, 0), (-2, -2), (-4, -4), (-6, -6)],
                    5: [(0, 0), (-2, -2), (-4, -4), (-6, -6), (-8, -8)],
                }
                if q:
                    physical = [layer.bounding_box() for layer in layers] + [f]
                    offsets = [(round(r['x']-base['x'], 3), round(r['y']-base['y'], 3)) for r in physical]
                    assert offsets == expected[min(q,5)], (q, offsets)
                    for lower, upper in zip(physical, physical[1:]):
                        assert abs(lower['x']-upper['x']-2)<.01
                        assert abs(lower['y']-upper['y']-2)<.01
                    if q > 1:
                        assert front.evaluate('el=>getComputedStyle(el).boxShadow') == 'none'
                        appearance = "el=>{let s=getComputedStyle(el);return [s.width,s.height,s.borderRadius,s.border,s.backgroundColor]}"
                        for layer in layers:
                            assert layer.evaluate(appearance) == front.evaluate(appearance)
                        for card in layers+[front]:
                            assert card.evaluate("el=>{let s=getComputedStyle(el);return s.outlineStyle==='none'||s.outlineWidth==='0px'}")
                            for pseudo in ('::before','::after'):
                                assert card.evaluate("(el,p)=>{let s=getComputedStyle(el,p);return s.content==='none'||s.display==='none'}",pseudo)
                    assert front.evaluate('el=>Number(getComputedStyle(el).zIndex)') > max(
                        [layer.evaluate('el=>Number(getComputedStyle(el).zIndex)') for layer in layers] or [0])
                assert f['y']>=0
                # Visible top edge must not be clipped/covered by neighboring cards.
                assert front.evaluate('(el)=>{const r=el.getBoundingClientRect();const hit=document.elementFromPoint(r.x+r.width/2,r.y+1);return el===hit||el.contains(hit)}')
                if q>1:assert frame.locator('.sticker-qty').inner_text()==str(q)
                else:assert frame.locator('.sticker-qty').count()==0
                # Show existing control without calling a quantity mutation.
                frame.evaluate("el=>el.classList.add('inline-active')")
                plus=frame.locator('[data-quantity-delta="1"]');assert plus.is_visible();plus.focus();assert plus.evaluate('el=>el===document.activeElement')
                assert frame.locator('[data-quantity-delta="-1"]').is_disabled()==(q==0)
                frame.evaluate("el=>el.classList.remove('inline-active')")
                results.append({'width':width,'quantity':q,'rise':rise,'layers':len(layers)})
            if width==390:page.screenshot(path='/private/tmp/stack-edges-390.png',full_page=True)
            baseline=page.locator('.slot').evaluate_all('els=>els.map(el=>{const r=el.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')
            # Even accidental loading of preview sheets must not redefine wall geometry.
            for name in ('compact_sticker_stack.css','trade_visual_preview.css'):
                page.add_style_tag(path=str(ROOT/'App/static'/name))
            after=page.locator('.slot').evaluate_all('els=>els.map(el=>{const r=el.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})')
            # Preview's global layout is not part of the app. Geometry invariants are
            # checked relative to each frame, independently of that global layout.
            for q,frame in zip(quantities,page.locator('.sticker-slot-frame').all()):
                base=frame.bounding_box();front=frame.locator('.slot').bounding_box()
                assert abs(front['x']-base['x']+max(min(q,5)-1,0)*2)<.1
                assert abs(front['y']-base['y']+max(min(q,5)-1,0)*2)<.1
            if width==390:page.screenshot(path='/private/tmp/vertical-wall-390.png',full_page=True)
        for initial_quantity in (0,4,5,7,20):
            check_accepted_interactive_stack(browser, initial_quantity)
        browser.close()
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
