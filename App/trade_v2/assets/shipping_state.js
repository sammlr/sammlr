// Read-only directional projections shared by storage, packing and shipping commands.
import {ROLES, version} from './deal_versions.js';
export const ownShipped=(r,role)=>ROLES.includes(role) && Boolean(role==='sender'?r.ownShipped:r.recipientShipped);
export const shippingSide=(r,role)=>r.shipping?.[role] || {releasedVersion:null,method:null,shippedAt:null};
export function fullyPacked(r,role) {
  if (!ROLES.includes(role) || !r.snapshot) return false;
  const keys=r.snapshot[role==='sender'?'give':'receive'].flatMap(a=>a.items.map(i=>i.key));
  const own=r.packing?.[role];
  return keys.length>0 && own?.phase==='packing_complete' && own.packed.length===keys.length && new Set(own.packed).size===keys.length && keys.every(k=>own.packed.includes(k));
}
export function shippingAllowed(r,role) {
  return r.status==='accepted' && fullyPacked(r,role) && r.amendment?.status!=='pending'
    && !ROLES.some(side=>r.packing?.[side]?.phase==='missing_reported');
}
export function shippingState(r,role) {
  if (ownShipped(r,role)) return 'SHIPPED';
  if (shippingAllowed(r,role) && shippingSide(r,role).releasedVersion===version(r)) return 'READY_TO_SHIP';
  return fullyPacked(r,role)?'PACKING_COMPLETE':'PACKING';
}
export const bothShipped=r=>ownShipped(r,'sender') && ownShipped(r,'recipient');
export function validShipping(r) {
  if (r.shipping===undefined) return true; // Earlier explicit QA shipped flags remain readable.
  if (!r.shipping || !r.snapshot) return false;
  return ROLES.every(role=>{
    const s=r.shipping[role];
    if (!s || ![null,version(r)].includes(s.releasedVersion) || ![null,'brief'].includes(s.method)) return false;
    if (s.releasedVersion!==null && !fullyPacked(r,role)) return false;
    if (s.method!==null && s.releasedVersion===null) return false;
    if (ownShipped(r,role)) return r.status==='accepted' && s.releasedVersion===version(r) && s.method==='brief' && Number.isFinite(s.shippedAt);
    return s.shippedAt===null;
  });
}
