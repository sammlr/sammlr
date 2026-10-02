import {completed} from './receipt_state.js';
import {receiptLink} from './receipt_history.js';
import {ownShipped,bothShipped,fullyPacked} from './shipping_state.js';
import {renderGive} from '/static/pax/pax.js';
import {renderReceive} from './receive.js';
import {loadSession} from './session.js';
import {initialState, expire, slots, incomingSlots, decide, perspective, readState, saveState} from './requests.js';

export function startRequestView(data, screen) {
  const fallback = data.deal;
  const params = new URL(location.href).searchParams;
  const role = params.get('role') === 'recipient' ? 'recipient' : 'sender';
  const showDeal = params.get('view') === 'deal';
  const base = `/trade-v2/requests/${fallback.partner_slug}`;
  const statusURL = `${base}?role=${role}`;
  const byId = id => document.getElementById(id);
  const setText = (id, text) => {const node = byId(id);if (node.textContent !== text) node.textContent = text;};
  const note = byId('capacity-note');
  const actions = byId('decision-actions');
  let state, busy = false, renderedSnapshot = null;
  function fail() {
    note.textContent = 'Demo-Speicher nicht verfügbar oder ungültig. Bitte Sitzungsspeicherung erlauben oder die lokale Demo zurücksetzen.';
    actions.hidden = true;byId('next-step').hidden = true;byId('view-request-deal').hidden = true;
  }
  try {state = loadSession(fallback);} catch (_) {fail();return;}
  const senderLink = byId('role-sender'), recipientLink = byId('role-recipient');
  senderLink.href = `${base}?role=sender`;recipientLink.href = `${base}?role=recipient`;
  (role === 'sender' ? senderLink : recipientLink).setAttribute('aria-current', 'page');
  byId('view-request-deal').href = `${base}?role=${role}&view=deal`;
  byId('next-step').href = `${base}/next?role=${role}`;
  byId('request-preview').addEventListener('click', () => location.assign(statusURL));
  function renderDeal(view) {
    const identity=JSON.stringify([view.requestId,view.give,view.receive]);
    if (renderedSnapshot === identity) return;
    byId('request-deal').innerHTML = '<div class="pax-board"><section class="pax-receive s30-album-page"><h2>Du bekommst</h2><div id="pax-receive-albums"></div></section><section class="pax-give sticker-list-page"><h2>Du gibst ab</h2><div id="pax-give-albums"></div></section></div>';
    renderReceive(view.receive);renderGive(view.give);renderedSnapshot = identity;
  }
  function update() {
    try {
      state = readState(sessionStorage);
      const before = JSON.stringify(state);expire(state, Date.now());
      if (JSON.stringify(state) !== before) saveState(sessionStorage, state);
      const request = state.requests[fallback.id];
      const view = perspective(request, role);
      document.body.dataset.requestState = request?.status || 'absent';
      document.body.dataset.role = role;
      document.body.dataset.requestId = request?.id || '';
      setText('capacity-count', role === 'sender' ? `${slots(state)}/3 ausgehend belegt` : `${incomingSlots(state, request?.snapshot?.partner_id)}/3 eingehend belegt`);
      note.textContent = '';
      setText('request-clock', '');setText('request-deadline', '');
      actions.hidden = true;byId('next-step').hidden = true;byId('request-preview').hidden = true;
      byId('view-request-deal').hidden = !view || showDeal || screen === 'next';
      if (!view) {
        setText('waiting-title', 'Noch keine Anfrage gesendet');
        setText('request-status', 'Öffne den vorgeschlagenen Deal, um eine Anfrage zu senden.');
        setText('request-summary', '');
        byId('view-request-deal').hidden = false;byId('view-request-deal').href = `/trade-v2/partners/${fallback.profile_slug||fallback.partner_slug}/smartdeal`;
        return;
      }
      // Read only the sent snapshot. Role changes never reconstruct it from fixtures.
      const summary = `${view.receive_count} ↔ ${view.give_count} · ${view.album_count} Alben`;
      if (byId('request-summary').textContent !== summary) {
        const albums = document.createElement('span');albums.textContent = `· ${view.album_count} Alben`;
        byId('request-summary').replaceChildren(`${view.receive_count} ↔ ${view.give_count} `, albums);
      }
      setText('role-recipient', view.side_b);
      setText('request-eyebrow', role === 'recipient' ? 'Tauschanfrage' : 'Deine Anfrage');
      const pendingRecipient = request.status === 'pending' && role === 'recipient';
      const needsDeal = screen !== 'next' && (pendingRecipient || showDeal);
      if (needsDeal) renderDeal(view);
      else {byId('request-deal').replaceChildren();renderedSnapshot = null;}
      if (screen === 'next') {
        setText('waiting-title', request.status === 'accepted' ? 'Der Tausch steht' : 'Noch kein aktiver Tausch');
        setText('request-status', request.status === 'accepted' ? 'Packphase folgt im nächsten Trade-Schritt.' : 'Dieser Schritt ist erst nach Annahme verfügbar.');
        byId('request-preview').hidden = false;return;
      }
      if (request.status === 'pending') {
        setText('waiting-title', role === 'sender' ? `Anfrage an ${view.partner} gesendet` : 'Valentin möchte mit dir tauschen.');
        setText('request-status', role === 'sender' ? `Wartet auf ${view.partner}` : 'Prüfe den vorgeschlagenen Tausch.');
        const minutes = Math.ceil(Math.max(0, request.expiresAt-Date.now())/60000);
        setText('request-clock', `${Math.floor(minutes/60)} Std. ${minutes%60} Min. verbleibend · 24 Stunden ab Senden`);
        setText('request-deadline', `Fristende: ${new Date(request.expiresAt).toLocaleString('de-DE')}`);
        actions.hidden = !pendingRecipient;byId('view-request-deal').hidden ||= pendingRecipient;
      } else if (request.status === 'accepted') {
        receiptLink(fallback);
        setText('waiting-title', role === 'sender' ? `${view.partner} hat angenommen ✓` : 'Tausch steht ✓');
        setText('request-status', `Du und ${view.partner} tauscht ${view.receive_count} ↔ ${view.give_count} Sticker. Nächster Schritt: Sticker packen.`);
        byId('next-step').hidden = false;
        const amendmentPending=request.amendment?.status==='pending';
        byId('next-step').href=`${base}/${amendmentPending?'amendment':'next'}?role=${role}`;
        byId('next-step').textContent=amendmentPending?'Änderung ansehen →':'Zum Packen →';
        if (amendmentPending) setText('request-status', 'Eine Änderung wartet auf Zustimmung. Das bisherige Paket bleibt bis zur Entscheidung vereinbart.');
        if (!amendmentPending && (ownShipped(request,role) || fullyPacked(request,role))) {
          byId('next-step').href=`${base}/shipping?role=${role}`;byId('next-step').textContent=ownShipped(request,role)?'Versandstatus ansehen →':'Adresse und Versand →';
        }
        if (bothShipped(request)) {setText('waiting-title','Beide Sendungen sind unterwegs ✓');setText('request-status','Der Tausch bleibt aktiv. Er ist noch nicht abgeschlossen.');}
        else if (ownShipped(request,role)) {setText('waiting-title','Deine Sticker sind unterwegs ✓');setText('request-status',`${view.partner} hat noch nicht versendet.`);}
        else if (ownShipped(request,role==='sender'?'recipient':'sender')) setText('request-status',`${view.partner}s Sticker sind unterwegs zu dir. Du musst dein Paket noch auf den Weg bringen.`);
        if(completed(request)){setText('waiting-title','Tausch abgeschlossen ✓');setText('request-status','Beide Empfangsrichtungen sind abgeschlossen.');byId('next-step').href=`${base}/receipt?role=${role}`;byId('next-step').textContent='Abschluss und Bewertung →';}
      } else if (request.status === 'cancelled') {
        setText('waiting-title', 'Der Tausch wurde beendet.');
        setText('request-status', 'Die vorgeschlagene Änderung wurde nicht angenommen. Dieser Tausch wird nicht fortgesetzt.');
        byId('request-deal').replaceChildren();byId('view-request-deal').hidden=true;
      } else if (request.status === 'declined') {
        setText('waiting-title', 'Tauschanfrage abgelehnt');
        setText('request-status', role === 'sender' ? `${view.partner} hat die Tauschanfrage abgelehnt.` : 'Du hast die Tauschanfrage abgelehnt.');
      } else {
        setText('waiting-title', 'Tauschanfrage abgelaufen');
        setText('request-status', role === 'sender' ? 'Die 24-Stunden-Frist ist abgelaufen. Der ausgehende Platz ist wieder frei.' : 'Die 24-Stunden-Frist ist abgelaufen. Du kannst diese Anfrage nicht mehr annehmen oder ablehnen.');
      }
      byId('request-preview').hidden = !showDeal;
    } catch (_) {fail();}
  }
  for (const [id, action] of [['accept-request', 'accept'], ['decline-request', 'decline']]) {
    byId(id).addEventListener('click', () => {
      if (busy) return;
      busy = true;
      try {
        state = readState(sessionStorage);
        decide(state, fallback.id, role, action, Date.now());
        saveState(sessionStorage, state);update();
        byId('waiting-title').focus();
      } catch (_) {fail();}
      finally {busy = false;}
    });
  }
  byId('demo-reset').addEventListener('click', () => {
    try {saveState(sessionStorage, initialState(Number(byId('demo-count').value)));location.assign(`/trade-v2/partners/${fallback.profile_slug||fallback.partner_slug}/smartdeal`);} catch (_) {fail();}
  });
  update();const timer = setInterval(update, 1000);
  window.addEventListener('pagehide', () => clearInterval(timer), {once:true});
}
