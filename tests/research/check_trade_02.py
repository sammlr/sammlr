"""Sender journey, same-tab idempotency, capacity and absolute expiry regression."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8095'
OUT = Path(__file__).parent / 'artifacts/trade-04/regression-02'
KEY = 'sammlr-trade-02'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results, images, errors, writes = [], [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (375, 390, 430, 1280):
            context = browser.new_context(viewport={'width': width, 'height': 900}, has_touch=True, reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda req: writes.append(req.url) if req.method not in ('GET','HEAD') or not req.url.startswith(BASE) else None)
            page.on('response', lambda res: errors.append(f'{res.status} {res.url}') if res.status >= 400 else None)

            def ready():
                page.wait_for_function('document.body.dataset.ready === "true"')
                page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert not re.search(r'\bpax\b|sammlrpax|\bpack\b|booster', page.locator('body').inner_text(), re.I)

            def go(path):
                page.goto(BASE+path);ready()

            def state():
                return page.evaluate('(key)=>JSON.parse(sessionStorage.getItem(key))', KEY)

            def shot(name):
                if width in (390,1280):
                    name = f'{name}-{width}.png';page.screenshot(path=str(OUT/name), full_page=True);images.append(name)

            go('/trade-v2/')
            assert page.locator('.top-toggle').count() == 3
            assert page.locator('.top-panel,.top-fan').count() == 0
            assert page.get_by_text('Tausch ansehen', exact=True).count() == 0
            shot('01-home')
            page.locator('.top-toggle').first.focus();page.keyboard.press('Enter');ready()
            assert page.url.endswith('/deals/fatima')
            assert page.locator('.deal-summary').inner_text() == '23 ↔ 23 · 6 Alben'
            assert page.locator('.pax-give-album .pending-review-row').count() == 23
            for toggle in page.locator('.pax-album-toggle').all(): toggle.click()
            assert page.locator('.pax-fan-grid .sticker-slot-frame').count() == 23
            for button in page.locator('.pax-album-fan .pj-simulation').all(): button.click()
            assert page.get_by_role('link', name=re.compile('SmartDeal erstellen|Selbst auswählen')).count() == 0
            assert page.locator('#capacity-count').inner_text() == '0/3 ausgehend belegt'
            shot('02-fatima-deal')
            # Multiple synchronous activations reach the handler even after disabling it.
            page.locator('#request-preview').evaluate('(b)=>{for(let i=0;i<8;i++)b.dispatchEvent(new MouseEvent("click",{bubbles:true}));}')
            page.wait_for_url('**/requests/fatima*');ready()
            initial = state()
            request = initial['requests']['demo-fatima']
            assert len(initial['requests']) == 1
            assert request['expiresAt']-request['bindingCreatedAt'] == 86400000
            assert request['snapshot']['origin'] == 'TOP_SUGGESTION'
            assert page.locator('#request-status').inner_text() == 'Wartet auf Fatima'
            assert '24 Stunden' in page.locator('#request-clock').inner_text()
            assert page.locator('.pax-board,input[type=checkbox],address').count() == 0
            shot('03-sent')
            page.reload();ready();assert state() == initial
            page.get_by_role('link', name='Vorgeschlagenen Deal ansehen').click();ready()
            page.get_by_role('button', name='Zum Anfragestatus').focus()
            for _ in range(3): page.keyboard.press('Enter')
            page.wait_for_url('**/requests/fatima*');ready();assert state() == initial
            go('/trade-v2/deals/fatima?demo=2')
            assert page.locator('#capacity-count').inner_text() == '2/3 ausgehend belegt'
            shot('04-two-before')
            page.locator('#request-preview').tap();page.wait_for_url('**/requests/fatima*');ready()
            assert page.locator('#capacity-count').inner_text() == '3/3 ausgehend belegt'
            assert len(state()['requests']) == 3
            shot('05-three-after')
            go('/trade-v2/deals/justus')
            assert page.locator('#request-preview').is_disabled()
            assert 'Ein Platz muss zuerst frei werden' in page.locator('#capacity-note').inner_text()
            page.locator('#request-preview').evaluate('(b)=>b.dispatchEvent(new MouseEvent("click"))')
            assert len(state()['requests']) == 3
            shot('06-fourth-blocked')
            # Independent seeded full scenario and real double click on an empty scenario.
            go('/trade-v2/deals/fatima?demo=3');assert page.locator('#request-preview').is_disabled()
            go('/trade-v2/deals/fatima?demo=0');page.locator('#request-preview').dblclick()
            page.wait_for_url('**/requests/fatima*');ready();assert len(state()['requests']) == 1
            go('/trade-v2/deals/fatima');page.locator('#request-preview').tap()
            page.wait_for_url('**/requests/fatima*');ready();assert len(state()['requests']) == 1
            go('/trade-v2/partners');shot('07-pool')
            page.get_by_role('link', name=re.compile('Karlheinz')).click();ready()
            assert page.locator('.match-data dd').all_text_contents() == ['84 Sticker','37 Sticker','6','4.603']
            assert page.get_by_role('link', name=re.compile('SmartDeal erstellen')).is_visible()
            assert page.get_by_role('link', name=re.compile('Selbst auswählen')).is_visible()
            shot('08-karlheinz')
            page.get_by_role('link', name=re.compile('SmartDeal erstellen')).click();ready()
            page.locator('#request-preview').click();page.wait_for_url('**/requests/karlheinz');ready()
            assert len(state()['requests']) == 2  # Same outgoing pool for both origins.
            assert state()['requests']['demo-karlheinz']['origin'] == 'SMARTDEAL'
            go('/trade-v2/requests/fatima?demo=sent')
            assert '?' not in page.url
            snapshot = state();page.reload();ready();assert state() == snapshot
            # Expiry while the page stays open; absolute 24h, including exact boundary.
            page.clock.install(time=snapshot['requests']['demo-fatima']['bindingCreatedAt'])
            page.reload();ready()  # Register the page timer under the controlled clock.
            page.clock.fast_forward(86400000)
            assert page.locator('#request-status').inner_text().startswith('Die 24-Stunden-Frist ist abgelaufen')
            assert page.locator('#capacity-count').inner_text() == '0/3 ausgehend belegt'
            assert state()['requests']['demo-fatima']['bindingCreatedAt'] == snapshot['requests']['demo-fatima']['bindingCreatedAt']
            page.reload();ready();assert state()['requests']['demo-fatima']['status'] == 'expired'
            results.append({'width':width,'sender':'PASS','capacity':'PASS','retries_reload_expiry':'PASS','overflow':False})
            context.close()

        context = browser.new_context()
        page = context.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        model = page.evaluate('''async()=>{
          const m=await import('/trade-v2/assets/requests.js');
          const deal=JSON.parse(document.querySelector('#trade-data').textContent).deal;
          const check=(ok,label)=>{if(!ok)throw Error(label);};
          const state=m.initialState(2,1000);
          const before=JSON.stringify(deal);
          check(m.slots(state,'outgoing',1000)===2,'two seeds');
          const first=m.send(state,deal,1000);
          for(let i=0;i<20;i++)check(m.send(state,deal,1001+i).request===first.request,'idempotency');
          check(m.slots(state,'outgoing',2000)===3,'three');
          check(m.send(state,{...deal,id:'fourth'},2000).status==='full','fourth blocked');
          check(JSON.stringify(deal)===before,'input snapshot unchanged');
          check(first.request.snapshot!==deal,'independent snapshot');
          check(first.request.expiresAt===1000+m.DAY,'absolute deadline');
          m.expire(state,1000+m.DAY-1);check(first.request.status==='pending','one ms before');
          m.expire(state,1000+m.DAY);check(first.request.status==='expired','at deadline');
          check(m.slots(state,'outgoing',1000+m.DAY)===0,'expiry releases');
          const accepted=m.initialState(1,1000);accepted.requests['seed-0'].status='accepted';
          m.expire(accepted,1000+m.DAY);check(m.slots(accepted,'outgoing',1000+m.DAY)===1,'accept keeps operative slot');
          accepted.requests['seed-0'].ownShipped=true;check(m.slots(accepted,'outgoing',1000+m.DAY)===0,'own shipment frees own slot');
          accepted.requests['seed-0'].ownShipped=false;accepted.requests['seed-0'].direction='incoming';
          check(m.slots(accepted,'outgoing',1000+m.DAY)===0 && m.slots(accepted,'incoming',1000+m.DAY)===1,'directions separate');
          const restored=m.readState({getItem:()=>JSON.stringify(state)});check(restored.requests[deal.id].bindingCreatedAt===1000,'restore keeps time');
          let bad=false;try{m.readState({getItem:()=>'{broken'});}catch{bad=true;}check(bad,'invalid storage rejected');
          return 'PASS';
        }''')
        assert model == 'PASS'
        page.evaluate('(k)=>sessionStorage.setItem(k,"{broken")',KEY);page.reload();page.wait_for_function('document.body.dataset.ready === "true"')
        assert page.locator('#request-preview').is_disabled()
        assert 'ungültig' in page.locator('#capacity-note').inner_text()
        context.close()
        browser.close()
    assert not errors,errors
    assert not writes,writes
    (OUT/'checks.json').write_text(json.dumps({'results':results,'model':model,'errors':errors,'writes_or_external':writes},indent=2)+'\n')
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-02 Galerie</title><style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}</style><h1>TRADE-02 · Sender-Journey</h1><p><a href="../regression-01/index.html">Weitere mobile Regressionen</a> · <a href="../stack-comparison.html">Kanonischer Stackvergleich</a></p><main>'+''.join(f'<figure><figcaption>{n}</figcaption><a href="{n}"><img src="{n}" alt="{n}" loading="lazy"></a></figure>' for n in images)+'</main></html>\n')
    print('PASS: sender/capacity/idempotency/absolute expiry at 375/390/430/1280; model and corrupt storage; screenshots',len(images))


if __name__ == '__main__':main()
