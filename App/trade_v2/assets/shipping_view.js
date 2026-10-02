import {readState,saveState,slots,incomingSlots,initialState} from './requests.js';
import {loadSession} from './session.js';
import {createShippingPanel,shippingDev} from './shipping_panel.js';
import {SHIPPING_DEMOS,shippingDemo} from './shipping_demo.js';
export function startShipping(data) {
  const $=id=>document.getElementById(id),url=new URL(location.href),role=url.searchParams.get('role')==='recipient'?'recipient':'sender';
  const base=`/trade-v2/requests/${data.deal.partner_slug}`,scenario=url.searchParams.get('ship');
  let state,request;
  const view=['ready','v2-ready'].includes(scenario)?'prepare':url.searchParams.get('view');
  const panel=createShippingPanel($('ship-panel'),role,base,command,view);
  $('ship-back').href=`${base}?role=${role}`;
  for(const side of ['sender','recipient'])$('role-'+side).href=`${base}/shipping?role=${side}`;
  $('role-'+role).setAttribute('aria-current','page');
  function fail(){ $('ship-panel').replaceChildren();$('ship-panel').textContent='Der lokale Versandstand ist nicht verfügbar. Bitte die Demo zurücksetzen.'; }
  try {
    if (SHIPPING_DEMOS.includes(scenario)) {
      state=shippingDemo(data.deal,scenario);saveState(sessionStorage,state);
      url.searchParams.delete('ship');if(view==='prepare')url.searchParams.set('view','prepare');history.replaceState(null,'',url);
    } else state=loadSession(data.deal);
    if (scenario==='amendment-blocked') {location.replace(`${base}/amendment?role=${role}`);return;}
    request=state.requests[data.deal.id];if(!request){fail();return;}
  } catch(_){fail();return;}
  function render(){
    panel.render(request);document.body.dataset.role=role;
    $('capacity-count').textContent=role==='sender'?`${slots(state)}/3 ausgehend belegt`:`${incomingSlots(state,request.snapshot.partner_id)}/3 eingehend belegt`;
    $('role-recipient').textContent=request.snapshot.partner;$('ship-dev').textContent=shippingDev(request,role);
  }
  function command(action){
    try {const next=readState(sessionStorage),r=next.requests[data.deal.id];if(!r){fail();return;}action(r);saveState(sessionStorage,next);state=next;request=r;render();$('ship-heading')?.focus();}
    catch(_){fail();}
  }
  $('demo-reset').addEventListener('click',()=>{try{saveState(sessionStorage,initialState(Number($('demo-count').value)));location.assign(base);}catch(_){fail();}});
  render();
}
