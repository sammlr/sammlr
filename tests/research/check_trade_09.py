"""Manual selection: bilateral rules, canonical list, limits and shared request flow."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tests/research/artifacts/trade-09'
BASE='http://127.0.0.1:8095'
def main():
 OUT.mkdir(parents=True,exist_ok=True);results=[];errors=[];writes=[];images=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  for width in (375,390,430,1280):
   ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce');p=ctx.new_page()
   p.on('pageerror',lambda e:errors.append(str(e)))
   p.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
   def ready():
    p.wait_for_function('document.body.dataset.ready==="true"');p.evaluate('document.fonts.ready');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   def go(path):p.goto(BASE+path);ready()
   def select(album,side,n):
    for i in range(n):p.locator(f'.manual-album[data-album="{album}"] button[data-side="{side}"]').nth(i).tap()
   def shot(name):
    ready();file=f'{name}-{width}.png';p.screenshot(path=str(OUT/file),full_page=True);images.append(file)
   go('/trade-v2/partners/karlheinz/manual?manual=same')
   contexts=p.locator('#trade-data').evaluate('(e)=>JSON.parse(e.textContent).contexts')
   model=(ROOT/'tests/research/trade_09_model.js').read_text().replace('export async function check','async function check')
   model_result=p.evaluate('(async contexts=>{'+model+';return await check(contexts);})',contexts)
   assert p.locator('.manual-album').count()==4
   before=p.locator('.sticker-list-item').count();select('wm06','receive',3)
   fourth=p.locator('.manual-album[data-album=wm06] button[data-side=receive]').nth(3)
   assert fourth.get_attribute('aria-disabled')=='true';fourth.focus();p.keyboard.press('Enter')
   assert '3 Sticker möglich' in p.locator('#manual-status').inner_text()
   assert p.locator('.sticker-list-item').count()==before
   assert p.locator('.manual-album[data-album=wm06] button[data-side=receive][aria-pressed=true]').count()==3
   select('wm06','give',3);assert p.locator('#manual-review').is_enabled();shot('02-album-limit')
   first=p.locator('.manual-album[data-album=wm06] button[data-side=receive]').first;first.tap();fourth.tap()
   assert p.locator('#manual-review').is_enabled();select('wm06','give',1);assert p.locator('#manual-review').is_disabled()
   fourth.tap();select('wm06','give',1);assert p.locator('#manual-review').is_enabled()
   p.reload();ready();assert p.locator('button[data-side=receive][aria-pressed=true]').count()==2
   assert p.locator('button[data-side=give][aria-pressed=true]').count()==3
   assert p.locator('button[data-side=give][aria-pressed=true] .marker-draw').evaluate_all('(es)=>es.every(e=>getComputedStyle(e).strokeDashoffset==="0px")');shot('03-two-for-three')
   go('/trade-v2/partners/karlheinz/manual?manual=one-sided');select('wm06','receive',1);select('buli07','give',1);assert p.locator('#manual-review').is_disabled()
   go('/trade-v2/partners/karlheinz/manual?manual=open');select('wm06','receive',3);select('em04','receive',2);select('buli07','give',5);assert p.locator('#manual-review').is_enabled();shot('04-open-selection')
   p.locator('#manual-review').tap();ready();assert '5 ↔ 5' in p.locator('.deal-summary').inner_text();shot('05-open-review')
   p.evaluate('sessionStorage.removeItem("sammlr-trade-09-draft/karlheinz")');p.locator('#request-preview').tap();assert p.locator('#request-preview').is_disabled();assert p.evaluate('!JSON.parse(sessionStorage.getItem("sammlr-trade-02")||"{\\"requests\\":{}}").requests["manual-karlheinz"]')
   go('/trade-v2/partners/karlheinz/manual/review');assert p.locator('#request-preview').is_disabled()
   go('/trade-v2/partners/karlheinz/manual?manual=same');select('wm06','receive',2);select('wm06','give',3);p.locator('#manual-review').tap();ready()
   assert '2 ↔ 3' in p.locator('.deal-summary').inner_text();p.locator('#request-preview').tap();p.wait_for_url('**/requests/manual-karlheinz');ready();shot('06-manual-request')
   record=p.evaluate('JSON.parse(sessionStorage.getItem("sammlr-trade-02")).requests["manual-karlheinz"]')
   assert record['snapshot']['origin']=='MANUAL' and record['snapshot']['receive_count']==2 and record['snapshot']['give_count']==3
   go('/trade-v2/partners/karlheinz/manual/review');p.locator('#request-preview').tap();ready()
   assert p.evaluate('JSON.parse(sessionStorage.getItem("sammlr-trade-02")).requests["manual-karlheinz"]')==record
   go('/trade-v2/requests/manual-karlheinz?role=recipient');p.locator('#accept-request').tap();ready()
   for role in ('sender','recipient'):
    go('/trade-v2/requests/manual-karlheinz/next?role='+role);p.locator('#pack-finish').tap();p.locator('#ship-prepare').tap();p.locator('#ship-method').select_option('brief');p.locator('#ship-confirm').tap();ready()
   for role in ('sender','recipient'):
    go('/trade-v2/requests/manual-karlheinz/receipt?role='+role);p.locator('#receipt-receive').tap();p.locator('#receipt-ok').tap();ready()
   final=p.evaluate('JSON.parse(sessionStorage.getItem("sammlr-trade-02")).requests["manual-karlheinz"]')
   assert final['completedAt'] and final['snapshot']==record['snapshot'];shot('07-manual-completed')
   go('/trade-v2/deals/fatima?demo=3');go('/trade-v2/partners/karlheinz/manual/review');assert p.locator('#request-preview').is_disabled()
   p.locator('#request-preview').evaluate('(e)=>e.dispatchEvent(new MouseEvent("click"))')
   assert p.evaluate('!JSON.parse(sessionStorage.getItem("sammlr-trade-02")).requests["manual-karlheinz"]')
   results.append({'width':width,'model':model_result,'limit':True,'no_disappearance':True,'two_for_three':True,'bilateral_open':True,'one_sided_rejected':True,'stale_and_empty_rejected':True,'request_reused':True,'complete_manual_e2e':True,'capacity_three_blocked':True,'overflow':False});ctx.close()
  browser.close()
 assert not errors,errors
 assert not writes,writes
 (OUT/'checks.json').write_text(json.dumps({'results':results,'browser_errors':errors,'network_mutations':writes},indent=2))
 (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>TRADE-09 Prüfgalerie</title><style>body{font-family:system-ui;max-width:1400px;margin:auto}img{max-width:100%;border:1px solid #ccc}figure{display:inline-block;vertical-align:top;width:390px}</style><h1>TRADE-09</h1>'+''.join(f'<p><a href="regression-0{n}/index.html">TRADE-0{n} Regression</a></p>' for n in range(1,9))+''.join(f'<figure><figcaption>{f}</figcaption><a href="{f}"><img src="{f}"></a></figure>' for f in images))
 print(json.dumps(results))
if __name__=='__main__':main()
