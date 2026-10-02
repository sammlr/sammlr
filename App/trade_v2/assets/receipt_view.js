import {readState,saveState,slots,incomingSlots,initialState,perspective} from './requests.js';
import {loadSession} from './session.js';
import {ROLES,opposite,version} from './deal_versions.js';
import {ownShipped,shippingState} from './shipping_state.js';
import {receiptSide,completed,tradeState,expectedPositions,PROBLEM_TYPES} from './receipt_state.js';
import {receive,allReceived,reportProblem,proposeResolution,confirmResolution,rate} from './receipts.js';
import {RECEIPT_DEMOS,receiptDemo} from './receipt_demo.js';
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
export function startReceipt(data) {
  const $=id=>document.getElementById(id),url=new URL(location.href),role=url.searchParams.get('role')==='recipient'?'recipient':'sender',other=opposite(role);
  const base=`/trade-v2/requests/${data.deal.partner_slug}`,scenario=url.searchParams.get('receipt'),root=$('receipt-panel');
  let state,r,form=['problem-form','positions'].includes(scenario)||url.searchParams.get('view')==='problem',selection=0;
  const button=(text,id,action,secondary=false)=>{const b=node('button',text,`action${secondary?' secondary':''}`);b.id=id;b.type='button';b.addEventListener('click',action);return b;};
  const link=(text,href)=>{const a=node('a',text,'action secondary');a.href=href;return a;};
  function fail(){root.replaceChildren(node('p','Der lokale Empfangsstand ist nicht verfügbar. Bitte die Demo zurücksetzen.'));}
  try {
    if(RECEIPT_DEMOS.includes(scenario)) {
      state=receiptDemo(data.deal,scenario);saveState(sessionStorage,state);
      if(/^rating-[123]$/.test(scenario))selection=Number(scenario.at(-1));
      url.searchParams.delete('receipt');if(form)url.searchParams.set('view','problem');history.replaceState(null,'',url);
    } else state=loadSession(data.deal);
    r=state.requests[data.deal.id];
  }catch(_){fail();return;}
  $('receipt-back').href=`${base}?role=${role}`;
  for(const side of ROLES)$('role-'+side).href=`${base}/receipt?role=${side}`;
  $('role-'+role).setAttribute('aria-current','page');
  function command(action){
    try {const next=readState(sessionStorage),current=next.requests[data.deal.id];if(!current){fail();return;}action(current);saveState(sessionStorage,next);state=next;r=current;form=false;url.searchParams.delete('view');history.replaceState(null,'',url);render();$('receipt-title').focus();}
    catch(_){fail();}
  }
  function problemBlock(reporter) {
    const side=receiptSide(r,reporter),p=side.problem;if(!p)return;
    const mine=reporter===role,box=node('section',undefined,'receipt-problem');box.dataset.reporter=reporter;
    const name=perspective(r,reporter).me;
    box.append(node('h2',side.state==='RESOLVED'?'Problem geklärt':mine?'Problem gemeldet':`${name} hat ein Problem gemeldet`));
    box.append(node('p',p.types.map(t=>PROBLEM_TYPES[t]).join(', ')));
    if(p.positionIds.length){const list=node('ul');for(const i of expectedPositions(r,reporter).filter(i=>p.positionIds.includes(i.positionId)))list.append(node('li',`${i.album} · ${i.code} · Exemplar ${i.instance}`));box.append(list);}
    if(side.state==='PROBLEM_REPORTED') {
      box.append(node('p',mine?`${perspective(r,reporter).partner} kann die Meldung im Tausch sehen.`:'Kläre das Problem gemeinsam mit deinem Tauschpartner.'));
      if(!mine)box.append(button('Problem als geklärt markieren','resolution-propose',()=>command(x=>proposeResolution(x,role,reporter))));
    }
    if(side.state==='RESOLUTION_PENDING') {
      box.append(node('p',mine?'Dein Tauschpartner hat eine Klärung bestätigt. Ist das Problem für dich gelöst?':'Wartet auf die Bestätigung der meldenden Seite.'));
      if(mine)box.append(button('Ja, Problem ist geklärt','resolution-confirm',()=>command(x=>confirmResolution(x,role))));
    }
    if(side.state==='RESOLVED')box.append(node('p','Die meldende Seite hat die Lösung bestätigt. Das vereinbarte Paket bleibt unverändert.'));
    root.append(box);
  }
  function problemForm(){
    const f=node('form');f.id='problem-form';
    const types=node('fieldset');types.append(node('legend','Was ist passiert?'));
    for(const [value,text] of Object.entries(PROBLEM_TYPES)) {
      const label=node('label',undefined,'receipt-choice'),input=node('input');input.type='checkbox';input.name='problem-type';input.value=value;label.append(input,node('span',text));types.append(label);
    }
    const positions=node('fieldset');positions.append(node('legend','Welche erwarteten Sticker sind betroffen?'));
    positions.append(node('p','Bei fehlenden, falschen oder beschädigten Stickern mindestens eine Position auswählen.','intro'));
    for(const i of expectedPositions(r,role)) {
      const label=node('label',undefined,'receipt-choice'),input=node('input');input.type='checkbox';input.name='position';input.value=i.positionId;
      label.append(input,node('span',`${i.album} · ${i.code} · Exemplar ${i.instance}`));positions.append(label);
    }
    const error=node('p');error.id='problem-error';error.setAttribute('role','alert');
    const submit=button('Problem melden','problem-submit',()=>{});submit.type='submit';
    f.append(types,positions,error,submit,button('Zurück zur Prüfung','problem-back',()=>{form=false;render();$('receipt-title').focus();},true));
    f.addEventListener('submit',event=>{
      event.preventDefault();const t=[...f.querySelectorAll('[name=problem-type]:checked')].map(e=>e.value),ids=[...f.querySelectorAll('[name=position]:checked')].map(e=>e.value);
      if(!t.length || (t.some(v=>v!=='incomplete')&&!ids.length)){error.textContent='Bitte eine Problemart und die betroffenen Sticker auswählen.';return;}
      command(x=>reportProblem(x,role,t,ids));
    });root.append(f);
  }
  function rating(){
    const partner=perspective(r,role).partner,saved=r.ratings?.[role];
    if(saved){const text=node('p',`Deine Bewertung für ${partner}: ${'★'.repeat(saved.stars)}`);text.id='rating-saved';root.append(text);return;}
    const f=node('form');f.id='rating-form';const field=node('fieldset');field.append(node('legend',`Wie war der Tausch mit ${partner}?`));
    const stars=node('div',undefined,'receipt-stars');
    for(const n of [1,2,3]) {
      const label=node('label'),input=node('input'),symbol=node('span',n<=selection?'★':'☆');input.type='radio';input.name='stars';input.value=n;input.checked=selection===n;input.setAttribute('aria-label',`${n} ${n===1?'Stern':'Sterne'}`);symbol.setAttribute('aria-hidden','true');
      input.addEventListener('change',()=>{selection=n;stars.querySelectorAll('span').forEach((s,i)=>s.textContent=i<n?'★':'☆');f.querySelector('button').disabled=false;});label.append(input,symbol);stars.append(label);
    }
    field.append(stars);const save=button('Bewertung speichern','rating-save',()=>{});save.type='submit';save.disabled=!selection;
    f.append(field,save,link('Später','/trade-v2/'));f.addEventListener('submit',event=>{event.preventDefault();command(x=>rate(x,role,selection));});root.append(f);
  }
  function render(){
    root.replaceChildren();document.body.dataset.role=role;
    if(!r?.snapshot||r.status!=='accepted'){$('receipt-title').textContent=r?.status==='cancelled'?'Der Tausch wurde beendet.':'Noch kein aktiver Tausch';root.append(node('p','Für diesen Vorgang ist kein Empfang oder Rating verfügbar.'));return;}
    const view=perspective(r,role),s=receiptSide(r,role),done=completed(r);
    $('role-recipient').textContent=r.snapshot.partner;
    $('capacity-count').textContent=role==='sender'?`${slots(state)}/3 ausgehend belegt`:`${incomingSlots(state,r.snapshot.partner_id)}/3 eingehend belegt`;
    document.body.dataset.receiptState=s.state;document.body.dataset.tradeState=tradeState(r);
    $('receipt-title').textContent=done?'Tausch abgeschlossen ✓':s.state==='WAITING'?(ownShipped(r,other)?`${view.partner}s Sticker sind unterwegs`:`Deine Sendung von ${view.partner}`):s.state==='RECEIVED_UNCHECKED'?(form?'Problem melden':'Ist alles da?'):s.state==='RECEIVED_OK'?'Alles da ✓':s.state==='RESOLVED'?'Problem geklärt':'Deine Empfangsmeldung';
    root.append(node('p',done?`${view.receive_count} ↔ ${view.give_count} Sticker getauscht · Mit ${view.partner}`:`${view.receive_count} erwartete Sticker von ${view.partner}`,'deal-summary'));
    if(!ownShipped(r,other))root.append(node('p',`${view.partner} hat den Versand noch nicht bestätigt. Du kannst den tatsächlichen Empfang trotzdem bestätigen. Die Versandbestätigung bleibt unabhängig.`, 'intro'));
    if(s.state==='WAITING') {
      root.append(node('p','Bestätige erst, wenn du die Sendung tatsächlich erhalten hast.'));
      root.append(button('Sendung erhalten','receipt-receive',()=>command(x=>receive(x,role))));
    } else if(s.state==='RECEIVED_UNCHECKED') {
      if(form)problemForm();else root.append(button('Ja, alles da','receipt-ok',()=>command(x=>allReceived(x,role))),button('Problem melden','receipt-problem',()=>{form=true;render();$('receipt-title').focus();},true));
    } else if(!done&&['RECEIVED_OK','RESOLVED'].includes(s.state))root.append(node('p',`Deine Empfangsrichtung ist erledigt. ${view.partner}s Empfang ist noch nicht abgeschlossen.`));
    problemBlock(role);problemBlock(other);
    if(done){if(ROLES.some(side=>receiptSide(r,side).state==='RESOLVED'))root.append(node('p','Abgeschlossen nach gemeinsam geklärtem Problem.'));rating();}
    if(!ownShipped(r,role))root.append(node('p','Deine eigene Versandbestätigung steht noch aus. Dein operativer Platz bleibt bis dahin belegt.'),link('Eigene Sendung bearbeiten →',`${base}/shipping?role=${role}`));
    root.append(link('Zurück zur Tauschbörse','/trade-v2/'));
    $('receipt-dev').textContent=JSON.stringify({active_deal_version:version(r),my_shipping:shippingState(r,role),partner_shipping:shippingState(r,other),my_receipt:s.state,partner_receipt:receiptSide(r,other).state,problems:ROLES.map(side=>({reporter:side,state:receiptSide(r,side).state,problem:receiptSide(r,side).problem})),trade_state:tradeState(r),completed_at:r.completedAt??null,my_rating_for_partner:r.ratings?.[role]??null,partner_rating_for_me:r.ratings?.[other]??null,my_operational_slot_occupied:!ownShipped(r,role),partner_operational_slot_occupied:!ownShipped(r,other)},null,2);
  }
  $('demo-reset').addEventListener('click',()=>{try{saveState(sessionStorage,initialState(Number($('demo-count').value)));location.assign('/trade-v2/');}catch(_){fail();}});
  render();
}
