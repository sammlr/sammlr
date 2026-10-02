import {loadSession} from './session.js';
import {initialState, expire, slots, send, readState, saveState} from './requests.js';

export function startSender(data, screen) {
  const deal = data.deal;
  const note = document.getElementById('capacity-note');
  const sendButton = document.getElementById('request-preview');
  const waitingURL = `/trade-v2/requests/${deal.partner_slug}`;
  let state;
  let submitting = false;
  try {
    state = loadSession(deal);
  } catch (_) {
    note.textContent = 'Demo-Speicher nicht verfügbar oder ungültig. Bitte die lokale Demo zurücksetzen bzw. Sitzungsspeicherung erlauben.';
    if (sendButton) sendButton.disabled = true;
    return;
  }
  if (state.requests[deal.id]?.status==='cancelled') {location.replace(waitingURL);return state.requests[deal.id].snapshot;}
  function update() {
    try {
      const before = JSON.stringify(state);expire(state, Date.now());
      if (JSON.stringify(state) !== before) saveState(sessionStorage, state);
      const count = slots(state);
      document.getElementById('capacity-count').textContent = `${count}/3 ausgehend belegt`;
      const existing = state.requests[deal.id];
      note.textContent = count >= 3 ? 'Deine 3 ausgehenden Plätze sind belegt. Ein Platz muss zuerst frei werden, etwa durch Ablehnung, Ablauf oder deinen bestätigten Versand nach Annahme.' : '';
      sendButton.disabled = !existing && count >= 3;
      sendButton.textContent = existing ? 'Zum Anfragestatus' : 'Tauschanfrage senden';
    } catch (_) {
      note.textContent = 'Der Demo-Zustand konnte nicht gespeichert werden. Es wurde keine neue Anfrage gesendet.';
      if (sendButton) sendButton.disabled = true;
    }
  }
  if (sendButton) sendButton.addEventListener('click', () => {
    if (submitting) return;
    submitting = true;
    sendButton.disabled = true;
    try {
      // Re-read before each command. Synchronous sessionStorage makes same-tab retries atomic.
      state = readState(sessionStorage);
      const result = send(state, deal, Date.now());
      saveState(sessionStorage, state);
      if (result.status !== 'full') location.assign(waitingURL);
      else {submitting = false;update();}
    } catch (_) {
      note.textContent = 'Die Anfrage konnte nicht lokal gespeichert werden. Bitte Sitzungsspeicherung erlauben.';
    }
  });
  update();
  const timer = setInterval(update, 1000);
  window.addEventListener('pagehide', () => clearInterval(timer), {once: true});
  document.getElementById('demo-reset').addEventListener('click', () => {
    saveState(sessionStorage, initialState(Number(document.getElementById('demo-count').value)));
    location.assign(`/trade-v2/partners/${deal.profile_slug||deal.partner_slug}/smartdeal`);
  });
  return state.requests[deal.id]?.snapshot || deal;
}
