"""Browser acceptance of the isolated V2 preview. No production app imports."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8093/preview/sammlrpax-journey-v2'
OUT=Path(__file__).parent/'artifacts/sammlrpax-journey-v2'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (375,390,430):
            page=browser.new_page(viewport={'width':width,'height':844},device_scale_factor=1)
            mutations=[];errors=[];failures=[]
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') else None)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:failures.append((r.url,r.status)) if r.status>=400 else None)
            assert page.goto(URL).status==200
            page.wait_for_load_state('networkidle')
            def snapshot(name):
                page.evaluate('window.scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,name)
                if width==390:page.screenshot(path=str(OUT/f'{name}-390.png'),full_page=True)
            snapshot('01-closed')
            page.locator('#pj-open').click()
            page.wait_for_function('document.body.dataset.view==="board"')
            assert page.locator('.trade-postit').count()==6
            assert page.locator('.trade-postit').first.evaluate('(e)=>getComputedStyle(e).width')=='224px'
            assert 'CEOKlaue Final Alt 1' in page.locator('.v2-todo').first.evaluate('(e)=>getComputedStyle(e).fontFamily')
            assert page.locator('#v2-stack .slot').evaluate('(e)=>getComputedStyle(e).transform')=='matrix(1, 0, 0, 1, -8, -8)'
            assert page.locator('#v2-request').is_disabled()
            assert page.locator('input[type=checkbox]').count()==0
            assert page.locator('#v2-stack .sticker-wall-stack-layer').count()==4
            receive=page.locator('#v2-cards .sticker-slot-frame').evaluate_all('es=>es.map(e=>e.dataset.code)')
            give=page.locator('.v2-todo').evaluate_all('es=>es.map(e=>e.dataset.code)')
            assert len(receive)==len(give)==23 and receive!=give
            snapshot('02-board')
            page.locator('#v2-stack-toggle').click()
            assert page.locator('#v2-fan').is_visible()
            snapshot('03-receive-fanned')
            page.locator('#v2-collapse').click()
            assert page.locator('#v2-fan').is_hidden()
            todos=page.locator('.v2-todo')
            todos.first.click();assert todos.first.get_attribute('aria-pressed')=='true'
            todos.first.click();assert todos.first.get_attribute('aria-pressed')=='false'
            for b in todos.all()[:5]:b.click()
            page.wait_for_timeout(400)
            snapshot('04-partial-todos')
            assert page.locator('#v2-progress').inner_text()=='5 / 23 geprüft'
            for b in todos.all()[5:]:b.click()
            page.wait_for_timeout(400)
            assert page.locator('#v2-request').is_enabled()
            snapshot('05-all-checked')
            todos.first.click();assert page.locator('#v2-request').is_disabled()
            todos.first.click();page.locator('#v2-request').click()
            assert page.locator('[data-screen=sent]').is_visible()
            page.locator('#v2-partner').click()
            assert page.locator('#v2-cards .sticker-slot-frame').evaluate_all('es=>es.map(e=>e.dataset.code)')==give
            assert page.locator('.v2-todo').evaluate_all('es=>es.map(e=>e.dataset.code)')==receive
            assert page.locator('#v2-progress').inner_text()=='0 / 23 geprüft'
            assert page.locator('#v2-request').is_disabled()
            snapshot('06-partner-mirrored')
            page.locator('#v2-stack-toggle').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#v2-collapse').click()
            for b in page.locator('.v2-todo').all():b.click()
            assert page.locator('#v2-request').inner_text()=='Pax annehmen →'
            page.locator('#v2-request').click()
            assert page.locator('[data-screen=shipping]').is_visible()
            assert page.locator('.v2-envelope').inner_text().find('Musterstraße 89')>=0
            snapshot('07-shipping-envelope')
            page.locator('#v2-send').click()
            assert page.locator('[data-screen=done]').is_visible()
            page.locator('#v2-again').click();assert page.locator('[data-screen=closed]').is_visible()
            page.reload();assert page.locator('#v2-progress').inner_text()=='0 / 23 geprüft'
            assert not mutations and not errors and not failures,(mutations,errors,failures)
            results.append({'width':width,'journey':'PASS','mirroring':'PASS','overflow':False,'mutation_requests':0,'console_errors':0})
            page.close()
        browser.close()
    (OUT/'checks.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
