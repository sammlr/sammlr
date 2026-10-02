"""Full UI-only lifecycle, shared problem resolution, Q2 and responsive evidence."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tests/research/artifacts/trade-07'
BASE='http://127.0.0.1:8095'
KEY='sammlr-trade-02'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    images,results,errors,mutations=[],[],[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (375,390,430,1280):
            ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce')
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:errors.append(f'{r.status}: {r.url}') if r.status>=400 else None)
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') or not r.url.startswith(BASE) else None)
            def ready():
                page.wait_for_function('document.body.dataset.ready==="true"');page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,page.url)
                assert not re.search(r'\bpax\b|sammlrpax|booster',page.locator('body').inner_text(),re.I)
            def record():return page.evaluate('(key)=>JSON.parse(sessionStorage.getItem(key)).requests["demo-fatima"]',KEY)
            def snapshot_guard(r):return {k:r.get(k) for k in ('snapshot','deal_version','dealVersions','packing','shipping','ownShipped','recipientShipped','status')}
            def shot(name,all_widths=False):
                ready()
                if width!=390 and not all_widths:return
                name=f'{name}-{width}.png';page.screenshot(path=str(OUT/name),full_page=True);images.append(name)
            def roles(side,screen):
                page.locator('.demo-tools').evaluate('(e)=>e.open=true');page.locator('#role-'+side).tap();page.wait_for_url(f'**/{screen}?role={side}');ready()
            def demo(name,role='sender'):
                page.goto(f'{BASE}/trade-v2/requests/fatima/receipt?receipt={name}&role={role}');ready()
            def receive():
                page.locator('#receipt-receive').focus();page.keyboard.press('Enter');assert record()['receipts'][page.locator('body').get_attribute('data-role')]['state']=='RECEIVED_UNCHECKED'
            def ship():
                for item in page.locator('.pax-pack-item').all():item.click()
                page.locator('#pack-finish').tap();page.locator('#ship-prepare').tap();page.locator('#ship-method').select_option('brief');page.locator('#ship-confirm').tap()
            # Mandatory E2E: brand-new browser session. No seeds or storage writes by the test.
            page.goto(BASE+'/trade-v2/');ready()
            page.locator('[data-deal="demo-fatima"] a').tap();page.wait_for_url('**/deals/fatima');ready()
            page.locator('#request-preview').tap();page.wait_for_url('**/requests/fatima');ready()
            page.locator('.demo-tools').evaluate('(e)=>e.open=true');page.locator('#role-recipient').tap();page.wait_for_url('**/requests/fatima?role=recipient');ready()
            page.locator('#accept-request').tap();assert record()['status']=='accepted'
            page.locator('.demo-tools').evaluate('(e)=>e.open=true');page.locator('#role-sender').tap();page.wait_for_url('**/requests/fatima?role=sender');ready()
            page.locator('#next-step').tap();page.wait_for_url('**/next?role=sender');ready();ship()
            roles('recipient','next');ship();assert record()['ownShipped'] and record()['recipientShipped']
            roles('sender','next');page.locator('#receipt-link').tap();page.wait_for_url('**/receipt?role=sender');ready()
            original=snapshot_guard(record());shot('01-partner-underway',True)
            receive();shot('02-received',True);shot('03-everything-there')
            page.locator('#receipt-ok').evaluate('(e)=>{for(let i=0;i<8;i++)e.click()}');assert record()['receipts']['sender']['state']=='RECEIVED_OK'
            assert not record().get('completedAt');shot('04-everything-confirmed',True);shot('12-one-final-other-waiting')
            roles('recipient','receipt');receive();page.locator('#receipt-ok').tap();assert record()['completedAt']
            assert snapshot_guard(record())==original;shot('13-completed-v1',True)
            roles('sender','receipt');shot('15-rating-empty')
            assert page.locator('#rating-save').is_disabled()
            for n in (1,2,3):
                radio=page.get_by_role('radio',name=f'{n} '+('Stern' if n==1 else 'Sterne'),exact=True);radio.focus();page.keyboard.press('Space')
                assert radio.is_checked();assert radio.evaluate('(e)=>getComputedStyle(e).outlineStyle')!='none'
                shot(f'{15+n:02}-rating-{n}',n==3)
            page.locator('#rating-save').evaluate('(e)=>{for(let i=0;i<8;i++)e.click()}')
            assert record()['ratings']['sender']['stars']==3 and not record()['ratings'].get('recipient');shot('19-rating-saved',True)
            saved=record();page.reload();ready();assert record()==saved
            assert page.locator('#rating-form').count()==0
            page.locator('.demo-tools').evaluate('(e)=>e.open=true');shot('24-dev-completed-separate-ratings')
            page.get_by_role('link',name='Zurück zur Tauschbörse',exact=True).tap();page.wait_for_url(BASE+'/trade-v2/');ready()
            assert page.locator('[data-deal="demo-fatima"]').count()==0
            assert page.locator('#trade-history a').count()==1;shot('20-history',True)
            page.locator('#trade-history a').tap();page.wait_for_url('**/receipt');ready();assert record()==saved;shot('21-final-from-history')
            # Independent problem journey starts BOTH_SHIPPED, then only real controls.
            demo('waiting');original=snapshot_guard(record());receive();page.locator('#receipt-problem').tap();shot('05-problem-types',True)
            page.locator('#problem-submit').tap();assert 'Bitte' in page.locator('#problem-error').inner_text()
            page.get_by_role('checkbox',name='Sticker fehlt',exact=True).check()
            expected=page.locator('[name=position]');expected.nth(2).check();expected.nth(3).check();shot('06-affected-stickers',True)
            page.locator('#problem-submit').evaluate('(e)=>{for(let i=0;i<8;i++)e.click()}');shot('07-problem-reported',True)
            problem=record()['receipts']['sender']['problem'];assert len(problem['positionIds'])==2
            before=record();page.reload();ready();assert record()==before
            page.locator('.demo-tools').evaluate('(e)=>e.open=true');shot('23-dev-problem')
            roles('recipient','receipt');assert record()['receipts']['sender']['problem']==problem;shot('08-partner-problem',True)
            assert page.locator('#resolution-confirm').count()==0
            page.locator('#resolution-propose').evaluate('(e)=>{for(let i=0;i<8;i++)e.click()}');assert record()['receipts']['sender']['state']=='RESOLUTION_PENDING';shot('09-partner-proposes-resolution',True)
            roles('sender','receipt');shot('10-reporter-confirms-resolution',True)
            page.locator('#resolution-confirm').evaluate('(e)=>{for(let i=0;i<8;i++)e.click()}');assert record()['receipts']['sender']['state']=='RESOLVED';shot('11-resolved',True)
            assert not record().get('completedAt') and not record().get('ratings')
            roles('recipient','receipt');receive();page.locator('#receipt-ok').tap()
            assert record()['completedAt'] and not record().get('ratings') and snapshot_guard(record())==original
            assert page.locator('#rating-form').is_visible();assert 'geklärtem Problem' in page.locator('#receipt-panel').inner_text()
            # Q2: no partner SHIPPED, actual receipt + problem still allowed, slots unchanged.
            demo('q2-waiting');q2=snapshot_guard(record());capacity=page.locator('#capacity-count').inner_text();assert not record().get('recipientShipped')
            receive();shot('22-q2-received-without-partner-shipped',True)
            page.locator('#receipt-problem').tap();page.get_by_role('checkbox',name='Falscher Sticker',exact=True).check();page.locator('[name=position]').first.check();page.locator('#problem-submit').tap()
            assert snapshot_guard(record())==q2 and page.locator('#capacity-count').inner_text()==capacity;shot('25-q2-problem',True)
            roles('recipient','receipt');assert page.locator('#capacity-count').inner_text()=='1/3 eingehend belegt';page.locator('#resolution-propose').tap()
            roles('sender','receipt');page.locator('#resolution-confirm').tap();assert snapshot_guard(record())==q2
            demo('q2-ready-received');assert record()['receipts']['sender']['state']=='RECEIVED_OK' and not record().get('recipientShipped')
            assert record()['shipping']['recipient']['releasedVersion']==1 and record()['shipping']['recipient']['shippedAt'] is None
            shot('27-q2-ready-partner-received-ok',True)
            demo('q2-completed');assert record()['completedAt'] and not record()['ownShipped'] and not record().get('recipientShipped')
            assert page.locator('#capacity-count').inner_text()=='3/3 ausgehend belegt'
            page.get_by_role('link',name='Eigene Sendung bearbeiten →').tap();page.wait_for_url('**/shipping?role=sender');ready()
            page.locator('#ship-prepare').tap();page.locator('#ship-method').select_option('brief');page.locator('#ship-confirm').tap()
            assert record()['ownShipped'] and record()['completedAt'];assert page.locator('#capacity-count').inner_text()=='2/3 ausgehend belegt'
            page.locator('#receipt-link').tap();page.wait_for_url('**/receipt?role=sender');ready();assert page.locator('#rating-form').is_visible()
            # Other mandatory direct states and exact V2 quantity.
            demo('completed-v2');assert record()['deal_version']==2 and record()['snapshot']['receive_count']==21
            assert '21 ↔ 21' in page.locator('#receipt-panel').inner_text();shot('14-completed-v2',True)
            page.get_by_role('link',name='Später',exact=True).tap();page.wait_for_url(BASE+'/trade-v2/');ready();assert not record().get('ratings')
            demo('cancelled');assert page.locator('#receipt-receive').count()==0 and page.locator('#rating-form').count()==0;shot('26-cancelled')
            # Pending/absent direct URL cannot perform any receipt mutation.
            page.goto(BASE+'/trade-v2/deals/fatima?demo=0');ready();page.goto(BASE+'/trade-v2/requests/fatima/receipt');ready();assert page.locator('#receipt-receive').count()==0
            if width==390:
                demos=page.evaluate("async()=> (await import('/trade-v2/assets/receipt_demo.js')).RECEIPT_DEMOS")
                for name in demos:
                    side='recipient' if name in ('partner-problem','resolution-pending') else 'sender'
                    demo(name,side);before=record();page.reload();ready();assert record()==before
                    roles('recipient' if side=='sender' else 'sender','receipt');assert record()==before
            results.append({'width':width,'full_ui_e2e':'PASS','problem_e2e':'PASS','q2_without_shipping':'PASS','snapshot_slots_immutable':'PASS','responsive_touch_keyboard_reduced_motion':'PASS'})
            ctx.close()
        ctx=browser.new_context();page=ctx.new_page();page.goto(BASE+'/trade-v2/deals/fatima')
        source=(ROOT/'tests/research/trade_07_model.js').read_text()
        model=page.evaluate("""async(source)=>{const m=await import(URL.createObjectURL(new Blob([source],{type:'text/javascript'})));return m.check(JSON.parse(document.querySelector('#trade-data').textContent).deal);} """,source)
        ctx.close();browser.close()
    assert not errors,errors
    assert not mutations,mutations
    (OUT/'checks.json').write_text(json.dumps({'browser':results,'model':model,'errors':errors,'external_or_write_requests':mutations,'screenshots':len(images)},indent=2)+'\n')
    style='<style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%;height:auto}td,th{padding:10px;text-align:left}</style>'
    figures=''.join(f'<figure><figcaption>{n}</figcaption><a href="{n}"><img src="{n}" alt="{n}" loading="lazy"></a></figure>' for n in images)
    (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-07 Galerie</title>'+style+'<h1>TRADE-07 · Empfang bis Bewertung</h1><p><a href="demos.html">Direkte Demos</a> · '+' · '.join(f'<a href="regression-0{i}/index.html">TRADE-0{i}</a>' for i in range(1,7))+'</p><main>'+figures+'</main></html>\n')
    names=['waiting','unchecked','all-ok','problem-form','positions','problem','partner-problem','resolution-pending','confirm-resolution','resolved','one-final','both-ok','completed-v1','completed-v2','rating-empty','rating-1','rating-2','rating-3','rated','one-rated','history','cancelled','q2-waiting','q2-received','q2-ok','q2-ready-received','q2-problem','q2-completed']
    rows=''.join('<tr><th>'+name+'</th>'+''.join(f'<td><a href="{BASE}/trade-v2/requests/fatima/receipt?receipt={name}&role={role}">{role}</a></td>' for role in ('sender','recipient'))+'</tr>' for name in names)
    (OUT/'demos.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-07 Demos</title>'+style+'<h1>TRADE-07 · Direkte Demos</h1><p>Die Links setzen ausschließlich den lokalen Zustand dieses Tabs zurück. Erledigt: nach history zur Tauschbörse zurückgehen.</p><table>'+rows+'</table></html>\n')
    print('PASS:',model['assertions'],'model assertions;',len(images),'screenshots; four complete E2E + problem E2E + Q2 journeys')


if __name__=='__main__':main()
