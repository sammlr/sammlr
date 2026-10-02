"""Directional shipping/address gate and responsive browser evidence; local only."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tests/research/artifacts/trade-06'
BASE='http://127.0.0.1:8095'
KEY='sammlr-trade-02'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    images,results,errors,mutations=[],[],[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (375,390,430,1280):
            context=browser.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce')
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:errors.append(f'{r.status}: {r.url}') if r.status>=400 else None)
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') or not r.url.startswith(BASE) else None)
            def record():return page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k)).requests["demo-fatima"]',KEY)
            def ready():
                page.wait_for_function('document.body.dataset.ready==="true"');page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,page.url)
                assert not re.search(r'\bpax\b|sammlrpax|booster',page.locator('body').inner_text(),re.I)
                assert page.get_by_role('button',name=re.compile(r'^(Erhalten|Alles angekommen|Problem melden|Sterne vergeben)$')).count()==0
            def go(scenario,role='sender'):
                page.goto(f'{BASE}/trade-v2/requests/fatima/shipping?ship={scenario}&role={role}')
                if scenario=='amendment-blocked':page.wait_for_url(f'**/amendment?role={role}')
                ready()
            def shot(name,locator=None):
                filename=f'{name}-{width}.png'
                if locator:locator.screenshot(path=str(OUT/filename))
                else:page.screenshot(path=str(OUT/filename),full_page=True)
                images.append(filename)
            def role(side):
                page.locator('.demo-tools').evaluate('(e)=>e.open=true');page.locator('#role-'+side).tap();ready()
            def no_address():
                assert page.locator('address').count()==0
                html=page.content()
                for text in ('Valentin Beispiel (Demo)','Fatima Beispiel (Demo)','Erfundene Musterstraße','Erfundener Beispielweg','00000 Musterstadt','00000 Beispielstadt'):
                    assert text not in html,text
            # The real finish action, not just a shipping seed, releases the correct address.
            page.goto(BASE+'/trade-v2/requests/fatima/next?pack=22&role=sender');ready();no_address()
            assert page.locator('#pack-finish').is_enabled()
            assert page.locator('.pax-pack-item,.pax-pack-mark').count()==0;no_address()
            if width==390:shot('01-all-marked-before-release')
            snapshot=record()['snapshot'];page.locator('#pack-finish').focus();page.keyboard.press('Enter')
            assert record()['shipping']['sender']['releasedVersion']==1
            assert 'Fatima Beispiel (Demo)' in page.locator('address').inner_text()
            assert 'Valentin Beispiel (Demo)' not in page.content()
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            shot('02-yellow-address')
            if width==390:shot('02b-address-note',page.locator('#ship-address-note'))
            released=record();page.reload();ready();assert record()==released
            page.locator('#ship-prepare').tap();assert record()==released
            if width==390:shot('04-prepare-shipping')
            page.locator('#ship-method').select_option('brief');assert not record()['ownShipped']
            assert page.locator('#ship-confirm').is_enabled()
            if width==390:shot('06-ready-to-ship')
            selected=record();page.locator('#ship-portal').click()
            assert record()==selected and not record()['ownShipped']
            shot('05-local-portal')
            page.locator('#ship-portal-back').focus();page.keyboard.press('Space')
            assert record()==selected
            if width==390:shot('07-before-confirmation')
            page.locator('#ship-confirm').focus();assert page.locator('#ship-confirm').evaluate('(e)=>getComputedStyle(e).outlineStyle')!='none'
            # Dispatch repeated clicks against the same old control: only one command has effect.
            page.locator('#ship-confirm').evaluate('(e)=>{for(let i=0;i<8;i++)e.dispatchEvent(new MouseEvent("click"))}')
            assert record()['ownShipped'] and not record().get('recipientShipped')
            assert record()['snapshot']==snapshot and record()['status']=='accepted'
            assert page.locator('#capacity-count').inner_text()=='2/3 ausgehend belegt'
            assert page.locator('#ship-heading').inner_text()=='Deine Sticker sind unterwegs ✓'
            no_address();shot('08-valentin-shipped-fatima-packing')
            sent=record();page.reload();ready();assert record()==sent;no_address()
            assert page.locator('#ship-confirm').count()==0
            # Own hidden historical controls cannot alter packing after shipment.
            page.locator('#pack-finish').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))');assert record()==sent
            page.locator('#pack-report').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))');assert record()==sent
            role('recipient');assert record()['ownShipped'] and not record().get('recipientShipped');no_address()
            assert 'Valentins Sticker sind unterwegs' in page.locator('#pack-subtitle').inner_text()
            if width==390:shot('09-fatima-sees-valentin-shipped')
            assert page.locator('#capacity-count').inner_text()=='1/3 eingehend belegt'
            assert len(record()['packing']['recipient']['packed'])==0
            for item in page.locator('.pax-pack-item').all()[1:]:item.click()
            page.locator('#pack-finish').tap();assert 'Valentin Beispiel (Demo)' in page.locator('address').inner_text()
            assert 'Fatima Beispiel (Demo)' not in page.content()
            page.locator('#ship-prepare').click();page.locator('#ship-method').select_option('brief')
            # Shipping outside the optional portal works; no portal visit on this side.
            page.locator('#ship-confirm').dblclick()
            assert record()['recipientShipped'] and record()['ownShipped']
            assert record()['status']=='accepted' and record()['deal_version']==1
            assert page.locator('#ship-heading').inner_text()=='Beide Sendungen sind unterwegs ✓'
            assert page.locator('#capacity-count').inner_text()=='0/3 eingehend belegt';no_address()
            shot('11-both-shipped')
            both=record();role('sender');assert record()==both and page.locator('#capacity-count').inner_text()=='2/3 ausgehend belegt'
            if width==390:page.locator('.demo-tools').evaluate('(e)=>e.open=true');shot('16-dev-independent-shipping')
            # Secondary address is only created on deliberate details opening, cleared on closing.
            page.locator('#ship-details summary').click();assert 'Fatima Beispiel (Demo)' in page.locator('address').inner_text()
            page.locator('#ship-details summary').click();page.wait_for_function('document.querySelectorAll("address").length===0')
            go('partner-first');no_address();assert 'Fatimas Sticker sind unterwegs' in page.locator('#ship-heading').inner_text()
            assert record()['recipientShipped'] and not record()['ownShipped']
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            if width==390:shot('10-fatima-shipped-valentin-packing')
            go('long');address=page.locator('address');assert '123 B' in address.inner_text();assert address.evaluate('(e)=>e.scrollWidth<=e.clientWidth')
            shot('03-long-demo-address')
            go('consent-blocked');no_address();assert 'Adressinhaber' in page.locator('#ship-panel').inner_text()
            go('locked');no_address()
            if width==390:shot('14-address-blocked')
            go('full-unreleased');no_address()
            # V2 naturally enters from amendment, then requires a conscious fresh release.
            page.goto(BASE+'/trade-v2/requests/fatima/amendment?amend=accepted&role=sender');ready();no_address()
            page.goto(BASE+'/trade-v2/requests/fatima/shipping?role=sender');ready();no_address()
            assert page.locator('#ship-release').is_visible();page.locator('#ship-release').tap()
            assert record()['deal_version']==2 and len(record()['packing']['sender']['packed'])==21
            assert 'Fatima Beispiel (Demo)' in page.locator('address').inner_text()
            shot('12-v2-address')
            page.locator('#ship-prepare').click();page.locator('#ship-method').select_option('brief');page.locator('#ship-confirm').tap()
            assert record()['ownShipped'] and record()['deal_version']==2 and record()['snapshot']['give_count']==21
            shot('13-v2-shipped');no_address()
            role('recipient');assert 'Valentins Sticker sind unterwegs' in page.locator('#ship-heading').inner_text();no_address()
            page.goto(BASE+'/trade-v2/requests/fatima/next?role=recipient');ready()
            assert page.locator('#pack-progress').inner_text()=='21 Sticker auf deiner Packliste'
            page.locator('#pack-review').click();page.locator('[name=missing]').last.check();page.locator('#pack-report').click();page.locator('#pack-amendment').click();ready()
            assert 'nicht mehr möglich' in page.locator('#amend-title').inner_text()
            assert record()['deal_version']==2 and record()['amendment']['status']=='accepted'
            if width==390:shot('15-amendment-blocked-after-shipment')
            # Reopen before shipping removes release/address but retains physical marks.
            go('address');page.locator('#ship-reopen').click();no_address()
            assert record()['packing']['sender']['phase']=='packing' and len(record()['packing']['sender']['packed'])==23
            # Every explicit QA seed remains stable through read-only role switches and reload.
            for scenario in ('address','ready','me-packing','me-complete','me-ready','both','partner-first','v2-address','v2-ready','v2-shipped','locked','amendment-blocked','long','consent-blocked','full-unreleased'):
                go(scenario);before=record()
                if scenario=='amendment-blocked':assert 'nicht mehr möglich' in page.locator('#amend-title').inner_text()
                if scenario=='me-complete':assert before['packing']['recipient']['phase']=='packing_complete' and before['shipping']['recipient']['releasedVersion'] is None
                if scenario=='me-ready':assert before['shipping']['recipient']['releasedVersion']==1 and not before.get('recipientShipped')
                page.reload();ready();assert record()==before
                role('recipient');assert record()==before;role('sender');assert record()==before
            results.append({'width':width,'address_direction_dom_slots_shipping_v1_v2_input_motion':'PASS','qa_scenarios':15})
            context.close()
        context=browser.new_context();page=context.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        source=(ROOT/'tests/research/trade_06_model.js').read_text()
        model=page.evaluate('''async(source)=>{const module=await import(URL.createObjectURL(new Blob([source],{type:'text/javascript'})));return module.check(JSON.parse(document.querySelector('#trade-data').textContent).deal);}''',source)
        context.close();browser.close()
    assert not errors,errors
    assert not mutations,mutations
    (OUT/'checks.json').write_text(json.dumps({'browser':results,'model':model,'errors':errors,'external_or_write_requests':mutations},indent=2)+'\n')
    style='<style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}td,th{padding:10px;text-align:left}</style>'
    figures=''.join(f'<figure><figcaption>{n}</figcaption><a href="{n}"><img src="{n}" alt="{n}" loading="lazy"></a></figure>' for n in images)
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-06 Galerie</title>'+style+'<h1>TRADE-06 · Eigener Versand</h1><p><a href="demos.html">Direkte Demos</a> · '+' · '.join(f'<a href="regression-0{i}/index.html">TRADE-0{i}</a>' for i in (1,2,3,4,5))+'</p><main>'+figures+'</main></html>\n')
    rows=''
    for scenario,label in [('address','Packfreigabe / Adresse'),('ready','Bereit zum Versand'),('me-packing','Valentin unterwegs, Fatima packt'),('me-complete','Valentin unterwegs, Fatima Packprüfung vollständig'),('me-ready','Valentin unterwegs, Fatima versandbereit'),('both','Beide unterwegs'),('partner-first','Fatima zuerst unterwegs'),('v2-address','V2 Adresse'),('v2-ready','V2 bereit'),('v2-shipped','V2 unterwegs'),('locked','Unvollständig: Adresse gesperrt'),('amendment-blocked','Versandt: Amendment gesperrt'),('long','Lange Demoadresse'),('consent-blocked','Eigentümerfreigabe fehlt'),('full-unreleased','23 markiert, noch nicht freigegeben')]:
        rows+=f'<tr><th>{label}</th>'+''.join(f'<td><a href="{BASE}/trade-v2/requests/fatima/shipping?ship={scenario}&role={role}">{name}</a></td>' for role,name in [('sender','Valentin'),('recipient','Fatima')])+'</tr>'
    (OUT/'demos.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-06 Demos</title>'+style+'<h1>TRADE-06 · Direkte Demos</h1><p>Diese Links setzen nur den lokalen Demo-Zustand im geöffneten Tab zurück.</p><table>'+rows+'</table></html>\n')
    print('PASS: four widths;',model['assertions'],'model assertions;',len(images),'screenshots; address privacy, both directions, slots, V1/V2, races, frozen packing')


if __name__=='__main__':main()
