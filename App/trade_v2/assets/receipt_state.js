// Receiving roles refer to the OTHER participant's physical package. Q2 is retained.
import {ROLES,opposite,positions,version} from './deal_versions.js';
export const RECEIPT_STATES=['WAITING','RECEIVED_UNCHECKED','RECEIVED_OK','PROBLEM_REPORTED','RESOLUTION_PENDING','RESOLVED'];
export const PROBLEM_TYPES={missing:'Sticker fehlt',wrong:'Falscher Sticker',damaged:'Sticker beschädigt',incomplete:'Sendung sonst unvollständig'};
export const receiptSide=(r,role)=>r?.receipts?.[role] || {state:'WAITING',receivedAt:null,version:null,problem:null};
export const finalReceipt=s=>['RECEIVED_OK','RESOLVED'].includes(s.state);
export const hasReceipt=r=>ROLES.some(role=>receiptSide(r,role).state!=='WAITING');
export const completed=r=>r?.status==='accepted' && ROLES.every(role=>finalReceipt(receiptSide(r,role)));
export const tradeState=r=>r?.status==='cancelled'?'CANCELLED':completed(r)?'COMPLETED':'ACTIVE';
export const expectedPositions=(r,role)=>ROLES.includes(role)&&r?.snapshot?positions(r.snapshot,opposite(role)):[];
const unique=a=>Array.isArray(a) && new Set(a).size===a.length;
export function validProblem(r,role,p) {
  return p && p.reporter===role && p.version===version(r) && unique(p.types) && p.types.length>0
    && p.types.every(t=>Object.hasOwn(PROBLEM_TYPES,t)) && unique(p.positionIds)
    && p.positionIds.every(id=>expectedPositions(r,role).some(i=>i.positionId===id))
    && (!p.types.some(t=>t!=='incomplete') || p.positionIds.length>0);
}
export function validReceipt(r) {
  if(r.receipts===undefined) return r.completedAt===undefined && r.ratings===undefined;
  if(r.status!=='accepted' || !r.receipts) return false;
  if(!ROLES.every(role=>{
    const s=r.receipts[role];
    if(!s || !RECEIPT_STATES.includes(s.state)) return false;
    if(s.state==='WAITING') return s.receivedAt===null && s.version===null && s.problem===null;
    if(!Number.isFinite(s.receivedAt) || s.version!==version(r)) return false;
    if(['RECEIVED_UNCHECKED','RECEIVED_OK'].includes(s.state)) return s.problem===null;
    const p=s.problem;
    if(!validProblem(r,role,p) || !Number.isFinite(p.reportedAt) || p.reportedAt<s.receivedAt) return false;
    if(s.state==='PROBLEM_REPORTED') return p.proposedAt===null && p.resolvedAt===null;
    if(!Number.isFinite(p.proposedAt) || p.proposedAt<p.reportedAt || p.proposedBy!==opposite(role)) return false;
    return s.state==='RESOLUTION_PENDING'?p.resolvedAt===null:Number.isFinite(p.resolvedAt) && p.resolvedAt>=p.proposedAt && p.resolvedBy===role;
  })) return false;
  if(completed(r)!==Number.isFinite(r.completedAt)) return false;
  if(r.ratings!==undefined && (!completed(r) || !r.ratings || Object.keys(r.ratings).some(k=>!ROLES.includes(k)))) return false;
  return ROLES.every(role=>{
    const rating=r.ratings?.[role];
    return rating===undefined || (rating && Number.isInteger(rating.stars) && rating.stars>=1 && rating.stars<=3 && rating.forRole===opposite(role) && Number.isFinite(rating.savedAt) && rating.savedAt>=r.completedAt);
  });
}
