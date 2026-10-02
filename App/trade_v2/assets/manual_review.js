import {readDraft,buildDeal,validate} from './manual_rules.js';
import {readState,saveState,send,slots,initialState} from './requests.js';
import {renderReceive} from './receive.js';
import {renderGive} from '/static/pax/pax.js';
export function startManualReview(data){
  const $=id=>document.getElementById(id),slug=data.partner.slug,button=$('request-preview'),note=$('capacity-note');let busy=false;
  function current(){
    const state=readState(sessionStorage),existing=state.requests['manual-'+slug];
    if(existing)return {state,deal:existing.snapshot,existing};
    const draft=readDraft(sessionStorage,slug,data.contexts),context=data.contexts[draft.scenario];
    if(!validate(context,draft).ok)throw Error('invalid');
    return {state,deal:buildDeal(context,draft)};
  }
  let initial;
  function fail(){button.disabled=true;note.textContent='Diese Auswahl ist nicht sendbar. Bitte gehe zurück und prüfe deine Sticker.';}
  try{
    initial=current();renderReceive(initial.deal.receive);renderGive(initial.deal.give);
    document.querySelector('.deal-summary').textContent=`${initial.deal.receive_count} ↔ ${initial.deal.give_count} · ${initial.deal.album_count} Alben`;
    document.querySelector('.eyebrow').textContent='Deine manuelle Auswahl';
    button.textContent=initial.existing?'Zum Tausch':'Tauschanfrage senden';
    $('capacity-count').textContent=`${slots(initial.state)}/3 ausgehend belegt`;
    button.disabled=!initial.existing&&slots(initial.state)>=3;
    if(button.disabled)note.textContent='Deine 3 ausgehenden Plätze sind belegt.';
  }catch(_){fail();}
  button.addEventListener('click',()=>{
    if(busy||!initial)return;busy=true;
    try{
      const latest=current();
      if(!latest.existing&&JSON.stringify(latest.deal)!==JSON.stringify(initial.deal)){fail();busy=false;return;}
      const result=send(latest.state,latest.deal,Date.now());
      if(result.status==='full'){button.disabled=true;note.textContent='Deine 3 ausgehenden Plätze sind belegt.';busy=false;return;}
      saveState(sessionStorage,latest.state);location.assign('/trade-v2/requests/'+latest.deal.partner_slug);
    }catch(_){fail();busy=false;}
  });
  $('demo-reset').addEventListener('click',()=>{saveState(sessionStorage,initialState(Number($('demo-count').value)));location.reload();});
}
