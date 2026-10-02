import {validReceipt} from './receipt_state.js';
import {validShipping} from './shipping_state.js';
import {freezeSnapshot, validVersions} from './deal_versions.js';
export {freezeSnapshot} from './deal_versions.js';
// Isolated single-tab demo model; no production commands, reservations or DB.
export const DAY = 24 * 60 * 60 * 1000;
export const STORAGE_KEY = 'sammlr-trade-02';
export function initialState(count = 0, now = Date.now()) {
  const requests = {};
  for (let i = 0; i < count; i++) requests[`seed-${i}`] = {
    id: `seed-${i}`, origin: ['MANUAL', 'SMARTDEAL', 'TOP_SUGGESTION'][i],
    direction: 'outgoing', status: 'pending', ownShipped: false,
    bindingCreatedAt: now, expiresAt: now + DAY, snapshot: null,
  };
  return {version: 1, requests};
}
export function expire(state, now) {
  for (const request of Object.values(state.requests)) {
    if (request.status === 'pending' && now >= request.expiresAt) request.status = 'expired';
  }
  return state;
}
export function slots(state, direction = 'outgoing', now = Date.now()) {
  return Object.values(state.requests).filter(r => r.direction === direction && !r.ownShipped &&
    (r.status === 'accepted' || (r.status === 'pending' && now < r.expiresAt))).length;
}
export function send(state, deal, now) {
  expire(state, now);
  // One fixture opportunity has one sender command in this demo session.
  // This is not a production cross-origin identity or lifetime uniqueness rule.
  if (state.requests[deal.id]) return {status: 'existing', request: state.requests[deal.id]};
  if (slots(state, 'outgoing', now) >= 3) return {status: 'full'};
  const request = {id: deal.id, origin: deal.origin, direction: 'outgoing',
    status: 'pending', ownShipped: false, deal_version: 1, bindingCreatedAt: now, expiresAt: now + DAY,
    snapshot: freezeSnapshot(JSON.parse(JSON.stringify(deal)))};
  state.requests[deal.id] = request;
  return {status: 'sent', request};
}
export function readState(storage) {
  const raw = storage.getItem(STORAGE_KEY);
  if (!raw) return initialState();
  const state = JSON.parse(raw);
  if (state.version !== 1 || !state.requests || Array.isArray(state.requests)) throw Error('Invalid demo state');
  for (const [key, r] of Object.entries(state.requests)) {
    if (!r || key !== r.id || !['pending', 'expired', 'accepted', 'declined', 'cancelled'].includes(r.status) ||
        !['outgoing', 'incoming'].includes(r.direction) || typeof r.ownShipped !== 'boolean' ||
        !['MANUAL', 'SMARTDEAL', 'TOP_SUGGESTION'].includes(r.origin) ||
        !Number.isFinite(r.bindingCreatedAt) || r.expiresAt !== r.bindingCreatedAt + DAY ||
        (!key.startsWith('seed-') && (!r.snapshot || r.snapshot.id !== key))) throw Error('Invalid demo request');
  }
  for (const r of Object.values(state.requests)) if (r.snapshot) {
    if (!validVersions(r) || !validShipping(r) || !validReceipt(r)) throw Error('Invalid deal version');
    freezeSnapshot(r.snapshot);freezeSnapshot(r.dealVersions);freezeSnapshot(r.positionOrder);freezeSnapshot(r.amendment?.proposal);
  }
  return state;
}
export function saveState(storage, state) {storage.setItem(STORAGE_KEY, JSON.stringify(state));}

// Snapshot is fixed already at request creation, not recomputed on acceptance.
export function perspective(request, role) {
  if (!request?.snapshot || !['sender', 'recipient'].includes(role)) return null;
  const snapshot = request.snapshot;
  return {
    requestId: request.id, side_a: 'Valentin', side_b: snapshot.partner,
    me: role === 'sender' ? 'Valentin' : snapshot.partner,
    partner: role === 'sender' ? snapshot.partner : 'Valentin',
    receive: role === 'sender' ? snapshot.receive : snapshot.give,
    give: role === 'sender' ? snapshot.give : snapshot.receive,
    receive_count: role === 'sender' ? snapshot.receive_count : snapshot.give_count,
    give_count: role === 'sender' ? snapshot.give_count : snapshot.receive_count,
    album_count: snapshot.album_count,
  };
}
export function decide(state, id, role, action, now) {
  expire(state, now);
  const request = state.requests[id];
  if (!request?.snapshot || role !== 'recipient' || !['accept', 'decline'].includes(action)) return 'forbidden';
  if (request.status !== 'pending') return request.status;
  request.status = action === 'accept' ? 'accepted' : 'declined';
  request.decidedAt = now;
  return request.status;
}
export function incomingSlots(state, partnerId, now = Date.now()) {
  return Object.values(state.requests).filter(r => r.snapshot?.partner_id === partnerId && !r.recipientShipped &&
    (r.status === 'accepted' || (r.status === 'pending' && now < r.expiresAt))).length;
}
