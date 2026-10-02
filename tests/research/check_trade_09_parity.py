"""Compare numeric Receive faces and list styling with actual canonical renderers."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.research.trade_09_reference import reference_html,webapp
from tests.research.check_trade_01 import PROPS,STYLE
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8095';OUT=Path('tests/research/artifacts/trade-09')
with sync_playwright() as pw:
 b=pw.chromium.launch();checks=[]
 for width in (375,390,430,1280):
  c=b.new_context(viewport={'width':width,'height':900});p=c.new_page();ref=c.new_page()
  ref.route('**/trade-v2/canonical-reference',lambda r:r.fulfill(body=reference_html(),content_type='text/html'))
  ref.goto(BASE+'/trade-v2/canonical-reference');ref.evaluate('document.fonts.ready')
  p.goto(BASE+'/trade-v2/partners/karlheinz/manual');p.wait_for_function('document.body.dataset.ready==="true"');p.evaluate('document.fonts.ready')
  for selector in ('.sticker-list-item','.sticker-list-ceoklaue'):
   if not ref.locator(selector).count():continue
   props=['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing']
   assert p.locator(selector).first.evaluate(STYLE,props)==ref.locator(selector).first.evaluate(STYLE,props)
  p.goto(BASE+'/trade-v2/deals/fatima');p.wait_for_function('document.body.dataset.ready==="true"')
  canonical_width=p.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--trade-card-width")')
  growth=[]
  for quantity in (1,2,5,6,10,15,37):
   markup=webapp.sticker_wall_slot_html('wm06','1',{'1':{'quantity':quantity}},None,'duplicate' if quantity>1 else 'owned','1',can_edit_inventory=False)
   ref.goto(BASE+'/trade-v2/');ref.set_content(f'<link rel="stylesheet" href="{BASE}/static/style.css"><body class="s31-product-page s30-reference-page s30-album-page"><div style="width:{canonical_width};margin:60px">{markup}</div></body>');ref.wait_for_load_state('networkidle')
   p.evaluate('''async n=>{const {renderReceive}=await import('/trade-v2/assets/receive.js');renderReceive([{id:'wm06',title:'WM 2006',items:Array.from({length:n},(_,i)=>({key:'num-'+i,code:'1'}))}]);}''',quantity)
   n=min(quantity,10)
   for selector in ('.slot','.slot .sticker-team','.slot .sammlr-retro-number-visual','.slot .sammlr-retro-digit'):
    actual=p.locator(selector).first.evaluate(STYLE,PROPS);expected=ref.locator(selector).first.evaluate(STYLE,PROPS)
    if selector=='.slot':expected.update(transform=f'matrix(1, 0, 0, 1, {-2*(n-1)}, {-2*(n-1)})',zIndex=str(n))
    assert actual==expected,(width,quantity,selector,actual,expected)
   if quantity>=10:growth.append(p.locator('.pax-album-toggle .sticker-wall-stack-layer,.pax-album-toggle .slot').evaluate_all('(es)=>es.map(e=>[getComputedStyle(e).transform,getComputedStyle(e).zIndex])'))
   checks.append({'width':width,'quantity':quantity,'numeric_face_parity':True})
  assert growth[0]==growth[1]==growth[2];c.close()
 b.close()
(OUT/'canonical-parity.json').write_text(json.dumps(checks,indent=2));print('PASS: canonical list styles and 28 numeric stack comparisons')
