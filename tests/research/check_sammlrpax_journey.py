"""Click through the isolated GET preview; verify no mutation requests are sent.
Run against the dedicated preview server, never a real trade mutation route.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL=os.environ.get('SAMMLRPAX_PREVIEW_URL','http://127.0.0.1:8092/preview/sammlrpax-journey-v1')


def main():
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (375,390,430):
            page=browser.new_page(viewport={'width':width,'height':844})
            mutations=[];errors=[];failures=[]
            page.on('request',lambda r:mutations.append(r.url) if r.method not in ('GET','HEAD') else None)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:failures.append((r.url,r.status)) if r.status>=400 else None)
            response=page.goto(URL);assert response.status==200
            page.wait_for_load_state('networkidle')
            def no_overflow():
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
            def snapshot(name):
                no_overflow()
                if width==390:page.screenshot(path=f'/private/tmp/pax-journey-{name}-390.png')
            snapshot('A-closed')
            page.locator('#pj-open').click()
            page.wait_for_function('document.querySelector(".pj").dataset.view==="board"')
            assert page.locator('#pj-request').inner_text().startswith('Pax anfragen')
            receive=page.locator('[data-fan="receive"] .pj-face').evaluate_all('es=>es.map(e=>e.dataset.code)')
            give=page.locator('[data-fan="give"] .pj-face').evaluate_all('es=>es.map(e=>e.dataset.code)')
            assert len(receive)==len(give)==5 and receive!=give
            snapshot('B-board')
            page.locator('[data-fan="receive"]').click()
            assert page.locator('#pj-fan .pj-face').count()==23
            assert page.locator('.pj-fan-group').count()==6
            snapshot('C-fanned')
            page.locator('#pj-close-fan').click();assert page.locator('#pj-fan').is_hidden()
            page.locator('[data-fan="give"]').click();assert page.locator('#pj-fan .pj-face').count()==23
            page.locator('[data-fan="give"]').click();assert page.locator('#pj-fan').is_hidden()
            page.locator('#pj-request').click();assert page.locator('[data-screen="sent"]').is_visible()
            page.locator('#pj-partner').click();assert page.locator('#pj-pack-partner').inner_text()=='mit Valentin'
            snapshot('D-partner-pack')
            page.locator('#pj-open').click();page.wait_for_function('document.querySelector(".pj").dataset.view==="partner-open"')
            assert page.locator('#pj-request').inner_text().startswith('Pax annehmen')
            assert page.locator('[data-fan="receive"] .pj-face').evaluate_all('es=>es.map(e=>e.dataset.code)')==give
            assert page.locator('[data-fan="give"] .pj-face').evaluate_all('es=>es.map(e=>e.dataset.code)')==receive
            snapshot('D-partner-board')
            page.locator('#pj-request').click();assert page.locator('[data-screen="shipping"]').is_visible()
            assert page.locator('#pj-send').is_disabled()
            snapshot('E-shipping')
            page.locator('#pj-check-toggle').click()
            boxes=page.locator('#pj-checklist input')
            assert boxes.count()==23
            for box in boxes.all():box.check()
            assert page.locator('#pj-check-count').inner_text()=='23 / 23'
            assert page.locator('#pj-send').is_enabled()
            boxes.first.uncheck();assert page.locator('#pj-send').is_disabled()
            boxes.first.check();assert page.locator('#pj-send').is_enabled()
            no_overflow()
            page.locator('#pj-check-toggle').click()
            page.locator('#pj-send').click();assert page.locator('[data-screen="done"]').is_visible()
            for state in ('closed','board','sent','partner','shipping'):
                page.locator(f'.pj-tools [data-view="{state}"]').click()
                assert page.locator('.pj').get_attribute('data-view')==state
                no_overflow()
            page.reload();assert page.locator('#pj-check-count').inner_text()=='0 / 23'
            assert page.locator('.pj').get_attribute('data-view')=='closed'
            assert not mutations and not errors and not failures,(mutations,errors,failures)
            results.append({'width':width,'full_journey':'PASS','mirrored_package':'PASS','client_only_checklist':'PASS','mutation_requests':len(mutations),'overflow':False})
            page.close()
        browser.close()
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
