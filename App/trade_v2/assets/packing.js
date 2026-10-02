import {ownShipped} from './shipping_state.js';
// Adapted from the audited PAX-05 pieces/missing/togglePiece/canContinue.
// Request remains accepted; packing is per physical direction, never a new trade.
import {perspective} from './requests.js';
const roles = ['sender', 'recipient'];
const empty = () => ({phase:'accepted', packed:[], missingReported:[]});
export function pieces(request, role) {
  return perspective(request, role)?.give.flatMap(a => a.items.map(item => ({...item, album:a.title}))) || [];
}
export function packSide(request, role) {
  return request?.packing?.[role] || empty();
}
export function validPacking(request) {
  if (request.packing === undefined) return true;
  if (!['accepted','cancelled'].includes(request.status) || !request.packing) return false;
  return roles.every(role => {
    const s = request.packing[role], keys = pieces(request,role).map(p=>p.key);
    return s && ['accepted','packing','packing_complete','missing_review','missing_reported'].includes(s.phase)
      && Array.isArray(s.packed) && new Set(s.packed).size === s.packed.length && s.packed.every(k=>keys.includes(k))
      && Array.isArray(s.missingReported) && new Set(s.missingReported).size === s.missingReported.length
      && s.missingReported.every(k=>keys.includes(k) && !s.packed.includes(k))
      && (s.phase !== 'packing_complete' || s.packed.length === keys.length)
      && (s.phase !== 'missing_reported' || (s.missingReported.length > 0 && s.missingReported.length === keys.length-s.packed.length));
  });
}
export function enterPacking(request, role) {
  if (request?.status !== 'accepted' || request.amendment?.status === 'pending' || ownShipped(request,role) || !roles.includes(role)) return false;
  request.packing ||= {sender:empty(), recipient:empty()};
  if (request.packing[role].phase === 'accepted') request.packing[role].phase = 'packing';
  return true;
}
export function missing(request, role) {
  return pieces(request,role).filter(item=>!packSide(request,role).packed.includes(item.key));
}
export function canFinish(request, role) {
  return request?.status === 'accepted' && request.amendment?.status !== 'pending' && !ownShipped(request,role) && roles.includes(role) && pieces(request,role).length > 0 && missing(request,role).length === 0;
}
export function togglePiece(request, role, key) {
  if (request?.status !== 'accepted' || request.amendment?.status === 'pending' || ownShipped(request,role) || !roles.includes(role) || packSide(request,role).phase !== 'packing'
      || !pieces(request,role).some(item=>item.key===key)) return false;
  const s = request.packing[role];
  s.packed = s.packed.includes(key) ? s.packed.filter(k=>k!==key) : [...s.packed,key];
  return true;
}
export function packAction(request, role, action) {
  if (request?.status !== 'accepted' || request.amendment?.status === 'pending' || ownShipped(request,role) || !roles.includes(role) || !request.packing) return false;
  const s = request.packing[role];
  if (action === 'finish' && s.phase === 'packing' && canFinish(request,role)) {s.phase='packing_complete';return true;}
  if (action === 'review' && s.phase === 'packing' && missing(request,role).length) {s.phase='missing_review';return true;}
  if (action === 'back' && s.phase === 'missing_review') {s.phase='packing';return true;}
  if (action === 'report' && s.phase === 'missing_review' && missing(request,role).length) {
    s.missingReported=missing(request,role).map(p=>p.key);s.phase='missing_reported';return true;
  }
  return false;
}
