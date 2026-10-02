/* PAX-05 browser-only demo model. No production services, requests or slots. */
export const DAY = 24 * 60 * 60 * 1000;
const roles = ['sender', 'recipient'];
const requireRole = role => {if (!roles.includes(role)) throw new Error('Unknown demo role');};
export function createDeal(candidate) {
  const snapshot = structuredClone(candidate);
  // Explicitly fictional owner-released contacts, scoped to this demo deal only.
  snapshot.participants = {
    sender: {addressReleased: true, address: ['Valentin Beispiel (Demo)', 'Beispielweg 12', '12345 Musterstadt']},
    recipient: {addressReleased: true, address: [candidate.partner + ' Beispiel (Demo)', 'Musterstraße 89', '29693 Hodenhagen']}
  };
  const freeze = value => {Object.values(value).forEach(v => {if (v && typeof v === 'object') freeze(v);});return Object.freeze(value);};
  return freeze(snapshot);
}
export function perspective(deal, role) {
  requireRole(role);
  return role === 'sender'
    ? {name: 'Valentin', partner: deal.partner, receive: deal.receive, give: deal.give}
    : {name: deal.partner, partner: 'Valentin', receive: deal.give, give: deal.receive};
}
export function pieces(deal, role) {
  return perspective(deal, role).give.flatMap(a => a.items.map(item => ({...item, album: a.title})));
}
export function initialState() {
  return {status: 'discovery', bindingCreatedAt: null, acceptedAt: null, packed: {sender: [], recipient: []}, ready: {sender:false, recipient:false}, shipped: {sender:false, recipient:false}, method: {sender:null, recipient:null}};
}
export function refresh(state, now) {
  if (state.status === 'pending' && now >= state.bindingCreatedAt + DAY) return {...state, status: 'expired'};
  return state;
}
export function transition(state, action, role, now) {
  requireRole(role);
  state = refresh(state, now);
  if (action === 'request' && role === 'sender' && state.status === 'discovery')
    return {...state, status: 'pending', bindingCreatedAt: now};
  if (state.status !== 'pending') return state;
  if (action === 'accept' && role === 'recipient') return {...state, status: 'packing', acceptedAt: now};
  if (action === 'decline' && role === 'recipient') return {...state, status: 'declined'};
  if (action === 'withdraw' && role === 'sender') return {...state, status: 'withdrawn'};
  return state;
}
export function missing(deal, state, role) {
  requireRole(role);
  return pieces(deal, role).filter(item => !state.packed[role].includes(item.key));
}
export function togglePiece(deal, state, role, key) {
  requireRole(role);
  if (state.status !== 'packing' || state.shipped[role] || !pieces(deal, role).some(item => item.key === key)) return state;
  const checked = state.packed[role];
  return {...state, ready: {...state.ready, [role]:false}, method: {...state.method, [role]:null}, packed: {...state.packed, [role]: checked.includes(key) ? checked.filter(k => k !== key) : [...checked, key]}};
}
export function canContinue(deal, state, role) {
  return state.status === 'packing' && missing(deal, state, role).length === 0;
}
export function validState(deal, state) {
  if (!state || !['discovery','pending','packing','expired','declined','withdrawn'].includes(state.status)) return false;
  if (state.status === 'discovery' ? state.bindingCreatedAt !== null : !Number.isFinite(state.bindingCreatedAt)) return false;
  if (state.status === 'packing') {
    if (!Number.isFinite(state.acceptedAt) || state.acceptedAt < state.bindingCreatedAt || state.acceptedAt >= state.bindingCreatedAt + DAY) return false;
  } else if (state.acceptedAt !== null) return false;
  if (!roles.every(role => typeof state.ready?.[role] === 'boolean' && typeof state.shipped?.[role] === 'boolean'
    && [null,'brief'].includes(state.method?.[role]))) return false;
  if (!roles.every(role => Array.isArray(state.packed?.[role]))) return false;
  if (!roles.every(role => (!state.ready[role] || (state.status === 'packing' && missing(deal,state,role).length === 0))
    && (!state.shipped[role] || (state.ready[role] && state.method[role] === 'brief'))
    && (state.method[role] === null || state.ready[role]))) return false;
  return roles.every(role => Array.isArray(state.packed?.[role]) && new Set(state.packed[role]).size === state.packed[role].length
    && state.packed[role].every(key => state.status === 'packing' && pieces(deal, role).some(p => p.key === key)));
}
