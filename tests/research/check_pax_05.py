"""PAX-05 browser-only lifecycle and protected mobile presentation gate."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from App.pax.fixtures import CANDIDATES

BASE='http://127.0.0.1:8094'
OUT=Path(__file__).parent/'artifacts/pax-05'

MODEL_TEST=r'''async candidates=>{
 const m=await import('/static/pax/lifecycle.js');
 const assert=(v,msg)=>{if(!v)throw Error(msg);};
 let cases=0;
 for(const candidate of candidates){
  const d=m.createDeal(candidate), original=JSON.stringify(d);
  const a=m.perspective(d,'sender'),b=m.perspective(d,'recipient');
  assert(a.receive===b.give && a.give===b.receive,'one canonical mirrored source');
  assert(Object.isFrozen(d)&&Object.isFrozen(d.give[0].items),'frozen snapshot');
  for(const [role,expected] of [['sender',d.give_count],['recipient',d.receive_count]]){
   assert(m.pieces(d,role).length===expected,'counts');
   assert(new Set(m.pieces(d,role).map(p=>p.key)).size===expected,'unique physical instances');
  }
  let s=m.initialState();const t=100000;
  assert(m.transition(s,'request','recipient',t).status==='discovery','recipient cannot send');
  s=m.transition(s,'request','sender',t);
  assert(s.bindingCreatedAt===t,'binding instant');
  assert(m.transition(s,'request','sender',t+5000).bindingCreatedAt===t,'retry does not rejuvenate');
  assert(m.transition(s,'accept','sender',t).status==='pending','sender cannot accept');
  assert(m.transition(s,'withdraw','recipient',t).status==='pending','recipient cannot withdraw');
  assert(m.transition(s,'decline','sender',t).status==='pending','sender cannot decline');
  assert(m.togglePiece(d,s,'sender',m.pieces(d,'sender')[0].key)===s,'no preaccept packing');
  assert(m.transition(s,'accept','recipient',t+m.DAY-1).status==='packing','accept just before boundary');
  assert(m.transition(s,'accept','recipient',t+m.DAY).status==='expired','absolute boundary');
  assert(m.transition(s,'accept','recipient',t+m.DAY+1).status==='expired','after boundary');
  for(const [action,role,end] of [['withdraw','sender','withdrawn'],['decline','recipient','declined']]){
   const terminal=m.transition(s,action,role,t+1);
   assert(terminal.status===end,'release');
   assert(m.transition(terminal,'accept','recipient',t+2).status===end,'terminal cannot accept');
  }
  s=m.transition(s,'accept','recipient',t+1);
  assert(m.refresh(s,t+10*m.DAY).status==='packing','accepted never pending-expires');
  assert(m.transition(s,'withdraw','sender',t+2)===s,'no postaccept withdraw');
  assert(m.togglePiece(d,s,'sender','foreign')===s,'unknown key rejected');
  const key=m.pieces(d,'sender')[0].key;
  s=m.togglePiece(d,s,'sender',key);
  assert(s.packed.recipient.length===0,'separate role marks');
  s=m.togglePiece(d,s,'sender',key);assert(s.packed.sender.length===0,'undo');
  for(const item of m.pieces(d,'sender'))s=m.togglePiece(d,s,'sender',item.key);
  assert(m.canContinue(d,s,'sender')&&!m.canContinue(d,s,'recipient'),'own complete only');
  assert(m.validState(d,s),'state restore validation');
  assert(!m.validState(d,{...s,packed:{...s.packed,sender:['foreign']}}),'invalid saved keys');
  assert(JSON.stringify(d)===original,'snapshot unchanged');cases++;
 }
 return {candidates:cases,mirror:true,expiry_boundary:true,role_guards:true,packing:true};
}'''

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 results=[]
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in (375,390,430):
   context=browser.new_context(viewport={'width':width,'height':844},has_touch=True,reduced_motion='reduce')
   page=context.new_page();errors=[];writes=[];failures=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
   page.on('response',lambda r:failures.append(r.url) if r.status>=400 else None)
   def ready():page.wait_for_function('document.body.dataset.screen!==undefined')
   def geometry():
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    for selector in ('.trade-postit','.pax-album-toggle .slot','.pax-fan-grid .slot'):
     assert page.locator(selector).evaluate_all('es=>es.filter(e=>e.checkVisibility()).every(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})'),selector
    assert page.locator('.sticker-list-review-codes').evaluate_all('es=>es.filter(e=>e.checkVisibility()).every(e=>e.scrollWidth<=e.clientWidth&&e.scrollHeight<=e.clientHeight)')
   def shot(name):
    geometry()
    if width==390:
     page.locator('.pax-dev').evaluate_all('es=>es.forEach(e=>e.open=false)')
     page.evaluate('scrollTo(0,0)');page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
   def role(name):
    page.locator('.pax-dev').evaluate('(e)=>e.open=true')
    page.locator(f'[data-role={name}]').click()
   def scenario(name):
    page.goto(BASE+'/pax/fatima?demo='+name);ready();page.wait_for_load_state('networkidle')
   def keys(selector):return page.locator(selector).evaluate_all('es=>es.map(e=>e.dataset.itemKey)')
   page.goto(BASE+'/pax/');page.wait_for_load_state('networkidle')
   model=page.evaluate(MODEL_TEST,list(CANDIDATES))
   shot('01-discovery')
   page.locator('[data-candidate=fatima]').tap();ready();page.wait_for_load_state('networkidle')
   assert page.locator('.pax-pack-item').count()==0
   incoming=keys('.pax-fan-grid .sticker-slot-frame');outgoing=keys('.pending-review-row')
   shot('02-opened')
   page.locator('#pax-request').click();assert page.locator('section[data-screen=waiting]').is_visible()
   assert '24 Std.' in page.locator('#pax-time').inner_text();shot('03-waiting')
   binding=page.evaluate("JSON.parse(sessionStorage.getItem('sammlr-pax-06:fatima')).state.bindingCreatedAt")
   page.reload();ready();assert page.locator('section[data-screen=waiting]').is_visible()
   assert page.evaluate("JSON.parse(sessionStorage.getItem('sammlr-pax-06:fatima')).state.bindingCreatedAt")==binding
   role('recipient')
   assert keys('.pax-fan-grid .sticker-slot-frame')==outgoing
   assert keys('.pending-review-row')==incoming
   assert page.locator('.pax-pack-item').count()==0;shot('04-recipient')
   page.locator('#pax-request').click();assert page.locator('.pax-pack-item').count()==23
   assert page.locator('#pax-progress').inner_text()=='0 / 23 eingepackt'
   assert page.locator('#pax-request').is_disabled()
   role('sender');shot('05-packing-zero')
   assert keys('.pax-pack-item')==outgoing
   before=page.locator('.trade-postit').evaluate_all('es=>es.map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y+scrollY,r.width,r.height]})')
   button=page.locator('.pax-pack-item').first
   button.tap();assert button.get_attribute('aria-pressed')=='true'
   button.focus();page.keyboard.press('Space');assert button.get_attribute('aria-pressed')=='false'
   page.keyboard.press('Enter');assert button.get_attribute('aria-pressed')=='true'
   assert button.evaluate('e=>getComputedStyle(e).outlineStyle')=='solid'
   after=page.locator('.trade-postit').evaluate_all('es=>es.map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y+scrollY,r.width,r.height]})')
   assert before==after,'marking changes note geometry'
   role('recipient');assert page.locator('#pax-progress').inner_text()=='0 / 23 eingepackt'
   role('sender');assert page.locator('#pax-progress').inner_text()=='1 / 23 eingepackt'
   page.reload();ready();assert page.locator('#pax-progress').inner_text()=='1 / 23 eingepackt'
   for item in page.locator('.pax-pack-item').all()[1:21]:item.click()
   assert page.locator('#pax-progress').inner_text()=='21 / 23 eingepackt';shot('06-packing-partial')
   page.locator('#pax-incomplete').click();shot('07-missing')
   assert page.locator('#pax-missing-list li').count()==2
   assert keys('#pax-missing-list li')==outgoing[-2:]
   page.locator('#pax-really-missing').click()
   assert 'Pax anpassen' in page.locator('#pax-end-copy').inner_text()
   page.locator('#pax-end-back').click();assert page.locator('#pax-progress').inner_text()=='21 / 23 eingepackt'
   for item in page.locator('.pax-pack-item').all()[-2:]:item.click()
   assert page.locator('#pax-request').is_enabled();shot('08-packing-complete')
   page.locator('.pax-secondary-receive>summary').click()
   page.locator('.pax-album-toggle').first.click();geometry()
   page.locator('.pax-album-fan:visible button').click();geometry()
   page.locator('#pax-request').click();assert page.locator('section[data-screen=address]').is_visible();shot('09-pack-endpoint')
   page.locator('#pax-reopen-pack').click();page.locator('.pax-pack-item').first.click()
   assert page.locator('#pax-request').is_disabled()
   page.locator('.pax-dev').evaluate('(e)=>e.open=true');page.locator('#pax-advance').click()
   assert page.locator('.pax-pack-item').count()==23,'accepted trade expired'
   # Decline, withdraw, exact expiry and rejection after expiry.
   scenario('received');page.locator('#pax-decline').click();assert 'abgelehnt' in page.locator('#pax-terminal-title').inner_text();geometry()
   scenario('waiting');page.locator('#pax-withdraw').click();assert 'zurückgezogen' in page.locator('#pax-terminal-title').inner_text();geometry()
   scenario('received');page.locator('.pax-dev').evaluate('(e)=>e.open=true');page.locator('#pax-advance').click()
   assert 'abgelaufen' in page.locator('#pax-terminal-title').inner_text();geometry()
   role('sender');assert page.locator('section[data-screen=terminal]').is_visible()
   # Repeat codes remain separate clickable physical instances (16/20/1).
   page.goto(BASE+'/pax/justus?demo=packing-sender');ready();page.wait_for_load_state('networkidle')
   assert page.locator('.pax-give-album').first.locator('.trade-postit').evaluate_all('es=>es.map(e=>e.querySelectorAll(".pax-pack-item").length)')==[16,20,1]
   first=page.locator('.pax-pack-item').nth(0);second=page.locator('.pax-pack-item').nth(1)
   first.click();assert first.get_attribute('aria-pressed')=='true' and second.get_attribute('aria-pressed')=='false';geometry()
   if width==390:
    page.clock.install()
    scenario('waiting')
    page.clock.fast_forward(24*60*60*1000)
    assert 'abgelaufen' in page.locator('#pax-terminal-title').inner_text(),'live timer did not expire'
   assert not errors and not writes and not failures,(errors,writes,failures)
   results.append({'width':width,'journey':'PASS','no_overflow':True,'no_writes':True,'model':model})
   context.close()
  browser.close()
 (OUT/'checks.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results,indent=2))

if __name__=='__main__':main()
