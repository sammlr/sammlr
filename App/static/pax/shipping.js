/* Isolated PAX-06 projection/commands. No inventory, HTTP or carrier integration. */
import {canContinue} from './lifecycle.js';
export const otherRole = role => {
  if (!['sender','recipient'].includes(role)) throw Error('Unknown demo role');
  return role === 'sender' ? 'recipient' : 'sender';
};
export function releasePacking(deal,state,role) {
  otherRole(role);
  if (!canContinue(deal,state,role) || state.shipped[role]) return state;
  return {...state,ready:{...state.ready,[role]:true}};
}
export function targetAddress(deal,state,role) {
  const owner = otherRole(role);
  return canContinue(deal,state,role) && state.ready[role] && deal.participants[owner].addressReleased
    ? deal.participants[owner].address : null;
}
export function chooseMethod(deal,state,role,method) {
  if (!targetAddress(deal,state,role) || state.shipped[role] || ![null,'brief'].includes(method)) return state;
  return {...state,method:{...state.method,[role]:method}};
}
export function confirmShipment(deal,state,role) {
  if (!targetAddress(deal,state,role) || state.method[role] !== 'brief' || state.shipped[role]) return state;
  return {...state,shipped:{...state.shipped,[role]:true}};
}
export function reopenPacking(state,role) {
  otherRole(role);
  if (state.status !== 'packing' || state.shipped[role]) return state;
  return {...state,ready:{...state.ready,[role]:false},method:{...state.method,[role]:null}};
}
export function shippingPhase(state,role) {
  const other = otherRole(role);
  if (state.status !== 'packing') return state.status;
  if (state.shipped[role] && state.shipped[other]) return 'BOTH_SHIPPED';
  if (state.shipped[role]) return 'SHIPPED_BY_ME';
  if (state.shipped[other]) return 'SHIPPED_BY_PARTNER';
  return state.ready[role] ? 'READY_TO_SHIP' : 'PACKING';
}
export function operationalSlots(state,role) {
  otherRole(role);
  // Exactly two other demo obligations per direction; never an engine/request count.
  const occupied = state.status === 'pending' || (state.status === 'packing' && !state.shipped[role]);
  return {outgoing:2 + Number(role === 'sender' && occupied),incoming:2 + Number(role === 'recipient' && occupied),ownSlotOccupied:occupied};
}
