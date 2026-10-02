import {readState} from './requests.js';
import {dismiss} from './discovery.js';
export function proposalDismiss(deal){
  if(deal.origin!=='TOP_SUGGESTION')return;
  try{if(readState(sessionStorage).requests[deal.id])return;}catch(_){return;}
  const b=document.createElement('button');b.type='button';b.className='action secondary';b.id='dismiss-proposal';b.textContent='Vorschlag ablehnen';
  b.addEventListener('click',()=>{try{if(readState(sessionStorage).requests[deal.id])return;dismiss(sessionStorage,deal.id);location.assign('/trade-v2/');}catch(_){document.getElementById('capacity-note').textContent='Der Vorschlag konnte nicht lokal ausgeblendet werden.';}});
  document.getElementById('request-preview').after(b);
}
