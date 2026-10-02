"""Compare actual production-rendered BRA 3 with Pax, without production DB access."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.test_sticker_wall_product_island import webapp
from playwright.sync_api import sync_playwright
import json

BASE='http://127.0.0.1:8094'
OUT=Path(__file__).parent/'artifacts/pax-cap10'
PROPS=['width','height','padding','borderRadius','borderColor','backgroundColor','transform','zIndex','fontFamily','fontSize','fontWeight','letterSpacing','aspectRatio']
STYLE='(e,props)=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]]))'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (375,390,430):
            page=browser.new_page(viewport={'width':width,'height':600})
            ref=browser.new_page(viewport={'width':width,'height':600})
            page.goto(BASE+'/pax/fatima');page.wait_for_load_state('networkidle')
            page.evaluate("""()=>{document.querySelector('main').innerHTML='<h1>BRA 3 · Pax Receive</h1><div class="pax-board"><section class="s30-album-page pax-receive"><div id="sample" style="width:100px;margin:60px"></div></section></div>';}""")
            growth=[]
            for quantity in (1,2,5,6,10,15,37):
                # Actual production renderer: read-only presentation, synthetic quantity.
                markup=webapp.sticker_wall_slot_html('wm26','BRA 3',{'BRA 3':{'quantity':quantity}},None,'duplicate' if quantity>1 else 'owned','BRA 3',can_edit_inventory=False)
                ref.goto(BASE+'/pax/')
                ref.set_content(f'<link rel="stylesheet" href="{BASE}/static/style.css"><body class="s31-product-page s30-reference-page s30-album-page"><h1>BRA 3 · Stickerwall · Menge {quantity}</h1><div style="width:100px;margin:60px">{markup}</div></body>')
                ref.wait_for_load_state('networkidle')
                await_expr="""async n=>{const {card}=await import('/static/pax/pax.js');document.querySelector('#sample').replaceChildren(card(Array.from({length:n},(_,i)=>({key:'bra-'+i,code:'BRA 3'})),true));} """
                page.evaluate(await_expr,quantity)
                n=min(quantity,10);wall=min(quantity,5)
                assert page.locator('.sticker-wall-stack-layer').count()==n-1
                assert ref.locator('.sticker-wall-stack-layer').count()==wall-1
                # Compare unchanged face geometry against the actual production HTML.
                for selector in ('.slot','.slot .sticker-team','.slot .sammlr-retro-number-visual','.slot .sammlr-retro-digit'):
                    actual=page.locator(selector).evaluate(STYLE,PROPS)
                    expected=ref.locator(selector).evaluate(STYLE,PROPS)
                    if selector=='.slot':
                        expected['transform']=f'matrix(1, 0, 0, 1, {-2*(n-1)}, {-2*(n-1)})'
                        expected['zIndex']=str(n)
                    assert actual==expected,(width,quantity,selector,actual,expected)
                layers=page.locator('.sticker-wall-stack-layer,.slot').evaluate_all('(es,props)=>es.map(e=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]])))',PROPS)
                for i,layer in enumerate(layers):
                    assert layer['transform']==f'matrix(1, 0, 0, 1, {-2*i}, {-2*i})'
                    assert layer['zIndex']==str(i+1)
                for i in range(wall-1):
                    actual=page.locator('.sticker-wall-stack-layer').nth(i).evaluate(STYLE,PROPS)
                    expected=ref.locator('.sticker-wall-stack-layer').nth(i).evaluate(STYLE,PROPS)
                    assert actual==expected,(quantity,actual,expected)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if quantity>=10:growth.append(layers)
                if width==390:
                    page.screenshot(path=str(OUT/f'pax-bra3-{quantity}.png'))
                    if quantity==6:ref.screenshot(path=str(OUT/'wall-bra3-6.png'))
                results.append({'width':width,'quantity':quantity,'pax_layers':n,'wall_layers':wall,'parity':'PASS'})
            assert growth[0]==growth[1]==growth[2], 'Geometry grows past cap'
            page.close();ref.close()
        browser.close()
    (OUT/'checks.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS: actual production BRA 3 renderer vs Pax; 21 cases; geometry identical at 10/15/37.')

if __name__=='__main__':main()
