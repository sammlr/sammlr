import {renderReceive, renderGive} from './pax.js';
import {DAY, createDeal, perspective, pieces, initialState, refresh, transition, missing, togglePiece, canContinue, validState} from './lifecycle.js';

import {otherRole, releasePacking, targetAddress, chooseMethod, confirmShipment, reopenPacking, shippingPhase, operationalSlots} from './shipping.js';

export function startJourney(candidate) {
  const deal = createDeal(candidate);
  const signature = JSON.stringify(deal);
  const storageKey = `sammlr-pax-06:${deal.id}`;
  let state = initialState(), role = 'sender', offset = 0, screen = 'board', shippingView = 'address';
  const $ = id => document.getElementById(id);
  const now = () => Date.now() + offset;
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey));
    if (saved?.signature === signature && validState(deal, saved.state) && ['sender','recipient'].includes(saved.role)
      && Number.isFinite(saved.offset) && saved.offset >= 0) {
      state = saved.state;role = saved.role;offset = saved.offset;
    }
  } catch { $('pax-storage-note').hidden = false; }
  function save() {
    try {sessionStorage.setItem(storageKey, JSON.stringify({signature,state,role,offset}));}
    catch {$('pax-storage-note').hidden = false;}
    const slots = operationalSlots(state,role);
    $('pax-shipping-dev').textContent = `Request-State: ${state.status === 'packing' ? 'accepted' : state.status}
Trade-State: ${shippingPhase(state,role)}
My packing complete: ${canContinue(deal,state,role)}
Partner packing complete: ${canContinue(deal,state,otherRole(role))}
My pack released: ${state.ready[role]}
My shipped: ${state.shipped[role]}
Partner shipped: ${state.shipped[otherRole(role)]}
Outgoing operational slots: ${slots.outgoing} / 3
Incoming operational slots: ${slots.incoming} / 3
Own slot occupied: ${slots.ownSlotOccupied}
Demo-Basis: je zwei weitere operative Vorgänge.`;
    $('pax-demo-state').textContent = `Rolle: ${perspective(deal,role).name} · Demo: ${state.status === 'packing' ? 'ACTIVE / '+shippingPhase(state,role) : state.status}`;
  }
  const boardScreen = document.querySelector('section[data-screen="board"]');
  const board = boardScreen.querySelector('.pax-board');
  const receive = board.querySelector('.pax-receive');
  const give = board.querySelector('.pax-give');
  const title = boardScreen.querySelector('h1');
  const subtitle = title.nextElementSibling;
  const primary = $('pax-request');
  const decline = document.createElement('button');decline.type = 'button';decline.className = 'pj-simulation';decline.id = 'pax-decline';decline.textContent = 'Ablehnen';primary.after(decline);
  const progress = document.createElement('p');progress.id = 'pax-progress';progress.className = 'pax-progress';progress.setAttribute('role','status');progress.setAttribute('aria-live','polite');
  const incomplete = document.createElement('button');incomplete.type = 'button';incomplete.id = 'pax-incomplete';incomplete.className = 'pj-simulation';incomplete.textContent = 'Es fehlen Sticker / trotzdem weiter';primary.after(incomplete);
  const secondary = document.createElement('details');secondary.className = 'pax-secondary-receive';
  const summary = document.createElement('summary');summary.textContent = 'DU BEKOMMST · Sticker ansehen';secondary.append(summary);
  function show(next, focus = true) {
    screen = next;document.body.dataset.screen = next;
    document.querySelectorAll('section[data-screen]').forEach(e => {e.hidden = e.dataset.screen !== next;});
    if (focus) {window.scrollTo(0,0);document.querySelector(`section[data-screen="${next}"] h1`)?.focus({preventScroll:true});}
  }
  function updateProgress() {
    const remaining = missing(deal,state,role).length;
    const total = pieces(deal,role).length;
    progress.textContent = remaining ? `${total-remaining} / ${total} eingepackt` : `${total} / ${total} eingepackt · Alle Sticker eingepackt ✓`;
    primary.disabled = remaining !== 0;
    incomplete.hidden = remaining === 0;
  }
  function packButtons() {
    give.querySelectorAll('.pending-review-row').forEach((row,index) => {
      const item = pieces(deal,role).find(p => p.key === row.dataset.itemKey);
      const label = row.firstElementChild;
      const button = document.createElement('button');button.type = 'button';button.className = 'pax-pack-item';
      button.dataset.itemKey = item.key;
      button.setAttribute('aria-label', `${item.album}, ${item.code}, Exemplar ${item.instance}, eingepackt`);
      button.setAttribute('aria-pressed', String(state.packed[role].includes(item.key)));
      const marker = document.createElement('img');marker.className = 'pax-pack-mark';marker.alt = '';marker.setAttribute('aria-hidden','true');
      marker.src = `/static/ceoklaue-markers/give_cross/give_cross_0${index % 5 + 1}.svg`;
      button.append(label,marker);row.append(button);
      button.addEventListener('click', () => {
        state = togglePiece(deal,state,role,item.key);
        button.setAttribute('aria-pressed', String(state.packed[role].includes(item.key)));
        updateProgress();save();
      });
    });
  }
  function render() {
    state = refresh(state,now());save();
    const view = perspective(deal,role);
    const packing = state.status === 'packing';
    document.querySelectorAll('[data-pax-address]').forEach(e=>e.textContent='');
    if (packing && state.shipped[role]) {
      $('pax-shipped-copy').textContent = 'Deine Sticker sind unterwegs zu '+view.partner+'.';
      $('pax-partner-package').textContent = 'PAKET VON '+view.partner.toUpperCase();
      $('pax-partner-shipping').textContent = state.shipped[otherRole(role)] ? 'Unterwegs' : 'Wartet auf Versand';
      show('shipped');return;
    }
    if (packing && state.ready[role]) {
      const address = targetAddress(deal,state,role);
      if (address) {
        document.querySelectorAll('[data-pax-address]').forEach(e=>e.textContent=address.join('\n'));
        $('pax-shipping-method').value = state.method[role] || '';
        $('pax-confirm-shipment').disabled = state.method[role] !== 'brief';
        show(shippingView);return;
      }
    }
    document.body.classList.toggle('pax-packing',packing);
    if (['expired','withdrawn','declined'].includes(state.status)) {
      $('pax-terminal-title').textContent = {expired:'Anfrage abgelaufen.',withdrawn:'Anfrage zurückgezogen.',declined:'Pax abgelehnt.'}[state.status];
      $('pax-terminal-copy').textContent = state.status === 'expired' ? 'Die 24 Stunden sind vorbei. Der operative Slot wäre wieder frei.' : 'Diese Anfrage ist beendet. Der operative Slot wäre wieder frei.';
      show('terminal');return;
    }
    if (state.status === 'pending' && role === 'sender') {
      $('pax-wait-copy').textContent = `${deal.partner} hat jetzt Zeit, sich den Tausch anzusehen.`;
      $('pax-wait-counts').textContent = `${deal.receive_count} für dich · ${deal.give_count} für ${deal.partner} · ${deal.album_count} Alben`;
      updateTime();show('waiting');return;
    }
    if (state.status === 'discovery' && role === 'recipient') {
      $('pax-terminal-title').textContent = 'Noch keine Anfrage.';
      $('pax-terminal-copy').textContent = 'Valentin hat diesen Pax noch nicht angefragt.';show('terminal');return;
    }
    $('pax-receive-albums').replaceChildren();$('pax-give-albums').replaceChildren();
    renderReceive(view.receive);renderGive(view.give);
    title.textContent = packing ? 'Dein Paket für '+view.partner+'.' : role === 'recipient' ? 'Valentin möchte mit dir tauschen.' : `Mit ${deal.partner} tauschen.`;
    subtitle.textContent = packing ? (state.shipped[otherRole(role)] ? `Das Paket von ${view.partner} ist unterwegs. Jetzt kannst du deine Sticker packen.` : 'Dieser Pax wurde angenommen. Jetzt kannst du deine Sticker packen.') : `${view.receive.reduce((n,a)=>n+a.items.length,0)} für dich. ${view.give.reduce((n,a)=>n+a.items.length,0)} für ${view.partner}.`;
    give.querySelector('h2').textContent = packing ? 'DEIN PAKET · WAS DU VERSCHICKST' : 'DU GIBST AB';
    if (packing) {
      secondary.open = false;secondary.append(receive);board.replaceChildren(give,progress,secondary);
      packButtons();primary.textContent = 'Packen abschließen →';updateProgress();
    } else {
      board.replaceChildren(receive,give);primary.disabled = false;incomplete.hidden = true;
      primary.textContent = role === 'recipient' ? 'Pax annehmen →' : 'Pax anfragen →';
    }
    decline.hidden = state.status !== 'pending' || role !== 'recipient';
    document.fonts.ready.then(() => give.querySelectorAll('h3').forEach(h => {h.nextElementSibling.style.width = `${Math.ceil(h.getBoundingClientRect().width+6)}px`;}));
    show('board');
  }
  function updateTime() {
    const minutes = Math.max(0, Math.ceil((state.bindingCreatedAt + DAY - now()) / 60000));
    $('pax-time').textContent = `Noch ${Math.floor(minutes/60)} Std. ${minutes%60} Min.`;
  }
  function act(action) {state = transition(state,action,role,now());render();}
  function reviewMissing() {
    if (state.status !== 'packing') return;
    const open = missing(deal,state,role);
    if (!open.length) {finish();return;}
    $('pax-missing-title').textContent = `Dir fehlen noch ${open.length} Sticker in deiner Packliste.`;
    $('pax-missing-list').replaceChildren(...open.map(item => {const li = document.createElement('li');li.textContent = `${item.album} · ${item.code} · Exemplar ${item.instance}`;li.dataset.itemKey = item.key;return li;}));
    show('missing');
  }
  function finish() {
    if (!canContinue(deal,state,role)) {reviewMissing();return;}
    state = releasePacking(deal,state,role);shippingView = 'address';render();
  }
  $('pax-prepare-shipping').addEventListener('click',()=>{shippingView='shipping';render();});
  $('pax-reopen-pack').addEventListener('click',()=>{state=reopenPacking(state,role);render();});
  $('pax-shipping-method').addEventListener('change',()=>{
    state=chooseMethod(deal,state,role,$('pax-shipping-method').value || null);save();
    $('pax-confirm-shipment').disabled=state.method[role]!=='brief';
  });
  $('pax-portal').addEventListener('click',()=>{shippingView='portal';render();});
  $('pax-portal-back').addEventListener('click',()=>{shippingView='shipping';render();});
  $('pax-confirm-shipment').addEventListener('click',()=>{state=confirmShipment(deal,state,role);render();});
  primary.addEventListener('click', () => state.status === 'packing' ? finish() : act(role === 'sender' ? 'request' : 'accept'));
  decline.addEventListener('click', () => act('decline'));
  $('pax-withdraw').addEventListener('click', () => act('withdraw'));
  incomplete.addEventListener('click',reviewMissing);
  $('pax-return').addEventListener('click',render);
  $('pax-end-back').addEventListener('click',render);
  $('pax-really-missing').addEventListener('click', () => {
    if (state.status !== 'packing' || !missing(deal,state,role).length) return;
    $('pax-end-title').textContent = 'Sticker fehlen wirklich.';
    $('pax-end-copy').textContent = 'Pax anpassen / Partner fragen folgt im nächsten Lifecycle-Schritt. Dein vereinbartes Paket bleibt unverändert.';show('endpoint');
  });
  document.querySelectorAll('[data-role]').forEach(button => button.addEventListener('click', () => {role = button.dataset.role;shippingView='address';render();}));
  function scenario(name) {
    const shippingDemo = ['address','shipping','shipped-me','shipped-partner','both-shipped'].includes(name);
    if (!shippingDemo && !['opened','waiting','received','packing-sender','packing-recipient','partial','complete'].includes(name)) return;
    state = initialState();offset = 0;shippingView='address';role = ['received','packing-recipient'].includes(name) ? 'recipient' : 'sender';
    if (name !== 'opened') state = transition(state,'request','sender',now());
    if (shippingDemo || ['packing-sender','packing-recipient','partial','complete'].includes(name)) state = transition(state,'accept','recipient',now());
    if (name === 'partial' || name === 'complete') {
      const all = pieces(deal,role);state.packed[role] = all.slice(0,name === 'complete' ? all.length : Math.max(0,all.length-2)).map(p=>p.key);
    }
    if (shippingDemo) {
      const completeRole = side => {state.packed[side]=pieces(deal,side).map(p=>p.key);state=releasePacking(deal,state,side);};
      const shipRole = side => {completeRole(side);state=chooseMethod(deal,state,side,'brief');state=confirmShipment(deal,state,side);};
      if (name==='shipped-partner') shipRole('recipient');
      else {completeRole('sender');if (name==='shipping') shippingView='shipping';}
      if (['shipped-me','both-shipped'].includes(name)) shipRole('sender');
      if (name==='both-shipped') shipRole('recipient');
    }
    render();
  }
  $('pax-load-scenario').addEventListener('click', () => scenario($('pax-scenario').value));
  $('pax-advance').addEventListener('click', () => {offset += DAY;render();});
  const url = new URL(location.href);
  if (url.searchParams.has('demo')) {
    const demo = url.searchParams.get('demo');url.searchParams.delete('demo');history.replaceState(null,'',url);scenario(demo);
  }
  render();
  // A live pending view expires even without another click; accepted deals never do.
  setInterval(() => {
    const next = refresh(state,now());
    if (next !== state) {state = next;render();}
    else if (screen === 'waiting') updateTime();
  },1000);
}
