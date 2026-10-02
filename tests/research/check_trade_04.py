"""Isolated accepted-snapshot packing, interaction parity and browser evidence."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tests/research/artifacts/trade-04'
BASE = 'http://127.0.0.1:8095'
KEY = 'sammlr-trade-02'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    images, errors, mutations, results = [], [], [], []
    # TRADE-08 replaces marker ticking with explicit package confirmation.
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (375,390,430,1280):
            context = browser.new_context(viewport={'width':width,'height':900},has_touch=True)
            page = context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:errors.append(f'{r.status}: {r.url}') if r.status>=400 else None)
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') or not r.url.startswith(BASE) else None)
            def ready():
                page.wait_for_function('document.body.dataset.ready === "true"')
                page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width,page.url)
                assert page.locator('#pax-give-albums input,#pax-give-albums button,.pax-pack-mark,#request-clock').count()==0
                # TRADE-06 replaces the old shipping placeholder with an authorized address.
                if page.locator('address').count():
                    assert record()['packing'][record_role := page.locator('body').get_attribute('data-role')]['phase']=='packing_complete'
                    assert record()['shipping'][record_role]['releasedVersion']==record().get('deal_version',1)
            def go(scenario='zero',role='sender'):
                page.goto(f'{BASE}/trade-v2/requests/fatima/next?pack={scenario}&role={role}');ready()
            def state():return page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k))',KEY)
            def record():return state()['requests']['demo-fatima']
            def shot(name,locator=None):
                filename=f'{name}-{width}.png'
                if locator:locator.screenshot(path=str(OUT/filename))
                else:page.screenshot(path=str(OUT/filename),full_page=True)
                images.append(filename)
            def role(which):
                page.locator('.demo-tools').evaluate('(e)=>e.open=true')
                page.locator('#role-'+which).click();ready()
            go();snapshot=record()['snapshot']
            ownkeys=[i['key'] for a in snapshot['give'] for i in a['items']]
            assert page.locator('.pending-review-row').count()==23
            assert page.locator('#pack-finish').is_enabled()
            assert page.locator('#pack-progress').inner_text()=='23 Sticker auf deiner Packliste'
            assert record()['packing']['sender']['packed']==[]
            shot('01-packlist-without-ticks')
            page.locator('#pack-finish').focus();page.keyboard.press('Enter')
            assert record()['packing']['sender']['phase']=='packing_complete'
            assert record()['packing']['sender']['packed']==ownkeys
            assert record()['packing']['recipient']['packed']==[]
            assert record()['snapshot']==snapshot and not record()['ownShipped']
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            shot('02-whole-package-confirmed')
            role('recipient');assert page.locator('.pending-review-row').count()==23
            assert record()['packing']['recipient']['packed']==[]
            go('zero');before=record();page.locator('#pack-review').tap()
            assert page.locator('#pack-report').is_disabled()
            page.locator('[name=missing]').nth(21).check();page.locator('[name=missing]').nth(22).check()
            shot('03-exact-missing-selection')
            page.locator('#pack-return').tap();assert record()==before
            page.locator('#pack-review').tap()
            for checkbox in page.locator('[name=missing]').all()[-2:]:checkbox.check()
            page.locator('#pack-report').tap()
            assert record()['packing']['sender']['missingReported']==ownkeys[-2:]
            assert record()['snapshot']==before['snapshot']
            assert record()['amendment']['status']=='pending'
            shot('04-missing-reported')
            # QA entries and durable state on both roles.
            for which in ('sender','recipient'):
                for scenario,phase,count in [('zero','packing',0),('partial','packing',21),('22','packing',22),('23','packing',23),('complete','packing_complete',23),('review','missing_review',21),('reported','missing_reported',21)]:
                    go(scenario,which);r=record()
                    assert r['packing'][which]['phase']==phase and len(r['packing'][which]['packed'])==count
                    page.reload();ready();assert record()==r
            go();page.locator('.secondary-receive>summary').click()
            stacks=page.locator('.pax-album-toggle')
            if stacks.count()==0:stacks=page.locator('#pax-receive-albums button[aria-expanded]')
            assert stacks.count()==6
            stacks.first.click();assert stacks.first.get_attribute('aria-expanded')=='true'
            stacks.nth(1).click();assert stacks.first.get_attribute('aria-expanded')=='true'
            page.get_by_role('button',name='Zusammenlegen ↑').first.click();assert stacks.first.get_attribute('aria-expanded')=='false'
            if width==390:shot('09-secondary-receive')
            results.append({'width':width,'packing_roles_slots_missing_input_motion_layout':'PASS','direct_scenarios':14,'whole_package_confirmation':'PASS'})
            context.close()
        context=browser.new_context();page=context.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        model=page.evaluate('''async()=>{
          const m=await import('/trade-v2/assets/requests.js'),p=await import('/trade-v2/assets/packing.js');
          const fixture=JSON.parse(document.querySelector('#trade-data').textContent).deal;
          const assert=(v,label)=>{if(!v)throw Error(label)};
          for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL']){
            const s=m.initialState(2,1000),r=m.send(s,{...fixture,origin},1000).request;
            assert(!p.enterPacking(r,'sender'),'pending cannot pack');m.decide(s,r.id,'recipient','accept',1001);
            const snapshot=JSON.stringify(r.snapshot);p.enterPacking(r,'sender');p.enterPacking(r,'recipient');
            assert(p.validPacking(r),'valid initial');assert(!p.togglePiece(r,'sender','unknown'),'unknown position');
            p.pieces(r,'recipient').slice(0,4).forEach(i=>p.togglePiece(r,'recipient',i.key));
            p.pieces(r,'sender').slice(0,22).forEach(i=>p.togglePiece(r,'sender',i.key));
            assert(!p.packAction(r,'sender','finish'),'22 cannot finish');
            p.togglePiece(r,'sender',p.pieces(r,'sender')[22].key);assert(p.canFinish(r,'sender'),'23 full');
            assert(p.packAction(r,'sender','finish'),'finish');assert(p.validPacking(r),'valid complete');
            assert(p.packSide(r,'recipient').packed.length===4,'independent partner');
            assert(!p.togglePiece(r,'sender',p.pieces(r,'sender')[0].key),'terminal stable');
            assert(m.slots(s,'outgoing',2000)===3 && m.incomingSlots(s,fixture.partner_id,2000)===1,'slots retained');
            m.expire(s,1000+2*m.DAY);assert(r.status==='accepted','no pack deadline');
            assert(m.slots(s,'outgoing',1000+2*m.DAY)===1,'accepted still occupies slot');
            assert(JSON.stringify(r.snapshot)===snapshot,'unchanged snapshot');
            r.packing.sender.packed.pop();assert(!p.validPacking(r),'incomplete completed state invalid');
          }
          const duplicate=structuredClone(fixture),one=duplicate.give[0].items[0];
          duplicate.give=[{...duplicate.give[0],items:[one,{...one,instance:2,key:one.key+'::second'}]}];duplicate.give_count=2;
          const s=m.initialState(),r=m.send(s,duplicate,1000).request;m.decide(s,r.id,'recipient','accept',1001);p.enterPacking(r,'sender');
          const items=p.pieces(r,'sender');p.togglePiece(r,'sender',items[0].key);
          assert(p.missing(r,'sender').length===1 && !p.canFinish(r,'sender'),'copies counted separately');
          p.togglePiece(r,'sender',items[1].key);assert(p.canFinish(r,'sender'),'two instances full');
          return 'PASS: origins, duplicate instances, guards, immutable snapshot, independent states, retained slots, no expiry';
        }''')
        context.close();browser.close()
    assert not errors,errors
    assert not mutations,mutations
    (OUT/'checks.json').write_text(json.dumps({'results':results,'model':model,'no_per_piece_controls':True,'errors':errors,'external_or_write_requests':mutations},indent=2)+'\n')
    style='<style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}</style>'
    figures=lambda names:''.join(f'<figure><figcaption>{n}</figcaption><a href="{n}"><img src="{n}" alt="{n}" loading="lazy"></a></figure>' for n in names)
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-04 Galerie</title>'+style+'<h1>TRADE-04 · Packphase</h1><p><a href="marker.html">Marker-Vergleich</a> · <a href="demos.html">Direkte Demo-Einstiege</a> · <a href="regression-01/index.html">Trade-01</a> · <a href="regression-02/index.html">Trade-02</a> · <a href="regression-03/index.html">Trade-03</a></p><main>'+figures(images)+'</main></html>\n')
    (OUT/'marker.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><title>Marker-Vergleich</title>'+style+'<h1>TRADE-08: kein Packmarker</h1><p>Die Einzelmarkierung wurde ausdrücklich durch eine Gesamtbestätigung ersetzt.</p><main>'+figures([n for n in images if n.startswith('marker-')])+'</main></html>\n')
    links=''
    for scenario,label in [('zero','0/23'),('partial','21/23'),('22','22/23'),('23','23/23'),('complete','Packprüfung abgeschlossen'),('review','Fehlmengenreview'),('reported','Fehlmenge gemeldet')]:
        links+=f'<tr><th>{label}</th>'+''.join(f'<td><a href="{BASE}/trade-v2/requests/fatima/next?pack={scenario}&role={role}">{name}</a></td>' for role,name in [('sender','Valentin'),('recipient','Fatima')])+'</tr>'
    (OUT/'demos.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><title>TRADE-04 Demos</title>'+style+'<h1>Direkte Demo-Einstiege</h1><p>Diese Links setzen den lokalen Demo-Zustand im geöffneten Tab zurück.</p><table>'+links+'</table></html>\n')
    print('PASS:',len(results),'widths; all 14 demos; packing model; interaction parity;',len(images),'screenshots')


if __name__=='__main__':main()
