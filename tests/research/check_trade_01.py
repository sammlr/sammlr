"""TRADE-01 browser/stack regression. Existing renderer uses a temporary test DB only."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
from tests.test_sticker_wall_product_island import webapp
from App.trade_v2.fixtures import PARTNERS

BASE = 'http://127.0.0.1:8095'
OUT = Path(__file__).parent / 'artifacts/trade-04/regression-01'
PROPS = ['width', 'height', 'padding', 'borderRadius', 'borderColor', 'backgroundColor',
         'transform', 'zIndex', 'fontFamily', 'fontSize', 'fontWeight', 'letterSpacing',
         'aspectRatio', 'boxShadow']
STYLE = '(e,props)=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]]))'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks, shots, errors, writes, external = [], [], [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (375, 390, 430):
            context = browser.new_context(viewport={'width': width, 'height': 844}, has_touch=True,
                                          reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda req: writes.append(req.url) if req.method not in ('GET', 'HEAD') else None)
            page.on('request', lambda req: external.append(req.url) if not req.url.startswith(BASE) else None)
            page.on('response', lambda res: errors.append(f'{res.status}: {res.url}') if res.status >= 400 else None)

            def visible_checks():
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, page.url)
                assert not re.search(r'pax|sammlrpax|pack öffnen|booster', page.locator('body').inner_text(), re.I)

            def go(path):
                page.goto(BASE+path)
                page.wait_for_function('document.body.dataset.ready === "true"')
                page.evaluate('document.fonts.ready')
                visible_checks()

            def shot(name, locator=None, full=True):
                file = f'{name}-{width}.png'
                if locator:
                    locator.screenshot(path=str(OUT/file))
                else:
                    page.screenshot(path=str(OUT/file), full_page=full)
                shots.append(file)

            go('/trade-v2/')
            assert page.locator('.top-offer').count() == 3
            assert page.locator('#partner-list').count() == 0
            # No overlapping hit targets; each stack has the responsive canonical wall width.
            rects = page.locator('.top-toggle').evaluate_all('(es)=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}})')
            for i, a in enumerate(rects):
                for b in rects[i+1:]:
                    assert a['right'] <= b['x'] or b['right'] <= a['x'] or a['bottom'] <= b['y'] or b['bottom'] <= a['y']
            assert page.locator('.top-table').bounding_box()['height'] < 660
            assert page.locator('.top-stack .sticker-slot-frame').evaluate_all('(es)=>es.every(e=>Math.abs(parseFloat(getComputedStyle(e).width)-parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--trade-card-width")))<.1)')
            shot('01-home')
            if width == 390:
                shot('02-top-five', page.locator('#top-table'))
                shot('05-navigation', page.locator('.home-nav'))
            for i, slug in enumerate(('fatima','justus','marek')):
                page.locator('.top-toggle').nth(i).tap()
                page.wait_for_function('document.body.dataset.ready === "true"')
                assert page.url.endswith('/deals/'+slug)
                go('/trade-v2/')
            first = page.locator('.top-toggle').first
            first.focus();page.keyboard.press('Space')
            page.wait_for_function('document.body.dataset.ready === "true"')
            assert page.url.endswith('/deals/fatima')
            visible_checks()
            assert page.locator('h1').inner_text() == 'Tausch mit Fatima'
            assert page.locator('.pax-receive-album').count() == 6
            if width == 390: shot('04-top-detail')
            toggles = page.locator('.pax-album-toggle')
            toggles.nth(0).tap();toggles.nth(1).tap()
            assert page.locator('.pax-receive-album.is-expanded').count() == 2
            assert page.locator('.pax-fan-grid').first.locator('.sticker-slot-frame').count() == 4
            pose = page.locator('.pax-fan-grid').first.inner_html()
            page.locator('.pax-album-fan .pj-simulation').first.click()
            assert page.locator('.pax-receive-album.is-expanded').count() == 1
            toggles.nth(0).click()
            assert page.locator('.pax-fan-grid').first.inner_html() == pose
            visible_checks()
            if width == 390: shot('11-receive-open')
            assert page.get_by_role('button', name='Tauschanfrage senden', exact=True).is_enabled()
            assert page.locator('input[type=checkbox]').count() == 0

            go('/trade-v2/deals/justus')
            notes = page.locator('.pax-give-album').first.locator('.trade-postit')
            assert notes.count() == 3
            assert [notes.nth(i).locator('.pending-review-row').count() for i in range(3)] == [16, 20, 1]
            if width == 390: shot('12-give-continuation', page.locator('.pax-give-album').first)

            go('/trade-v2/partners')
            expected = sorted(PARTNERS, key=lambda p: (-p['max_swap'], p['id']))
            def ids():
                return page.locator('.partner-row').evaluate_all('(es)=>es.map(e=>Number(e.dataset.partnerId))')
            assert ids() == [p['id'] for p in expected]
            if width == 390: shot('06-partners')
            page.locator('summary').focus();page.keyboard.press('Enter')
            for key in ('total_duplicates', 'for_me', 'max_swap'):
                page.locator('#sort').select_option(key)
                assert ids() == [p['id'] for p in sorted(PARTNERS, key=lambda p: (-p[key], p['id']))]
            page.locator('#album').select_option('wm06')
            expected = [p for p in expected if any(a['id'] == 'wm06' for a in p['albums'])]
            assert ids() == [p['id'] for p in expected]
            assert page.locator('#result-count').inner_text() == '2 Sammler'
            visible_checks()
            if width == 390: shot('07-filter')
            page.get_by_role('link', name=re.compile('Karlheinz')).click()
            page.wait_for_function('document.body.dataset.ready === "true"')
            assert page.locator('.match-data dd').all_text_contents() == ['84 Sticker', '37 Sticker', '6', '4.603']
            visible_checks()
            if width == 390: shot('08-karlheinz')
            page.get_by_role('link', name=re.compile('SmartDeal erstellen')).click()
            page.wait_for_function('document.body.dataset.ready === "true"')
            payload = json.loads(page.locator('#trade-data').text_content())['deal']
            assert payload['origin'] == 'SMARTDEAL' and payload['partner'] == 'Karlheinz'
            assert payload['give_count'] == payload['receive_count'] == 37
            assert page.locator('.deal-summary').inner_text() == '37 ↔ 37 · 6 Alben'
            visible_checks()
            if width == 390: shot('09-karlheinz-smartdeal')
            assert page.get_by_role('button', name='Tauschanfrage senden', exact=True).is_enabled()
            go('/trade-v2/partners/karlheinz')
            page.get_by_role('link', name=re.compile('Selbst auswählen')).click()
            page.wait_for_function('document.body.dataset.ready === "true"')
            assert page.locator('#manual-albums .manual-album').count() == 4
            assert page.locator('.sticker-list-item').count() > 0
            assert page.locator('#manual-review').is_disabled()
            assert json.loads(page.locator('#trade-data').text_content())['origin'] == 'MANUAL'
            assert page.locator('input,select').count() == 0
            visible_checks()
            if width == 390: shot('10-manual-end')
            assert page.evaluate('localStorage.length === 0 && sessionStorage.length === 0')
            # Every pool partner can use the same normalized SmartDeal view.
            for p in PARTNERS:
                go('/trade-v2/partners/'+p['slug']+'/smartdeal')
                assert page.locator('h1').inner_text() == 'Tausch mit '+p['display_name']

            # Actual canonical renderer parity, never the production application/DB.
            reference = context.new_page()
            go('/trade-v2/deals/fatima')
            page.evaluate('''()=>{document.querySelector('main').innerHTML='<div class="pax-board"><div class="s30-album-page"><div id="sample" style="width:100px;margin:60px"></div></div></div>'}''')
            growth = []
            for quantity in (1, 2, 5, 6, 10, 15, 37):
                markup = webapp.sticker_wall_slot_html('wm26', 'BRA 3', {'BRA 3': {'quantity': quantity}}, None,
                    'duplicate' if quantity > 1 else 'owned', 'BRA 3', can_edit_inventory=False)
                reference.goto(BASE+'/trade-v2/')
                reference.set_content(f'<link rel="stylesheet" href="{BASE}/static/style.css"><body class="s31-product-page s30-reference-page s30-album-page"><div style="width:100px;margin:60px">{markup}</div></body>')
                reference.wait_for_load_state('networkidle')
                page.evaluate('''async n=>{const {card}=await import('/static/pax/pax.js');document.querySelector('#sample').replaceChildren(card(Array.from({length:n},(_,i)=>({key:'bra-'+i,code:'BRA 3'})),true));}''', quantity)
                n, wall = min(quantity, 10), min(quantity, 5)
                assert page.locator('.sticker-wall-stack-layer').count() == n-1
                assert reference.locator('.sticker-wall-stack-layer').count() == wall-1
                for selector in ('.slot', '.slot .sticker-team', '.slot .sammlr-retro-number-visual', '.slot .sammlr-retro-digit'):
                    actual = page.locator(selector).first.evaluate(STYLE, PROPS)
                    expected = reference.locator(selector).first.evaluate(STYLE, PROPS)
                    if selector == '.slot':
                        expected['transform'] = f'matrix(1, 0, 0, 1, {-2*(n-1)}, {-2*(n-1)})'
                        expected['zIndex'] = str(n)
                    assert actual == expected, (width, quantity, selector, actual, expected)
                for i in range(wall-1):
                    actual_back = page.locator('.sticker-wall-stack-layer').nth(i).evaluate(STYLE, PROPS)
                    expected_back = reference.locator('.sticker-wall-stack-layer').nth(i).evaluate(STYLE, PROPS)
                    assert actual_back == expected_back, (width, quantity, i, actual_back, expected_back)
                layers = page.locator('.sticker-wall-stack-layer,.slot').evaluate_all('(es,props)=>es.map(e=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]])))', PROPS)
                for i, layer in enumerate(layers):
                    assert layer['transform'] == f'matrix(1, 0, 0, 1, {-2*i}, {-2*i})'
                    assert layer['zIndex'] == str(i+1)
                if width == 390 and quantity in (6,10,37):
                    page.screenshot(path=str(OUT.parent/f'trade-stack-{quantity}.png'))
                    reference.screenshot(path=str(OUT.parent/f'wall-stack-{quantity}.png'))
                if quantity >= 10: growth.append(layers)
                checks.append(dict(width=width, quantity=quantity, stack_parity='PASS'))
            assert growth[0] == growth[1] == growth[2]
            checks.append(dict(width=width, journeys='PASS', overflow=False, touch_keyboard_mouse='PASS'))
            context.close()
        browser.close()
    assert not errors, errors
    assert not writes, writes
    assert not external, external
    (OUT/'checks.json').write_text(json.dumps(dict(results=checks, errors=errors, mutations=writes, external_requests=external), indent=2)+'\n')
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-01 · Galerie</title><style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;gap:24px;flex-wrap:wrap;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}figcaption{padding:12px 0}</style><h1>TRADE-01 · Tauschhalle</h1><main>'+''.join(f'<figure><figcaption>{name}</figcaption><a href="{name}"><img loading="lazy" src="{name}" alt="{name}"></a></figure>' for name in shots)+'</main></html>\n')
    print('PASS: 375/390/430, all journeys, 21 canonical stack cases, no writes/external requests/errors; screenshots:', len(shots))


if __name__ == '__main__':
    main()
