// Pure read projection. No request, physical state, snapshot or storage mutations.
import {targetAddress} from './shipping.js';
import {perspective} from './requests.js';
import {opposite} from './deal_versions.js';
import {completed,receiptSide} from './receipt_state.js';
import {ownShipped,shippingState,shippingSide,shippingAllowed} from './shipping_state.js';
export const GROUPS=[['incoming','Eingegangen'],['action','Du bist dran'],['waiting','Wartet']];
export function projectTrade(r,role,now=Date.now()){
  if(!r?.snapshot||!['sender','recipient'].includes(role)||!['pending','accepted'].includes(r.status)||completed(r))return null;
  if(r.status==='pending'&&now>=r.expiresAt)return null;
  const view=perspective(r,role),base=`/trade-v2/requests/${encodeURIComponent(r.snapshot.partner_slug)}`;
  const link=screen=>`${base}${screen?'/'+screen:''}?role=${role}`;
  const row={id:r.id,role,partner:view.partner,receive:view.receive_count,give:view.give_count,albums:view.album_count,created:r.bindingCreatedAt,expiresAt:r.status==='pending'?r.expiresAt:null};
  const result=(group,label,screen,extra={})=>({...row,group,label,href:link(screen),...extra});
  if(r.status==='pending')return role==='recipient'?result('incoming','Tauschanfrage ansehen',''):result('waiting','Wartet auf Antwort','');
  const mine=receiptSide(r,role),other=receiptSide(r,opposite(role));
  const receipt=mine.state==='WAITING'?{receiptHref:link('receipt')}:{};
  const action=(label,screen)=>result('action',label,screen,receipt);
  const wait=(label,screen)=>result('waiting',label,screen,receipt);
  if(other.state==='PROBLEM_REPORTED')return action('Problem klären','receipt');
  if(mine.state==='RESOLUTION_PENDING')return action('Lösung bestätigen','receipt');
  if(mine.state==='RECEIVED_UNCHECKED')return action('Sendung prüfen','receipt');
  if(r.amendment?.status==='pending')return r.amendment.proposer===role?wait('Wartet auf Änderung','amendment'):action('Änderung bestätigen','amendment');
  if(!ownShipped(r,role)){
    if(['missing_review','missing_reported'].includes(r.packing?.[role]?.phase))return action('Fehlmenge prüfen','next');
    const shipping=shippingState(r,role);
    if(shipping==='READY_TO_SHIP'&&!targetAddress(r,role))return wait('Wartet auf Adressfreigabe','shipping');
    if(shipping==='READY_TO_SHIP')return shippingSide(r,role).method?result('action','Versand bestätigen','shipping',{...receipt,href:link('shipping')+'&view=prepare'}):action('Versand vorbereiten','shipping');
    if(shipping==='PACKING_COMPLETE'&&!shippingAllowed(r,role))return wait('Wartet auf Fehlmengenklärung','next');
    if(shipping==='PACKING_COMPLETE')return action('Packfreigabe bestätigen','next');
    return action('Sticker raussuchen','next');
  }
  if(mine.state==='PROBLEM_REPORTED'||other.state==='RESOLUTION_PENDING')return wait('Wartet auf Problemklärung','receipt');
  if(mine.state==='WAITING')return ownShipped(r,opposite(role))?action('Empfang bestätigen','receipt'):wait('Wartet auf Versand','receipt');
  return wait('Wartet auf Empfang','receipt');
}
export function projectOverview(state,roles={},now=Date.now()){
  const order=Object.fromEntries(GROUPS.map(([id],i)=>[id,i]));
  return Object.values(state.requests).map(r=>projectTrade(r,roles[r.id]||(r.direction==='incoming'?'recipient':'sender'),now)).filter(Boolean)
    .sort((a,b)=>order[a.group]-order[b.group]||(a.expiresAt??a.created)-(b.expiresAt??b.created)||a.id.localeCompare(b.id));
}
