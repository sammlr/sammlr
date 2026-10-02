"""One saved request, two perspectives, exclusive recipient decisions."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8095'
OUT = Path(__file__).parent / 'artifacts/trade-04/regression-03'
KEY = 'sammlr-trade-02'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results, images, errors, mutations = [], [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (375,390,430,1280):
            context = browser.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') or not r.url.startswith(BASE) else None)
            page.on('response',lambda r:errors.append(f'{r.status}: {r.url}') if r.status>=400 else None)

            def ready():
                page.wait_for_function('document.body.dataset.ready === "true"')
                page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,page.url)
                assert not re.search(r'\bpax\b|sammlrpax|booster',page.locator('body').inner_text(),re.I)
                assert page.locator('address,input[type=checkbox],.sticker-selection-marker').count()==0

            def go(path):page.goto(BASE+path);ready()
            def state():return page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k))',KEY)
            def record():return state()['requests']['demo-fatima']
            def shot(name,full=True):
                filename=f'{name}-{width}.png';page.screenshot(path=str(OUT/filename),full_page=full);images.append(filename)
            def role(which):
                page.locator('.demo-tools').evaluate('(e)=>e.open=true')
                page.locator('#role-'+which).tap();ready()
            def keys(side):
                selector='.pax-fan-grid .sticker-slot-frame' if side=='receive' else '.pax-give-album .pending-review-row'
                return page.locator(selector).evaluate_all('(es)=>es.map(e=>e.dataset.itemKey)')

            # Send the actual reference request, then inspect it from the second role.
            go('/trade-v2/deals/fatima?demo=2')
            go('/trade-v2/')
            page.locator('.top-toggle').first.tap();ready()
            page.get_by_role('button',name='Tauschanfrage senden').click()
            page.wait_for_url('**/requests/fatima');ready()
            original=record();snapshot=original['snapshot']
            assert snapshot['origin']=='TOP_SUGGESTION'
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            assert page.locator('#request-status').inner_text()=='Wartet auf Fatima'
            shot('01-valentin-waiting')
            if width==390:
                shot('11-slot-before-decline')
                page.locator('.demo-tools').evaluate('(e)=>e.open=true');shot('10-dev-roles')
            role('recipient')
            assert record()==original
            assert page.locator('#waiting-title').inner_text()=='Valentin möchte mit dir tauschen.'
            assert page.locator('#request-summary').inner_text()=='23 ↔ 23 · 6 Alben'
            assert page.locator('.pax-receive-album').count()==6
            assert keys('give')==[i['key'] for a in snapshot['receive'] for i in a['items']]
            # The receive fans exist closed, so compare every exact original item key.
            assert keys('receive')==[i['key'] for a in snapshot['give'] for i in a['items']]
            assert len(keys('receive'))==len(keys('give'))==23
            assert page.locator('#capacity-count').inner_text()=='1/3 eingehend belegt'
            shot('02-fatima-incoming',False);shot('03-fatima-mirrored')
            page.locator('#accept-request').scroll_into_view_if_needed()
            if width==390:shot('04-fatima-before-accept',False)
            page.locator('#accept-request').focus();page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.id')=='decline-request'
            page.keyboard.press('Shift+Tab');assert page.evaluate('document.activeElement.id')=='accept-request'
            page.keyboard.press('Space');ready()
            assert record()['status']=='accepted'
            assert record()['snapshot']==snapshot
            assert len(state()['requests'])==3
            accepted=record()
            assert page.locator('#waiting-title').inner_text()=='Tausch steht ✓'
            assert page.locator('#decision-actions').is_hidden()
            assert page.locator('.pax-board').count()==0
            assert page.locator('#capacity-count').inner_text()=='1/3 eingehend belegt'
            # Opposite command and repeated Enter cannot reverse the accepted decision.
            page.locator('#decline-request').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))')
            for _ in range(3):page.keyboard.press('Enter')
            assert record()==accepted
            shot('05-fatima-accepted')
            page.get_by_role('link',name='Zum Packen →').click();ready()
            assert page.locator('#pack-progress').inner_text()=='23 Sticker auf deiner Packliste'
            assert record()['snapshot']==accepted['snapshot']
            assert record()['status']=='accepted'
            assert record()['packing']['recipient']['phase']=='packing'
            accepted=record()
            go('/trade-v2/requests/fatima?role=sender')
            assert page.locator('#waiting-title').inner_text()=='Fatima hat angenommen ✓'
            assert 'Wartet auf Fatima' not in page.locator('body').inner_text()
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            shot('06-valentin-accepted')
            page.reload();ready();assert record()==accepted
            page.get_by_role('link',name='Vorgeschlagenen Deal ansehen').click();ready()
            assert keys('receive')==[i['key'] for a in snapshot['receive'] for i in a['items']]
            assert keys('give')==[i['key'] for a in snapshot['give'] for i in a['items']]
            assert record()==accepted

            go('/trade-v2/requests/fatima?scenario=open&role=recipient')
            assert '?' in page.url and 'scenario' not in page.url
            before=record()
            page.locator('#decline-request').dblclick();ready()
            declined=record();assert declined['status']=='declined'
            assert declined['snapshot']==before['snapshot']
            assert declined['bindingCreatedAt']==before['bindingCreatedAt']
            page.locator('#accept-request').evaluate('(e)=>{for(let i=0;i<6;i++)e.dispatchEvent(new MouseEvent("click"))}')
            assert record()==declined
            shot('07-fatima-declined')
            role('sender')
            assert page.locator('#request-status').inner_text()=='Fatima hat die Tauschanfrage abgelehnt.'
            assert page.locator('#capacity-count').inner_text()=='2/3 ausgehend belegt'
            assert page.locator('#next-step').is_hidden()
            shot('08-valentin-declined')
            if width==390:shot('12-slot-after-decline')
            page.reload();ready();assert record()==declined

            go('/trade-v2/requests/fatima?scenario=open&role=recipient')
            page.locator('#accept-request').dblclick();ready()
            once=record()
            page.locator('#accept-request').evaluate('(e)=>{for(let i=0;i<8;i++)e.dispatchEvent(new MouseEvent("click"))}')
            assert record()==once and once['status']=='accepted'
            # Real timer boundary on an open receiver page; both roles share expiry.
            go('/trade-v2/requests/fatima?scenario=open&role=recipient')
            before=record();page.clock.install(time=before['bindingCreatedAt']);page.reload();ready()
            page.clock.fast_forward(86400000)
            assert record()['status']=='expired'
            assert page.locator('#decision-actions').is_hidden()
            expired=record()
            for action in ('accept','decline'):
                page.locator('#'+action+'-request').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))')
            assert record()==expired
            shot('09-fatima-expired')
            role('sender')
            assert page.locator('#capacity-count').inner_text()=='0/3 ausgehend belegt'  # Seed pending requests also expire.
            assert record()['expiresAt']==before['expiresAt']
            assert page.locator('#waiting-title').inner_text()=='Tauschanfrage abgelaufen'
            page.reload();ready();assert record()==expired
            # Every requested direct QA scenario/role entry is functional.
            for scenario in ('open','accepted','declined','expired'):
                for which in ('sender','recipient'):
                    go(f'/trade-v2/requests/fatima?scenario={scenario}&role={which}')
                    expected='pending' if scenario=='open' else scenario
                    assert record()['status']==expected
                    assert record()['origin']=='TOP_SUGGESTION'
                    saved=record();page.reload();ready();assert record()==saved
            results.append({'width':width,'mirror_decisions_slots_expiry':'PASS','responsive_input':'PASS'})
            context.close()

        context=browser.new_context();page=context.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        model=page.evaluate('''async()=>{
          const m=await import('/trade-v2/assets/requests.js');
          const fixture=JSON.parse(document.querySelector('#trade-data').textContent).deal;
          const assert=(v,label)=>{if(!v)throw Error(label);};
          for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL']){
            for(const action of ['accept','decline']){
              const s=m.initialState(2,1000);const r=m.send(s,{...fixture,origin},1000).request;
              const original=JSON.stringify(r.snapshot),before=r.bindingCreatedAt;
              const a=m.perspective(r,'sender'),b=m.perspective(r,'recipient');
              assert(a.receive===b.give && a.give===b.receive,'mirror references');
              assert(a.requestId===b.requestId && a.receive_count===b.give_count && a.album_count===6,'identity counts');
              assert(Object.isFrozen(r.snapshot.receive[0].items[0]),'deep frozen');
              assert(m.decide(s,r.id,'sender',action,1001)==='forbidden','sender cannot decide');
              const result=m.decide(s,r.id,'recipient',action,1002);
              const fixed=JSON.stringify(r);
              for(let i=0;i<20;i++)m.decide(s,r.id,'recipient',i%2?'accept':'decline',1003+i);
              assert(JSON.stringify(r)===fixed,'first transition wins');
              assert(r===s.requests[r.id] && Object.keys(s.requests).length===3,'same object, no second trade');
              assert(JSON.stringify(r.snapshot)===original && r.bindingCreatedAt===before,'snapshot and time stable');
              assert(m.slots(s,'outgoing',2000)===(action==='accept'?3:2),'sender slot');
              assert(m.incomingSlots(s,fixture.partner_id,2000)===(action==='accept'?1:0),'recipient slot');
              m.expire(s,1000+m.DAY);
              assert(r.status===result,'accepted/declined do not expire');
            }
          }
          for(const action of ['accept','decline']){
            const s=m.initialState();const r=m.send(s,fixture,1000).request;
            assert(m.decide(s,r.id,'recipient',action,1000+m.DAY)==='expired','deadline exclusive');
            assert(m.slots(s,'outgoing',1000+m.DAY)===0,'expiry frees slot');
            const before=JSON.stringify(r);m.decide(s,r.id,'recipient',action,1000+m.DAY+1);
            assert(JSON.stringify(r)===before,'expiry terminal');
            const valid=m.initialState();const v=m.send(valid,fixture,1000).request;
            assert(m.decide(valid,v.id,'recipient',action,1000+m.DAY-1)!=='expired','before deadline');
          }
          return 'PASS';
        }''')
        assert model=='PASS'
        context.close();browser.close()
    assert not errors,errors
    assert not mutations,mutations
    (OUT/'checks.json').write_text(json.dumps({'results':results,'model':model,'errors':errors,'external_or_write_requests':mutations},indent=2)+'\n')
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-03 Galerie</title><style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}</style><h1>TRADE-03 · Ein Request, zwei Perspektiven</h1><p><a href="../regression-01/index.html">Trade-01 Regression</a> · <a href="../regression-02/index.html">Trade-02 Regression</a></p><main>'+''.join(f'<figure><figcaption>{n}</figcaption><a href="{n}"><img src="{n}" alt="{n}" loading="lazy"></a></figure>' for n in images)+'</main></html>\n')
    print('PASS: 4 widths, exact mirror, accept/decline/expiry, roles, slots, double actions, all 8 direct scenarios; screenshots',len(images))


if __name__=='__main__':main()
