"""TRADE-05 browser and model gate; no production mutations."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tests/research/artifacts/trade-05'
BASE = 'http://127.0.0.1:8095'
KEY = 'sammlr-trade-02'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    images, results, errors, mutations = [], [], [], []
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (375,390,430,1280):
            context=browser.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce')
            page=context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:errors.append(f'{r.status}: {r.url}') if r.status>=400 else None)
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') or not r.url.startswith(BASE) else None)
            def ready():
                page.wait_for_function('document.body.dataset.ready === "true"');page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),page.url
                assert not re.search(r'\bpax\b|sammlrpax|booster|dhl',page.locator('body').inner_text(),re.I)
                assert page.locator('address').count()==0
                assert page.locator('#pax-give-albums input,#pax-give-albums button').count()==0
            def go(scenario,role='sender'):
                page.goto(f'{BASE}/trade-v2/requests/fatima/amendment?amend={scenario}&role={role}');ready()
            def state():return page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k))',KEY)
            def record():return state()['requests']['demo-fatima']
            def role(which):
                page.locator('.demo-tools').evaluate('(e)=>e.open=true');page.locator('#role-'+which).tap();ready()
            def shot(name,locator=None):
                filename=f'{name}-{width}.png'
                if locator:locator.screenshot(path=str(OUT/filename))
                else:page.screenshot(path=str(OUT/filename),full_page=True)
                images.append(filename)
            # Actual TRADE-04 report -> generated pending amendment, no direct-demo shortcut.
            page.goto(BASE+'/trade-v2/requests/fatima/next?pack=partial&role=sender');ready()
            original=record()['snapshot'];own=[i['key'] for a in original['give'] for i in a['items']];other=[i['key'] for a in original['receive'] for i in a['items']]
            if width==390:shot('01-packing-21')
            page.locator('#pack-review').click()
            for checkbox in page.locator('[name=missing]').all()[-2:]:checkbox.check()
            page.locator('#pack-report').tap()
            assert record()['snapshot']==original and record()['amendment']['status']=='pending'
            if width==390:shot('01b-missing-reported')
            page.locator('#pack-amendment').click();ready()
            assert page.locator('#amend-title').inner_text()=='Wartet auf Fatima.'
            assert page.locator('#amend-actions').is_hidden()
            assert record()['deal_version']==1
            assert record()['amendment']['proposal']['snapshot']['give_count']==21
            shot('02-valentin-waiting')
            pending=record();page.reload();ready();assert record()==pending
            # Hidden controls cannot self-accept.
            page.locator('#amend-accept').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))')
            assert record()==pending
            role('recipient');assert record()==pending
            assert page.locator('#amend-own-removed li').evaluate_all('(es)=>es.map(e=>e.dataset.itemKey)')==own[-2:]
            assert page.locator('#amend-counter-removed li').evaluate_all('(es)=>es.map(e=>e.dataset.itemKey)')==other[-2:]
            assert page.locator('#amend-before').inner_text()=='23 ↔ 23'
            assert page.locator('#amend-after').inner_text()=='21 ↔ 21'
            shot('03-fatima-proposal')
            if width==390:
                shot('04-missing-positions',page.locator('.amend-changes').first);shot('05-counter-positions',page.locator('.amend-changes').nth(1));shot('06-before-after',page.locator('.amend-size'))
                page.locator('.demo-tools').evaluate('(e)=>e.open=true');shot('13-dev-v1')
            page.locator('#amend-accept').focus();page.keyboard.press('Tab');assert page.evaluate('document.activeElement.id')=='amend-cancel'
            page.keyboard.press('Shift+Tab');assert page.evaluate('document.activeElement.id')=='amend-accept'
            assert page.locator('#amend-accept').evaluate('(e)=>getComputedStyle(e).outlineStyle')!='none'
            page.keyboard.press('Space')
            assert record()['deal_version']==2 and record()['snapshot']['give_count']==21
            accepted=record()
            for id in ('amend-accept','amend-cancel'):
                page.locator('#'+id).evaluate('(e)=>{for(let i=0;i<8;i++)e.dispatchEvent(new MouseEvent("click"))}')
            assert record()==accepted
            shot('07-fatima-accepted')
            role('sender');assert record()==accepted
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            page.locator('#amend-pack').click();ready()
            assert page.locator('#pack-progress').inner_text()=='21 Sticker auf deiner Packliste'
            assert page.locator('.pending-review-row').count()==21 and page.locator('.pax-pack-item').count()==0
            assert page.locator('.pax-pack-item').evaluate_all('(es)=>es.every(e=>e.disabled && e.getAttribute("aria-pressed")==="true")')
            shot('08-valentin-v2-packed')
            assert record()['snapshot']==accepted['snapshot']
            # The explicit QA counterpart had 12 packed, one removal among them -> 11/21.
            go('partial-before','recipient');assert len(record()['packing']['recipient']['packed'])==12
            page.locator('#amend-accept').dblclick();assert record()['deal_version']==2
            assert len(record()['packing']['recipient']['packed'])==11
            if width==390:page.locator('.demo-tools').evaluate('(e)=>e.open=true');shot('14-dev-v2')
            page.locator('#amend-pack').click();ready()
            assert page.locator('#pack-progress').inner_text()=='21 Sticker auf deiner Packliste'
            assert page.locator('.pending-review-row').count()==21 and page.locator('.pax-pack-item').count()==0
            shot('09-fatima-progress-retained')
            page.reload();ready();assert page.locator('#pack-progress').inner_text()=='21 Sticker auf deiner Packliste'
            # Active detail and request views also consume V2, not the fallback 23 fixture.
            page.goto(BASE+'/trade-v2/requests/fatima?role=sender&view=deal');ready()
            assert '21 ↔ 21' in page.locator('#request-summary').inner_text()
            assert page.locator('.pending-review-row').count()==21
            page.goto(BASE+'/trade-v2/deals/fatima');ready()
            assert '21 ↔ 21' in page.locator('.deal-summary').inner_text()
            assert page.locator('.pending-review-row').count()==21
            go('proposal','recipient');page.locator('#amend-cancel').focus();page.keyboard.press('Enter')
            cancelled=record();assert cancelled['status']=='cancelled'
            assert page.locator('#capacity-count').inner_text()=='0/3 eingehend belegt'
            shot('10-fatima-cancelled')
            for id in ('amend-cancel','amend-accept'):
                page.locator('#'+id).evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))')
            assert record()==cancelled
            role('sender');assert page.locator('#capacity-count').inner_text()=='2/3 ausgehend belegt'
            assert page.locator('#amend-title').inner_text()=='Der Tausch wurde beendet.'
            shot('11-valentin-cancelled')
            page.goto(BASE+'/trade-v2/requests/fatima/next?role=sender');page.wait_for_url('**/amendment?role=sender');ready()
            assert record()==cancelled
            page.goto(BASE+'/trade-v2/requests/fatima?role=sender');ready();assert page.locator('#waiting-title').inner_text()=='Der Tausch wurde beendet.'
            assert page.locator('#next-step').is_hidden()
            go('shipped','recipient');before=record();assert page.locator('#amend-actions').is_hidden()
            assert 'nicht mehr möglich' in page.locator('#amend-title').inner_text()
            assert before['snapshot']['give_count']==23 and 'amendment' not in before
            if width==390:shot('12-shipped-blocked')
            go('empty','recipient');assert page.locator('#amend-accept').is_hidden()
            assert record()['snapshot']['give_count']==23 and not record()['amendment']['proposal']['continuable']
            if width==390:shot('15-empty-proposal')
            page.locator('#amend-cancel').tap();assert record()['status']=='cancelled'
            go('second','recipient');assert page.locator('#amend-title').inner_text()=='Weitere Änderung erforderlich'
            assert record()['deal_version']==2 and record()['amendment']['status']=='accepted'
            # Every direct entry survives reload and role changes without a second proposal.
            for scenario in ('missing','waiting','proposal','accepted','cancelled','partial-before','partial-after','shipped','empty','second'):
                go(scenario,'recipient' if scenario in ('proposal','partial-before','partial-after','second') else 'sender')
                before=record();page.reload();ready()
                assert record()==before,(scenario,width)
            results.append({'width':width,'journey_versions_marks_slots_races_keyboard_touch':'PASS','horizontal_overflow':False})
            context.close()
        context=browser.new_context();page=context.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        source=(ROOT/'tests/research/trade_05_model.js').read_text()
        # Import a blob module in the preview's origin so actual app modules resolve normally.
        model=page.evaluate('''async(source)=>{const url=URL.createObjectURL(new Blob([source],{type:'text/javascript'}));const test=await import(url);return test.check(JSON.parse(document.querySelector('#trade-data').textContent).deal);}''',source)
        context.close();browser.close()
    assert not errors,errors
    assert not mutations,mutations
    (OUT/'checks.json').write_text(json.dumps({'browser':results,'model':model,'errors':errors,'external_or_write_requests':mutations},indent=2)+'\n')
    style='<style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}td,th{padding:10px;text-align:left}</style>'
    figures=''.join(f'<figure><figcaption>{name}</figcaption><a href="{name}"><img src="{name}" alt="{name}" loading="lazy"></a></figure>' for name in images)
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-05 Galerie</title>'+style+'<h1>TRADE-05 · Bestätigte Änderung</h1><p><a href="demos.html">Direkte Demos</a> · '+ ' · '.join(f'<a href="regression-0{i}/index.html">TRADE-0{i}</a>' for i in (1,2,3,4))+'</p><main>'+figures+'</main></html>\n')
    rows=''
    for scenario,label in [('missing','Fehlmenge gemeldet'),('waiting','Wartet auf Zustimmung'),('proposal','Vorschlag prüfen'),('accepted','Änderung angenommen'),('cancelled','Tausch beendet'),('partial-before','Fatima 12/23 vor Zustimmung'),('partial-after','Fatima 11/21 nach Zustimmung'),('shipped','Versand blockiert Änderung'),('empty','Leerer Restdeal'),('second','Weitere Änderung erforderlich')]:
        rows+=f'<tr><th>{label}</th>'+''.join(f'<td><a href="{BASE}/trade-v2/requests/fatima/amendment?amend={scenario}&role={role}">{name}</a></td>' for role,name in [('sender','Valentin'),('recipient','Fatima')])+'</tr>'
    (OUT/'demos.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-05 Demos</title>'+style+'<h1>TRADE-05 · Direkte Demos</h1><p>Die Links setzen nur den lokalen Demo-Zustand im geöffneten Tab zurück.</p><table>'+rows+'</table></html>\n')
    print('PASS: four widths; actual report/accept/cancel journeys;',model['assertions'],'model assertions;',len(images),'screenshots')


if __name__=='__main__':main()
