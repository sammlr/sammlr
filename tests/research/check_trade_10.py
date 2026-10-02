"""Read-only overview projection, real lifecycle links and Q2 browser regression."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'tests/research/artifacts/trade-10';BASE='http://127.0.0.1:8095'
def main():
 OUT.mkdir(parents=True,exist_ok=True);images=[];results=[];errors=[];writes=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in (375,390,430,1280):
   ctx=b.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce');p=ctx.new_page()
   p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
   p.on('response',lambda r:errors.append(str(r.status)+' '+r.url) if r.status>=400 else None)
   def ready():
    p.wait_for_function('document.body.dataset.ready==="true"');p.evaluate('document.fonts.ready');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   def go(path):p.goto(BASE+path);ready()
   def shot(name):
    file=f'{name}-{width}.png';p.screenshot(path=str(OUT/file),full_page=True);images.append(file)
   def record():return p.evaluate('JSON.parse(sessionStorage.getItem("sammlr-trade-02")).requests["demo-fatima"]')
   go('/trade-v2/');assert p.locator('.top-offer').count()==3;assert p.locator('#trade-active').count()==0
   p.get_by_role('link',name='Laufende Tausche',exact=True).tap();ready();assert p.locator('h1').inner_text()=='Laufende Tausche';assert 'Keine laufenden Tausche.' in p.locator('#trade-active').inner_text();shot('01-empty')
   model=(ROOT/'tests/research/trade_10_model.js').read_text().replace('export async function check','async function check')
   deals=p.locator('#trade-data').evaluate('(e)=>JSON.parse(e.textContent).deals');checks=p.evaluate('(async deals=>{'+model+';return await check(deals);})',deals)
   go('/trade-v2/active?overview=mixed');assert p.locator('.overview-row').count()==6
   assert p.locator('.overview-group').evaluate_all('(es)=>es.map(e=>e.dataset.group)')==['incoming','action','waiting']
   assert p.locator('#trade-active .sticker-slot-frame,#trade-active .trade-postit,#trade-history').count()==0
   p.locator('.overview-primary').first.focus();p.wait_for_timeout(1100);assert p.locator('.overview-primary').first.evaluate('(e)=>document.activeElement===e')
   before=p.evaluate('sessionStorage.getItem("sammlr-trade-02")');p.reload();ready();assert p.evaluate('sessionStorage.getItem("sammlr-trade-02")')==before;shot('02-mixed')
   links=p.locator('.overview-primary').evaluate_all('(es)=>es.map(e=>e.getAttribute("href"))')
   for href in links:
    go(href);assert p.locator('body').get_attribute('data-role') in ('sender','recipient');assert p.locator('.demo-tools').count()==1
   for scenario,group,ending in [('incoming','incoming','?role=recipient'),('action','action','/next?role=sender'),('waiting','waiting','?role=sender'),('amendment','action','/amendment?role=recipient'),('amendment-wait','waiting','/amendment?role=sender'),('shipping','action','/shipping?role=sender&view=prepare'),('receipt','action','/receipt?role=sender'),('problem','action','/receipt?role=recipient'),('problem-wait','waiting','/receipt?role=sender')]:
    go('/trade-v2/active?overview='+scenario);assert p.locator('.overview-group').get_attribute('data-group')==group
    a=p.locator('.overview-primary');assert a.get_attribute('href').endswith(ending);shot('03-'+scenario)
    a.focus();assert a.evaluate('(e)=>getComputedStyle(e).outlineStyle')!='none';p.keyboard.press('Enter');ready();assert p.url.endswith(ending)
   go('/trade-v2/active?overview=incoming');p.locator('.overview-primary').click();ready();p.locator('#accept-request').tap();go('/trade-v2/active');assert p.locator('.overview-group').get_attribute('data-group')=='action'
   go('/trade-v2/active?overview=incoming');p.locator('.overview-primary').tap();ready();p.locator('#decline-request').tap();go('/trade-v2/active');assert p.locator('.overview-row').count()==0
   go('/trade-v2/requests/fatima?scenario=expired');go('/trade-v2/active');assert p.locator('.overview-row').count()==0
   go('/trade-v2/requests/fatima/receipt?receipt=completed-v1');go('/trade-v2/active');assert p.locator('.overview-row,#trade-history').count()==0
   go('/trade-v2/active?overview=q2');shot('04-q2-entry');before=record();p.locator('.overview-receipt').tap();ready();p.locator('#receipt-receive').tap();p.locator('#receipt-ok').tap()
   after=record();assert not after.get('recipientShipped');assert after['shipping']==before['shipping'];assert after['ownShipped']==before['ownShipped'];assert after['receipts']['sender']['state']=='RECEIVED_OK';shot('05-q2-received')
   go('/trade-v2/active');assert 'Versand vorbereiten' in p.locator('#trade-active').inner_text()
   go('/trade-v2/active?overview=q2');p.locator('.overview-receipt').tap();ready();p.locator('#receipt-receive').tap();p.locator('#receipt-problem').tap();p.get_by_role('checkbox',name='Falscher Sticker',exact=True).check();p.locator('[name=position]').first.check();p.locator('#problem-submit').tap();assert record()['shipping']==before['shipping'];shot('06-q2-problem')
   go('/trade-v2/active?overview=mixed');assert p.evaluate('document.getAnimations().length')==0
   results.append({'width':width,'model':checks,'groups_links_terminal_q2':'PASS','touch_mouse_keyboard_reduced_motion':'PASS','overflow':False});ctx.close()
  b.close()
 assert not errors,errors
 assert not writes,writes
 (OUT/'checks.json').write_text(json.dumps({'results':results,'errors':errors,'network_mutations':writes},indent=2)+'\n')
 (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-10 Prüfgalerie</title><style>body{font:16px system-ui;background:#f7f5f0;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{width:390px;max-width:100%;margin:0}img{width:100%}</style><h1>TRADE-10 · Laufende Tausche</h1><p>'+ ' · '.join(f'<a href="regression-{n:02}/index.html">TRADE-{n:02}</a>' for n in range(1,10))+'</p><main>'+''.join(f'<figure><figcaption>{f}</figcaption><a href="{f}"><img loading="lazy" src="{f}" alt="{f}"></a></figure>' for f in images)+'</main></html>\n')
 print(json.dumps(results))
if __name__=='__main__':main()
