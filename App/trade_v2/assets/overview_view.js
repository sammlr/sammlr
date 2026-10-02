import {readState,saveState} from './requests.js';
import {GROUPS,projectOverview} from './overview.js';
import {ROLE_KEY,SCENARIOS,overviewDemo} from './overview_demo.js';
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
export function startOverview(data){
 const root=document.getElementById('trade-active'),url=new URL(location.href),scenario=url.searchParams.get('overview');
 if(SCENARIOS.includes(scenario)){
  const {state,roles}=overviewDemo(data.deals,scenario);saveState(sessionStorage,state);sessionStorage.setItem(ROLE_KEY,JSON.stringify({roles,bindings:Object.fromEntries(Object.values(state.requests).map(r=>[r.id,r.bindingCreatedAt]))}));
  url.searchParams.delete('overview');history.replaceState(null,'',url);
 }
 let signature;
 function render(){
  try{
   const now=Date.now(),state=readState(sessionStorage),meta=JSON.parse(sessionStorage.getItem(ROLE_KEY)||'{}'),roles=Object.fromEntries(Object.entries(meta.roles||{}).filter(([id])=>state.requests[id]?.bindingCreatedAt===meta.bindings?.[id]));
   const rows=projectOverview(state,roles,now),next=JSON.stringify(rows);
   if(next===signature)return;signature=next;root.replaceChildren();
   if(!rows.length){root.append(node('p','Keine laufenden Tausche.'));const a=node('a','Tauschpartner finden','action secondary');a.href='/trade-v2/partners';root.append(a);return;}
   for(const [group,title] of GROUPS){
    const entries=rows.filter(r=>r.group===group);if(!entries.length)continue;
    const section=node('section',undefined,'overview-group');section.dataset.group=group;
    const h=node('h2',title);h.id='overview-'+group;section.setAttribute('aria-labelledby',h.id);section.append(h);
    const list=node('ul');
    for(const row of entries){
     const li=node('li',undefined,'overview-row');li.dataset.request=row.id;
     const a=node('a',undefined,'overview-primary');a.href=row.href;
     const head=node('span',undefined,'overview-head');head.append(node('strong',row.partner),node('span',`${row.receive} ↔ ${row.give}`));
     a.append(head,node('span',`${row.albums} Alben`,'overview-meta'),node('span',row.label,'overview-status'));
     if(row.expiresAt){const time=node('time','Läuft ab: '+new Intl.DateTimeFormat('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(row.expiresAt),'overview-deadline');time.dateTime=new Date(row.expiresAt).toISOString();a.append(time);}
     li.append(a);
     if(row.receiptHref&&row.label!=='Empfang bestätigen'){const receipt=node('a','Sendung bereits erhalten?','overview-receipt');receipt.href=row.receiptHref;li.append(receipt);}
     list.append(li);
    }
    section.append(list);root.append(section);
   }
  }catch(_){signature=null;root.replaceChildren(node('p','Der lokale Tauschstand ist nicht verfügbar.'));}
 }
 let timer;const resume=()=>{render();clearInterval(timer);timer=setInterval(render,1000);};
 resume();addEventListener('pagehide',()=>clearInterval(timer));addEventListener('pageshow',resume);
}
