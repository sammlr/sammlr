// UI adapter: explicit whole-package assertion, not per-sticker ticking.
// Existing packing/version/shipping validation and transitions remain authoritative.
import {pieces,packSide,packAction,validPacking} from './packing.js';
import {ownShipped} from './shipping_state.js';
import {releasePacking} from './shipping.js';
const allowed=(r,role)=>['sender','recipient'].includes(role)&&r?.status==='accepted'&&r.amendment?.status!=='pending'&&!ownShipped(r,role)&&validPacking(r)&&packSide(r,role).phase==='packing';
export function confirmPackage(r,role){
  if(!allowed(r,role)||!pieces(r,role).length)return false;
  r.packing[role].packed=pieces(r,role).map(i=>i.key);
  return packAction(r,role,'finish')&&releasePacking(r,role);
}
export function reportMissing(r,role,keys){
  if(!allowed(r,role)||!Array.isArray(keys)||!keys.length||new Set(keys).size!==keys.length||!keys.every(k=>pieces(r,role).some(i=>i.key===k)))return false;
  r.packing[role].packed=pieces(r,role).filter(i=>!keys.includes(i.key)).map(i=>i.key);
  return packAction(r,role,'review')&&packAction(r,role,'report');
}
