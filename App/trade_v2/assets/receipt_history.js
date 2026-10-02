import {readState,expire,saveState} from './requests.js';
import {completed} from './receipt_state.js';
const node=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
export function renderHistory(state) {
  const records=Object.values(state.requests).filter(completed);
  if(!records.length)return;
  const section=node('section');section.id='trade-history';section.setAttribute('aria-labelledby','history-title');
  const h=node('h2','Erledigt');h.id='history-title';section.append(h);
  for(const r of records){const a=node('a',`${r.snapshot.partner} · ${r.snapshot.receive_count} ↔ ${r.snapshot.give_count} · Abgeschlossen`);a.className='partner-row';a.href=`/trade-v2/requests/${r.snapshot.partner_slug}/receipt`;section.append(a);}
  document.getElementById('main').append(section);
}
export function receiptLink(deal) {
  try {
    if(document.getElementById('receipt-link'))return;
    const r=readState(sessionStorage).requests[deal.id];if(r?.status!=='accepted')return;
    const role=new URL(location.href).searchParams.get('role')==='recipient'?'recipient':'sender';
    const a=node('a',completed(r)?'Abschluss und Bewertung →':'Empfang der Partner-Sendung →');a.id='receipt-link';a.className='action secondary';a.style.marginTop='18px';a.href=`/trade-v2/requests/${deal.partner_slug}/receipt?role=${role}`;
    document.getElementById('capacity-count').before(a);
  }catch(_){/* Existing page retains its storage error/reset UI. */}
}

export function renderActive(){
  const root=document.getElementById('trade-active');
  try{const state=readState(sessionStorage),before=JSON.stringify(state);expire(state,Date.now());if(JSON.stringify(state)!==before)saveState(sessionStorage,state);const records=Object.values(state.requests).filter(r=>r.snapshot&&['pending','accepted'].includes(r.status)&&!completed(r));
    if(!records.length)root.append(node('p','Keine laufenden Anfragen oder Tausche.'));
    for(const r of records){const a=node('a',`${r.snapshot.partner} · ${r.snapshot.receive_count} ↔ ${r.snapshot.give_count} · ${r.status==='pending'?'Anfrage':'Laufender Tausch'}`);a.className='partner-row';a.href=`/trade-v2/requests/${r.snapshot.partner_slug}`;root.append(a);}renderHistory(state);
  }catch(_){root.append(node('p','Der lokale Tauschstand ist nicht verfügbar.'));}
}
