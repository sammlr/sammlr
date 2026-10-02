"""PAX-06: gating, directional shipping and conceptual operational capacity."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from App.pax.fixtures import CANDIDATES
BASE='http://127.0.0.1:8094'
OUT=Path(__file__).parent/'artifacts/pax-06'
MODEL=r'''async candidates=>{
 const m=await import('/static/pax/lifecycle.js'),s=await import('/static/pax/shipping.js');
 const assert=(v,msg)=>{if(!v)throw Error(msg);};
 for(const c of candidates){
  const d=m.createDeal(c),original=JSON.stringify(d);
  let state=m.initialState();
  assert(s.targetAddress(d,state,'sender')===null,'discovery address');
  state=m.transition(state,'request','sender',1000);
  assert(s.targetAddress(d,state,'recipient')===null,'pending address');
  assert(s.operationalSlots(state,'sender').outgoing===3,'pending slot');
  state=m.transition(state,'accept','recipient',1001);
  assert(s.operationalSlots(state,'sender').outgoing===3,'accept retains slot');
  assert(s.operationalSlots(state,'recipient').incoming===3,'incoming direction');
  for(const item of m.pieces(d,'sender').slice(0,-1))state=m.togglePiece(d,state,'sender',item.key);
  assert(s.releasePacking(d,state,'sender')===state,'incomplete release rejected');
  assert(s.targetAddress(d,state,'sender')===null,'incomplete address');
  assert(s.confirmShipment(d,state,'sender')===state,'incomplete cannot ship');
  const last=m.pieces(d,'sender').at(-1);state=m.togglePiece(d,state,'sender',last.key);
  assert(s.targetAddress(d,state,'sender')===null,'complete still requires release');
  state=s.releasePacking(d,state,'sender');
  assert(s.shippingPhase(state,'sender')==='READY_TO_SHIP','ready state');
  assert(s.targetAddress(d,state,'sender')===d.participants.recipient.address,'sender target canonical');
  assert(s.targetAddress(d,state,'recipient')===null,'other side still gated');
  const revoked=structuredClone(d);revoked.participants.recipient.addressReleased=false;
  assert(s.targetAddress(revoked,state,'sender')===null,'owner release required');
  assert(s.confirmShipment(d,state,'sender')===state,'method missing');
  state=s.chooseMethod(d,state,'sender','brief');
  assert(!state.shipped.sender,'method does not ship');
  assert(s.confirmShipment(revoked,state,'sender')===state,'no ship without owner release');
  assert(s.chooseMethod(d,state,'sender','invented')===state,'no invented shipping product');
  state=s.confirmShipment(d,state,'sender');
  assert(state.shipped.sender&&!state.shipped.recipient,'own direction only');
  assert(s.operationalSlots(state,'sender').outgoing===2,'own slot released');
  assert(s.operationalSlots(state,'recipient').incoming===3,'partner slot retained');
  assert(s.shippingPhase(state,'sender')==='SHIPPED_BY_ME'&&s.shippingPhase(state,'recipient')==='SHIPPED_BY_PARTNER','directional views');
  assert(s.confirmShipment(d,state,'sender')===state,'idempotent confirmation');
  assert(s.reopenPacking(state,'sender')===state,'no reopening shipped package');
  assert(m.togglePiece(d,state,'sender',last.key)===state,'no editing shipped list');
  assert(state.status==='packing','trade not complete');
  for(const item of m.pieces(d,'recipient'))state=m.togglePiece(d,state,'recipient',item.key);
  state=s.releasePacking(d,state,'recipient');
  assert(s.targetAddress(d,state,'recipient')===d.participants.sender.address,'recipient target canonical');
  assert(d.participants.sender.address!==d.participants.recipient.address,'different addresses');
  state=s.chooseMethod(d,state,'recipient','brief');state=s.confirmShipment(d,state,'recipient');
  assert(s.shippingPhase(state,'sender')==='BOTH_SHIPPED','both shipped');
  assert(s.operationalSlots(state,'recipient').incoming===2,'recipient incoming slot released');
  assert(state.status==='packing'&&!('received' in state)&&!('rating' in state),'no premature completion/receipt/rating');
  assert(m.validState(d,state),'restore valid shipped state');
  assert(!m.validState(d,{...state,ready:{sender:false,recipient:true}}),'invalid released state');
  assert(JSON.stringify(d)===original,'deal frozen unchanged');
 }
 return {candidates:candidates.length,gating:true,directional:true,slots:true,idempotent:true};
}'''

def main():
 OUT.mkdir(parents=True,exist_ok=True);results=[]
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in (375,390,430):
   context=browser.new_context(viewport={'width':width,'height':844},has_touch=True,reduced_motion='reduce')
   page=context.new_page();errors=[];writes=[];external=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
   page.on('request',lambda r:external.append(r.url) if not r.url.startswith(BASE) else None)
   def scenario(name):
    page.goto(BASE+'/pax/fatima?demo='+name);page.wait_for_function('document.body.dataset.screen!==undefined');page.wait_for_load_state('networkidle')
   def state():return page.evaluate("JSON.parse(sessionStorage.getItem('sammlr-pax-06:fatima')).state")
   def geometry():
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('.pax-address-note,.trade-postit').evaluate_all('es=>es.filter(e=>e.checkVisibility()).every(e=>{const r=e.getBoundingClientRect();return r.x>=0&&r.right<=innerWidth&&e.scrollWidth<=e.clientWidth})')
   def shot(name,dev=False,viewport=False):
    geometry()
    if width==390:
     page.locator('.pax-dev').evaluate('(e,open)=>e.open=open',dev)
     if not viewport:page.evaluate('scrollTo(0,0)')
     page.screenshot(path=str(OUT/(name+'.png')),full_page=not viewport)
   def role(name):
    page.locator('.pax-dev').evaluate('e=>e.open=true');page.locator(f'[data-role={name}]').click()
   def no_address():assert page.locator('[data-pax-address]').evaluate_all('es=>es.every(e=>!e.textContent)')
   scenario('opened');model=page.evaluate(MODEL,list(CANDIDATES));no_address()
   scenario('received');no_address()
   scenario('complete');no_address();shot('01-packed-23')
   page.locator('.pax-pack-item').first.tap();assert '22 / 23' in page.locator('#pax-progress').inner_text();no_address()
   assert page.locator('#pax-request').is_disabled()
   page.locator('#pax-incomplete').click();no_address();assert page.locator('#pax-missing-list li').count()==1
   page.locator('#pax-return').click();page.locator('.pax-pack-item').first.click();no_address()
   page.locator('#pax-request').scroll_into_view_if_needed();shot('02-finish-packing',viewport=True)
   page.locator('#pax-request').focus();page.keyboard.press('Enter')
   assert page.locator('section[data-screen=address]').is_visible();assert not state()['shipped']['sender'];shot('03-address')
   address=page.locator('section[data-screen=address] address').inner_text();assert 'Fatima Beispiel' in address
   # No bypass after returning to packing and removing a mark.
   page.locator('#pax-reopen-pack').click();page.locator('.pax-pack-item').first.click();no_address()
   page.locator('.pax-pack-item').first.click();page.locator('#pax-request').click()
   page.locator('#pax-prepare-shipping').tap();shot('04-shipping')
   assert page.locator('#pax-confirm-shipment').is_disabled()
   page.locator('#pax-shipping-method').select_option('brief');assert not state()['shipped']['sender']
   page.locator('#pax-portal').click();shot('05-portal-demo');assert not state()['shipped']['sender']
   page.locator('#pax-portal-back').click();shot('06-before-confirmation')
   assert not state()['shipped']['recipient'];shot('09-dev-before',dev=True)
   assert 'Outgoing operational slots: 3 / 3' in page.locator('#pax-shipping-dev').text_content()
   page.locator('#pax-confirm-shipment').focus();page.keyboard.press('Space')
   assert page.locator('section[data-screen=shipped]').is_visible()
   assert state()['shipped']=={'sender':True,'recipient':False}
   assert page.locator('#pax-partner-shipping').inner_text()=='Wartet auf Versand';shot('07-own-shipped')
   no_address();assert page.locator('.pax-pack-item:visible').count()==0
   assert 'Outgoing operational slots: 2 / 3' in page.locator('#pax-shipping-dev').text_content();shot('10-dev-after',dev=True)
   page.reload();page.wait_for_function('document.body.dataset.screen==="shipped"');assert state()['shipped']['sender']
   role('recipient');no_address();assert 'Incoming operational slots: 3 / 3' in page.locator('#pax-shipping-dev').text_content()
   for item in page.locator('.pax-pack-item').all():item.click()
   page.locator('#pax-request').click();assert 'Valentin Beispiel' in page.locator('section[data-screen=address] address').inner_text();shot('11-recipient-address')
   page.locator('#pax-prepare-shipping').click();page.locator('#pax-shipping-method').select_option('brief');page.locator('#pax-confirm-shipment').click()
   assert state()['shipped']=={'sender':True,'recipient':True}
   assert 'Incoming operational slots: 2 / 3' in page.locator('#pax-shipping-dev').text_content()
   role('sender');assert page.locator('#pax-partner-shipping').inner_text()=='Unterwegs';shot('08-both-shipped')
   assert state()['status']=='packing'
   assert page.locator('section[data-screen=shipped] button:visible').all_text_contents()==[],'Product shipped view should have no new action'
   for name in ('address','shipping','shipped-me','shipped-partner','both-shipped'):
    scenario(name);geometry()
   assert not errors and not writes and not external,(errors,writes,external)
   results.append({'width':width,'journey':'PASS','external_requests':0,'write_requests':0,'model':model});context.close()
  browser.close()
 (OUT/'checks.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))

if __name__=='__main__':main()
