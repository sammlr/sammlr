"""Top-three refill, shared receive renderer and package confirmation UX evidence."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tests/research/artifacts/trade-08'
BASE='http://127.0.0.1:8095'
KEY='sammlr-trade-02'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    images,results,errors,writes=[],[],[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (375,390,430,1280):
            ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=True)
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') or not r.url.startswith(BASE) else None)
            page.on('response',lambda r:errors.append(str(r.status)+r.url) if r.status>=400 else None)
            def ready():
                page.wait_for_function('document.body.dataset.ready==="true"');page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,page.url)
            def go(path):page.goto(BASE+path);ready()
            def shot(name):
                ready();page.evaluate('Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{})))');file=f'{name}-{width}.png';page.screenshot(path=str(OUT/file),full_page=True);images.append(file)
            def record():return page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k)).requests["demo-fatima"]',KEY)
            go('/trade-v2/')
            assert page.locator('h1').inner_text()=='Tauschen'
            assert page.locator('.top-offer').count()==3 and page.locator('#partner-preview,#partner-list').count()==0
            assert '3 vielversprechende Tauschvorschläge für dich.' in page.locator('main').inner_text()
            rects=page.locator('.top-toggle').evaluate_all('(es)=>es.map(e=>e.getBoundingClientRect().y)');assert max(rects)-min(rects)<1
            assert page.locator('.top-stack .sticker-slot-frame').evaluate_all('(es)=>es.every(e=>Math.abs(parseFloat(getComputedStyle(e).width)-parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--trade-card-width")))<.1)')
            shot('01-top-three')
            page.locator('.top-toggle').first.tap();page.wait_for_url('**/deals/fatima');ready()
            assert page.locator('.pax-album-toggle').count()==6
            assert page.get_by_role('button',name='Tausch ansehen',exact=True).count()==0
            shot('02-compact-albums')
            page.locator('.pax-album-toggle').first.focus();page.keyboard.press('Enter')
            assert page.locator('.pax-receive-album.is-expanded').count()==1
            durations=page.evaluate('document.getAnimations().map(a=>a.effect.getTiming().duration)');assert 440 in durations
            page.locator('.pax-album-toggle').nth(1).tap();assert page.locator('.pax-receive-album.is-expanded').count()==2
            page.locator('.pax-album-fan .pj-simulation').first.tap();assert page.locator('.pax-receive-album.is-expanded').count()==1
            page.locator('.receive-all').tap();assert page.locator('.pax-receive-album.is-expanded').count()==6
            assert page.locator('.pax-fan-grid .sticker-slot-frame').count()==23
            shot('03-all-album-sectors')
            page.emulate_media(reduced_motion='reduce');page.locator('.pax-album-fan .pj-simulation').first.tap();page.locator('.pax-album-toggle').first.tap()
            assert page.evaluate('document.getAnimations().length')==0
            before=page.evaluate('(k)=>sessionStorage.getItem(k)',KEY)
            page.locator('#dismiss-proposal').tap();page.wait_for_url(BASE+'/trade-v2/');ready()
            assert page.locator('.top-name').all_text_contents()==['Justus','Marek','Luca']
            assert page.evaluate('(k)=>sessionStorage.getItem(k)',KEY)==before
            page.reload();ready();assert page.locator('[data-deal="demo-fatima"]').count()==0
            shot('04-refill-dismissed')
            page.locator('.top-toggle').first.tap();page.wait_for_url('**/deals/justus');ready()
            page.locator('#request-preview').tap();page.wait_for_url('**/requests/justus');ready()
            go('/trade-v2/');assert page.locator('.top-name').all_text_contents()==['Marek','Luca','Amadou']
            page.get_by_role('link',name='Laufende Tausche',exact=True).tap();page.wait_for_url('**/active');ready()
            assert 'Justus' in page.locator('#trade-active').inner_text();shot('05-active-requests')
            page.locator('#trade-active a').tap();page.wait_for_url('**/requests/justus?role=sender');ready()
            go('/trade-v2/partners');assert page.locator('h1').inner_text()=='Alle Sammlr';shot('06-all-sammlr')
            go('/trade-v2/deals/fatima?demo=3');assert page.locator('#request-preview').is_disabled()
            page.locator('#request-preview').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))');assert page.url.endswith('?demo=3') is False # seed stripped
            assert page.locator('#request-preview').is_disabled();shot('07-three-slots-blocked')
            go('/trade-v2/requests/fatima/next?pack=zero&role=sender');snapshot=record()['snapshot']
            assert page.locator('#pax-give-albums input,#pax-give-albums button,.pax-pack-mark').count()==0
            assert record()['packing']['sender']['packed']==[];shot('08-packlist-no-ticking')
            page.locator('#pack-review').tap();assert page.locator('#pack-report').is_disabled()
            for item in page.locator('[name=missing]').all()[-2:]:item.check()
            shot('09-select-missing-only');page.locator('#pack-report').tap()
            assert record()['snapshot']==snapshot and record()['amendment']['status']=='pending'
            page.locator('#pack-amendment').tap();page.wait_for_url('**/amendment?role=sender');ready()
            page.locator('.demo-tools').evaluate('(e)=>e.open=true');page.locator('#role-recipient').tap();page.wait_for_url('**/amendment?role=recipient');ready()
            page.locator('#amend-accept').tap();assert record()['deal_version']==2
            shot('10-amendment-still-works')
            go('/trade-v2/requests/fatima/next?pack=zero&role=sender')
            page.locator('#pack-finish').focus();page.keyboard.press('Space')
            assert record()['packing']['sender']['phase']=='packing_complete' and record()['shipping']['sender']['releasedVersion']==1
            assert page.locator('address').count()==1;assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt';shot('11-explicit-release-address')
            results.append({'width':width,'top3_refill_reload_slots':'PASS','receive_independent_all_keyboard_touch_motion':'PASS','whole_package_and_missing_amendment_address':'PASS','overflow':False});ctx.close()
        ctx=browser.new_context();page=ctx.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        model=page.evaluate('''async()=>{
          const q=await import('/trade-v2/assets/requests.js'),p=await import('/trade-v2/assets/packing.js'),a=await import('/trade-v2/assets/packing_confirmation.js');
          const f=JSON.parse(document.querySelector('#trade-data').textContent).deal;let checks=0;const check=(v,t)=>{checks++;if(!v)throw Error(t);};
          for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL'])for(const role of ['sender','recipient']){
            const s=q.initialState(),r=q.send(s,{...f,origin},1000).request;check(!a.confirmPackage(r,role),'pending');q.decide(s,r.id,'recipient','accept',1001);p.enterPacking(r,role);
            const before=JSON.stringify(r.snapshot),other=role==='sender'?'recipient':'sender';
            check(!a.reportMissing(r,role,[]),'empty');check(!a.reportMissing(r,role,['invented']),'unknown');
            check(a.confirmPackage(r,role),'package');check(r.packing[role].phase==='packing_complete','phase');check(r.shipping[role].releasedVersion===1,'conscious release');
            check(p.packSide(r,other).packed.length===0,'other preserved');check(JSON.stringify(r.snapshot)===before,'snapshot');
            const fixed=JSON.stringify(r);check(!a.confirmPackage(r,role)&&JSON.stringify(r)===fixed,'repeat');check(!a.reportMissing(r,role,[p.pieces(r,role)[0].key]),'late missing');
            const s2=q.initialState(),r2=q.send(s2,{...f,origin},1000).request;q.decide(s2,r2.id,'recipient','accept',1001);p.enterPacking(r2,role);
            const keys=p.pieces(r2,role).slice(-2).map(i=>i.key);check(a.reportMissing(r2,role,keys),'exact missing');check(JSON.stringify(r2.packing[role].missingReported)===JSON.stringify(keys),'keys');
            check(r2.packing[role].packed.length===21,'remaining explicitly declared');check(JSON.stringify(r2.snapshot)===before,'report snapshot');check(!r2.ownShipped&&!r2.recipientShipped,'no shipping');
          }return {assertions:checks,status:'PASS'};
        }''');ctx.close();browser.close()
    assert not errors,errors
    assert not writes,writes
    (OUT/'checks.json').write_text(json.dumps({'browser':results,'model':model,'errors':errors,'external_or_write_requests':writes,'screenshots':len(images)},indent=2)+'\n')
    style='<style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}</style>'
    figures=''.join(f'<figure><figcaption>{n}</figcaption><a href="{n}"><img src="{n}" alt="{n}" loading="lazy"></a></figure>' for n in images)
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-08 Galerie</title>'+style+'<h1>TRADE-08 · Tauschbörse</h1><p>'+' · '.join(f'<a href="regression-0{i}/index.html">TRADE-0{i}</a>' for i in range(1,8))+'</p><main>'+figures+'</main></html>\n')
    print('PASS:',model['assertions'],'adapter assertions;',len(images),'screenshots; four widths')


if __name__=='__main__':main()
