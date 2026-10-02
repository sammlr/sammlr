import {releasePacking} from './shipping.js';
import {ownShipped,shippingSide,bothShipped} from './shipping_state.js';
import {createShippingPanel,shippingDev} from './shipping_panel.js';
import {proposeAmendment} from './amendments.js';
import {version} from './deal_versions.js';
import {renderGive} from '/static/pax/pax.js';
import {renderReceive} from './receive.js';
import {confirmPackage,reportMissing} from './packing_confirmation.js';
import {readState, saveState, initialState, send, decide, perspective, slots, incomingSlots} from './requests.js';
import {loadSession} from './session.js';
import {pieces, packSide, validPacking, enterPacking, togglePiece, missing, canFinish, packAction} from './packing.js';

export function startPacking(data) {
  const $ = id=>document.getElementById(id);
  const url = new URL(location.href), role = url.searchParams.get('role') === 'recipient' ? 'recipient' : 'sender';
  const other = role === 'sender' ? 'recipient' : 'sender';
  const base = `/trade-v2/requests/${data.deal.partner_slug}`;
  let state, request, view, selectingMissing=false;
  const shippingPanel=createShippingPanel($('ship-panel'),role,base,action=>{command(action);$('ship-heading')?.focus();});
  document.body.classList.add('trade-packing');
  $('pack-back-status').href=`${base}?role=${role}`;
  $('pack-amendment').href=`${base}/amendment?role=${role}`;
  $('pack-completed-list').href=`${base}/next?role=${role}&view=packed`;
  $('role-sender').href=`${base}/next?role=sender`;
  $('role-recipient').href=`${base}/next?role=recipient`;
  $('role-'+role).setAttribute('aria-current','page');
  function fail(message='Der lokale Packstand konnte nicht gespeichert werden.') {
    $('pack-main').hidden=true;$('pack-outcome').hidden=false;
    $('pack-outcome-title').textContent=message;$('pack-outcome-copy').textContent='';
    $('pack-missing-actions').hidden=true;$('pack-missing-list').replaceChildren();
  }
  try {
    const scenario = url.searchParams.get('pack');
    if (['zero','partial','22','23','complete','review','reported'].includes(scenario)) {
      state=initialState(2);request=send(state,data.deal,Date.now()).request;
      decide(state,request.id,'recipient','accept',Date.now());enterPacking(request,role);
      const all=pieces(request,role), n = scenario==='zero' ? 0 : ['23','complete'].includes(scenario) ? all.length : scenario==='22' ? Math.max(0,all.length-1) : Math.max(0,all.length-2);
      all.slice(0,n).forEach(item=>togglePiece(request,role,item.key));
      if (scenario==='complete') {packAction(request,role,'finish');releasePacking(request,role);}
      if (['review','reported'].includes(scenario)) packAction(request,role,'review');
      if (scenario==='reported') packAction(request,role,'report');
      saveState(sessionStorage,state);url.searchParams.delete('pack');history.replaceState(null,'',url);
    } else state=loadSession(data.deal);
    request=state.requests[data.deal.id];
    if (request?.status==='cancelled' || (request?.amendment?.status==='pending' && packSide(request,role).phase!=='missing_reported')) {location.replace(`${base}/amendment?role=${role}`);return;}
    if (!request || request.status!=='accepted') {fail('Noch kein aktiver Tausch');return;}
    if (!validPacking(request)) {fail('Ungültiger lokaler Packstand');return;}
    enterPacking(request,role);
    if (packSide(request,role).phase==='missing_reported') proposeAmendment(request,role);
    saveState(sessionStorage,state);view=perspective(request,role);
  } catch (_) {fail();return;}
  $('pack-title').textContent=`${view.give_count} Sticker für ${view.partner}`;
  $('pack-subtitle').textContent=ownShipped(request,other)?`${view.partner}s Sticker sind unterwegs zu dir. Du musst deine Sticker noch packen.`:'Prüfe die Sticker, die du verschicken wirst.';
  $('role-recipient').textContent=view.side_b;
  renderGive(view.give);renderReceive(view.receive);
  function command(action) {
    try {
      const next=readState(sessionStorage), r=next.requests[data.deal.id];
      if (!r || !validPacking(r) || JSON.stringify(r.snapshot)!==JSON.stringify(request.snapshot)) {fail('Ungültiger lokaler Packstand');return;}
      action(r);
      if (packSide(r,role).phase==='missing_reported') proposeAmendment(r,role);
      saveState(sessionStorage,next);state=next;request=r;render();
    } catch (_) {fail();}
  }
  function showOutcome(title,copy,review=false) {
    $('pack-outcome-title').textContent=title;$('pack-outcome-copy').textContent=copy;
    $('pack-missing-actions').hidden=!review;$('pack-missing-list').replaceChildren();
    $('pack-missing-options').replaceChildren();
    if(review){
      const defaults=packSide(request,role).phase==='missing_review'?missing(request,role).map(i=>i.key):[];
      for(const item of pieces(request,role)){
        const label=document.createElement('label'),input=document.createElement('input'),text=document.createElement('span');input.type='checkbox';input.name='missing';input.value=item.key;input.checked=defaults.includes(item.key);
        text.textContent=`${item.album} · ${item.code} · Exemplar ${item.instance}`;label.append(input,text);$('pack-missing-options').append(label);
      }
      const update=()=>{$('pack-report').disabled=!$('pack-missing-options').querySelector('input:checked');};$('pack-missing-options').addEventListener('change',update,{once:false});update();
    }

  }
  function render() {
    const own=packSide(request,role), partner=packSide(request,other), total=pieces(request,role).length, count=own.packed.length;
    const previous=document.body.dataset.packPhase;
    document.body.dataset.packPhase=own.phase;document.body.dataset.role=role;
    const reviewing=selectingMissing||own.phase==='missing_review';
    const showPacked=own.phase==='packing_complete' && !ownShipped(request,role) && url.searchParams.get('view')==='packed';
    $('pack-main').hidden=reviewing||(own.phase!=='packing' && !showPacked);$('pack-outcome').hidden=!reviewing&&(own.phase==='packing' || showPacked);
    document.querySelector('#pack-main .pack-actions').hidden=showPacked;
    $('pack-completed-list').hidden=own.phase!=='packing_complete' || showPacked || version(request)<2 || ownShipped(request,role);
    $('pack-amendment').hidden=own.phase!=='missing_reported';
    if (request.amendment?.status==='pending') { $('role-sender').href=`${base}/amendment?role=sender`;$('role-recipient').href=`${base}/amendment?role=recipient`; }
    $('pack-progress').textContent=`${total} Sticker auf deiner Packliste`;
    $('pack-finish').disabled=own.phase!=='packing'||ownShipped(request,role)||request.amendment?.status==='pending';$('pack-review').hidden=false;
    if (own.phase==='packing_complete') showOutcome(ownShipped(request,role)?'Versandstatus':'Packprüfung abgeschlossen.',ownShipped(request,role)?'':shippingSide(request,role).releasedVersion===version(request)?'Deine Packfreigabe ist bestätigt.':'Bestätige die Packfreigabe für dein aktuelles Paket.');
    if (own.phase==='packing_complete' && !showPacked) shippingPanel.render(request);else $('ship-panel').replaceChildren();
    $('ship-dev').textContent=shippingDev(request,role);
    if(reviewing)showOutcome('Welche Sticker fehlen?','Wähle nur die vereinbarten Sticker aus, die du tatsächlich nicht bereitstellen kannst.',true);
    if (own.phase==='missing_reported') showOutcome('Fehlende Sticker gemeldet.','Die Gegenseite muss der konkreten Änderung zustimmen.');
    $('capacity-count').textContent=role==='sender' ? `${slots(state)}/3 ausgehend belegt` : `${incomingSlots(state,request.snapshot.partner_id)}/3 eingehend belegt`;
    $('pack-dev').textContent=`Role: ${role}\nRequest-State: ${request.status}\nTrade-State (my direction): ${own.phase}\nMy packing count: ${count}/${total}\nMy packing complete: ${own.phase==='packing_complete'}\nActive deal version: ${version(request)}\nPartner packing count: ${partner.packed.length}/${pieces(request,other).length}\nPartner packing complete: ${partner.phase==='packing_complete'}\nMissing reported: ${own.missingReported.length}\nOperational slot occupied: ${!ownShipped(request,role)}`;
    if (previous && previous!==own.phase) {
      window.scrollTo(0,0);$(own.phase==='packing'?'pack-title':'pack-outcome-title').focus({preventScroll:true});
    }
  }
  $('pack-finish').addEventListener('click',()=>command(r=>confirmPackage(r,role)));
  $('pack-review').addEventListener('click',()=>{if(packSide(request,role).phase!=='packing'||ownShipped(request,role))return;selectingMissing=true;render();$('pack-outcome-title').focus();});
  $('pack-return').addEventListener('click',()=>{selectingMissing=false;if(packSide(request,role).phase==='missing_review')command(r=>packAction(r,role,'back'));else render();});
  $('pack-report').addEventListener('click',()=>{
    const keys=[...$('pack-missing-options').querySelectorAll('input:checked')].map(i=>i.value);
    if(!keys.length)return;
    selectingMissing=false;command(r=>{if(packSide(r,role).phase==='missing_review')packAction(r,role,'back');reportMissing(r,role,keys);});
  });
  $('demo-reset').addEventListener('click',()=>{try{saveState(sessionStorage,initialState(Number($('demo-count').value)));location.assign(`${base}?role=${role}`);}catch(_){fail();}});
  render();
}
