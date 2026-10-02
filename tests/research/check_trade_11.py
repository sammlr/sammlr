"""Real wall layout vs rendered Trade contexts, motion and visual evidence."""
import sys,json,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.research.trade_11_reference import wall_html
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'tests/research/artifacts/trade-11';BASE='http://127.0.0.1:8095'
PROPS=['width','height','aspectRatio','borderRadius','borderTopWidth','borderTopStyle','padding','fontFamily','fontSize','fontWeight','display','flexDirection','alignItems','justifyContent']
STYLE='(e,props)=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]]))'
def main():
 OUT.mkdir(parents=True,exist_ok=True);results=[];errors=[];writes=[];images=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in (375,390,430,1280):
   ctx=b.new_context(viewport={'width':width,'height':900},has_touch=True);p=ctx.new_page();ref=ctx.new_page()
   p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
   p.on('response',lambda r:errors.append(str(r.status)+r.url) if r.status>=400 else None)
   ref.route('**/trade-v2/wall-reference',lambda r:r.fulfill(body=wall_html(),content_type='text/html'))
   ref.goto(BASE+'/trade-v2/wall-reference');ref.evaluate('document.fonts.ready')
   wall=ref.locator('.slot[data-code="BRA1"]');wall.scroll_into_view_if_needed();expected=wall.evaluate(STYLE,PROPS)
   assert wall.locator('..').locator('.sticker-wall-stack-layer').count()==4
   def settled():
    p.wait_for_function('document.body.dataset.ready==="true"');p.evaluate('document.fonts.ready');p.evaluate('Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{})))');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   def go(path):p.goto(BASE+path);settled()
   def shot(name):
    file=f'{name}-{width}.png';p.screenshot(path=str(OUT/file),full_page=True);images.append(file)
   def inner_equal(locator):
    for selector in ('.sticker-team','.sammlr-retro-number-visual','.sammlr-retro-digit'):
     props=['width','height','fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','alignItems','justifyContent']
     assert locator.locator(selector).first.evaluate(STYLE,props)==wall.locator(selector).first.evaluate(STYLE,props),(width,selector)
   def equal(locator):
    actual=locator.evaluate(STYLE,PROPS)
    for prop in PROPS:
     if prop in ['width','height']:assert abs(float(actual[prop][:-2])-float(expected[prop][:-2]))<.04,(width,prop,actual,expected)
     else:assert actual[prop]==expected[prop],(width,prop,actual[prop],expected[prop])
    assert locator.evaluate('''e=>{for(let n=e;n&&n!==document.body;n=n.parentElement){const m=new DOMMatrix(getComputedStyle(n).transform);if(Math.abs(Math.hypot(m.a,m.b)-1)>.0001||Math.abs(Math.hypot(m.c,m.d)-1)>.0001)return false;}return true;}''')
    return actual
   def separate(rects):
    for i,a in enumerate(rects):
     for d in rects[i+1:]:assert a['right']<=d['x']+.05 or d['right']<=a['x']+.05 or a['bottom']<=d['y']+.05 or d['bottom']<=a['y']+.05,(width,a,d)
   crops=[('Wall',wall.screenshot())]
   go('/trade-v2/');assert '3 vielversprechende Tauschvorschläge für dich.' in p.locator('main').inner_text();top=equal(p.locator('.top-stack .slot').first);inner_equal(p.locator('.top-stack .slot').first)
   rects=p.locator('.top-stack').evaluate_all('''es=>es.map(e=>{const rs=[...e.querySelectorAll('.slot,.sticker-wall-stack-layer')].map(n=>n.getBoundingClientRect());return {x:Math.min(...rs.map(r=>r.x)),y:Math.min(...rs.map(r=>r.y)),right:Math.max(...rs.map(r=>r.right)),bottom:Math.max(...rs.map(r=>r.bottom))};})''');separate(rects)
   assert min(r['x'] for r in rects)>=0 and max(r['right'] for r in rects)<=width
   crops.append(('Top 3',p.locator('.top-stack .slot').first.screenshot()));shot('top')
   go('/trade-v2/partners/fatima/smartdeal');before=p.evaluate('sessionStorage.getItem("sammlr-trade-02")');stack=equal(p.locator('.pax-album-toggle .slot').first);inner_equal(p.locator('.pax-album-toggle .slot').first);crops.append(('Albumstapel',p.locator('.pax-album-toggle .slot').first.screenshot()));shot('closed')
   toggle=p.locator('.pax-album-toggle').first;toggle.focus();p.keyboard.press('Enter')
   p.evaluate('document.getAnimations().forEach(a=>{a.pause();a.currentTime=110})');assert p.locator('.trade-flight-layer .slot').count()>0
   for tile in p.locator('.trade-flight-layer .slot').all():equal(tile)
   inner_equal(p.locator('.trade-flight-layer .slot').first)
   assert p.evaluate('document.querySelector(".trade-flight-layer").getAnimations({subtree:true}).every(a=>a.effect.getTiming().duration===440)');shot('opening-motion')
   p.evaluate('document.getAnimations().forEach(a=>a.play())');settled();fan=equal(p.locator('.pax-fan-grid .slot').first);inner_equal(p.locator('.pax-fan-grid .slot').first);crops.append(('Ausgelegt',p.locator('.pax-fan-grid .slot').first.screenshot()));shot('open')
   p.locator('.pax-album-fan .pj-simulation').first.tap();p.evaluate('document.getAnimations().forEach(a=>{a.pause();a.currentTime=220})');assert p.locator('.trade-flight-layer .slot').count()>0
   for tile in p.locator('.trade-flight-layer .slot').all():equal(tile)
   inner_equal(p.locator('.trade-flight-layer .slot').first)
   shot('closing-motion');p.evaluate('document.getAnimations().forEach(a=>a.play())');settled();assert p.locator('.pax-receive-album.is-expanded').count()==0
   p.locator('.receive-all').tap();settled();assert p.locator('.pax-receive-album.is-expanded').count()==6
   tiles=p.locator('.pax-fan-grid .slot');assert tiles.count()==23
   for tile in tiles.all():equal(tile)
   separate(tiles.evaluate_all('(es)=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}})'));shot('all')
   poses=p.locator('.pax-fan-grid>.sticker-slot-frame').evaluate_all('(es)=>es.map(e=>e.style.cssText)')
   assert p.locator('.receive-all').bounding_box()['height']>=44
   p.emulate_media(reduced_motion='reduce');p.locator('.pax-album-fan .pj-simulation').first.tap();p.locator('.pax-album-toggle').first.tap();assert p.evaluate('document.getAnimations().length')==0;assert p.locator('.trade-flight-layer').count()==0
   assert p.evaluate('sessionStorage.getItem("sammlr-trade-02")')==before
   p.reload();settled();p.locator('.receive-all').tap();settled();assert p.locator('.pax-fan-grid>.sticker-slot-frame').evaluate_all('(es)=>es.map(e=>e.style.cssText)')==poses
   comparison=ctx.new_page();comparison.set_viewport_size({'width':800,'height':350});html='<meta charset="utf-8"><style>body{font:14px system-ui;background:#f6f3ef;padding:20px}main{display:flex;gap:40px}figure{margin:0}img{display:block;margin-top:20px}</style><h1>Wall / Trade · '+str(width)+' px Viewport</h1><p>'+expected['width']+' × '+expected['height']+' · unskalierte Originalaufnahmen</p><main>'
   html+=''.join('<figure><figcaption>'+name+'</figcaption><img src="data:image/png;base64,'+base64.b64encode(png).decode()+'"></figure>' for name,png in crops)+'</main>'
   (OUT/f'comparison-{width}.html').write_text(html);comparison.set_content(html);comparison.screenshot(path=str(OUT/f'comparison-{width}.png'));images.append(f'comparison-{width}.png')
   results.append({'viewport':width,'wall':expected,'top':top,'stack':stack,'fan':fan,'same_dimensions_no_scale':True,'forward_reverse_motion_ms':440,'deterministic_pose':True,'reduced_motion':True,'no_collisions_overflow':True,'no_store_mutation':True});ctx.close()
  b.close()
 assert not errors,errors
 assert not writes,writes
 (OUT/'checks.json').write_text(json.dumps({'results':results,'errors':errors,'network_mutations':writes},indent=2)+'\n')
 (OUT/'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRADE-11 Galerie</title><style>body{font:16px system-ui;background:#f6f3ef;margin:24px}main{display:flex;flex-wrap:wrap;gap:24px;align-items:start}figure{margin:0;width:390px;max-width:100%}img{width:100%}</style><h1>TRADE-11 · Kanonische Stickerphysik</h1><p>'+ ' · '.join(f'<a href="regression-{n:02}/index.html">TRADE-{n:02}</a>' for n in range(1,11))+'</p><main>'+''.join(f'<figure><figcaption>{file}</figcaption><a href="{file}"><img loading="lazy" src="{file}" alt="{file}"></a></figure>' for file in images)+'</main></html>\n')
 print('PASS',[(r['viewport'],r['wall']['width'],r['wall']['height']) for r in results])
if __name__=='__main__':main()
