from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8094'
props=['width','height','padding','borderRadius','borderColor','backgroundColor','boxShadow','transform','fontFamily','fontSize','fontWeight','letterSpacing','aspectRatio']
expr='(e,props)=>Object.fromEntries(props.map(k=>[k,getComputedStyle(e)[k]]))'
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in (375,390,430):
        page=browser.new_page(viewport={'width':width,'height':844})
        page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
        ref=browser.new_page(viewport={'width':width,'height':844})
        ref.goto(BASE+'/pax/')
        page.goto(BASE+'/pax/fatima');page.wait_for_function('document.body.dataset.screen==="board"')
        frame=page.locator('.pax-album-toggle .sticker-slot-frame').first.evaluate('(e)=>e.outerHTML')
        ref.set_content(f'<link rel="stylesheet" href="{BASE}/static/style.css"><body class="s31-product-page s30-reference-page s30-album-page"><div style="width:100px">{frame}</div></body>')
        ref.wait_for_load_state('networkidle')
        for selector in ('.slot','.slot .sticker-team','.slot .sammlr-retro-number-visual','.slot .sammlr-retro-digit','.sticker-wall-stack-layer'):
            actual=page.locator('.pax-album-toggle '+selector).first.evaluate(expr,props)
            expected=ref.locator(selector).first.evaluate(expr,props)
            assert actual==expected,(width,selector,actual,expected)
        page.close();ref.close()
    browser.close()
print('PASS: stable card front computed styles/geometry match original at 375/390/430.')
