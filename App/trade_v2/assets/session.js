// Explicit DEV entry points reset only this tab's existing isolated demo store.
import {DAY, initialState, send, decide, expire, readState, saveState} from './requests.js';
export function loadSession(deal) {
  const query = new URL(location.href);
  const demo = query.searchParams.get('demo');
  const scenario = query.searchParams.get('scenario');
  let state;
  if (['open', 'accepted', 'declined', 'expired'].includes(scenario)) {
    const now = Date.now();
    const created = scenario === 'expired' ? now - DAY : now;
    state = initialState(2, now);
    send(state, deal, created);
    if (scenario === 'accepted' || scenario === 'declined') decide(state, deal.id, 'recipient', scenario === 'accepted' ? 'accept' : 'decline', now);
    expire(state, now);
    saveState(sessionStorage, state);query.searchParams.delete('scenario');
  } else if (['0', '2', '3', 'sent'].includes(demo)) {
    state = initialState(demo === 'sent' ? 0 : Number(demo));
    if (demo === 'sent') send(state, deal, Date.now());
    saveState(sessionStorage, state);
  } else state = readState(sessionStorage);
  if (query.searchParams.has('demo')) query.searchParams.delete('demo');
  if (query.href !== location.href) history.replaceState(null, '', query);
  return state;
}
