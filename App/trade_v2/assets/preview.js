import {prepareStickerPhysics} from './sticker_physics.js';
import {renderReceive} from './receive.js';
import {dismissed,visibleDeals} from './discovery.js';
import {readState} from './requests.js';
import {completed} from './receipt_state.js';
// Reuse pure display exports. No #pax-data exists, so no lifecycle is loaded.
import {card, renderGive} from '/static/pax/pax.js';
const data = JSON.parse(document.getElementById('trade-data').textContent);
const screen = document.body.dataset.screen;
await prepareStickerPhysics();
const el = (tag, cls, text) => {
  const node = document.createElement(tag);node.className = cls || '';
  if (text !== undefined) node.textContent = text;
  return node;
};
export function sortedPartners(partners, key = 'max_swap', album = '') {
  const allowed = ['max_swap', 'total_duplicates', 'for_me'];
  const field = allowed.includes(key) ? key : 'max_swap';
  return partners.filter(p => !album || p.albums.some(a => a.id === album))
    .slice().sort((a, b) => b[field] - a[field] || a.id - b.id);
}
function partnerRows(partners) {
  const target = document.getElementById('partner-list');target.replaceChildren();
  for (const p of partners) {
    const link = el('a', 'partner-row');link.href = `/trade-v2/partners/${p.slug}`;
    link.dataset.partnerId = p.id;link.dataset.maxSwap = p.max_swap;
    const head = el('div', 'row-head');head.append(el('strong', '', p.display_name), el('span', 'swap', `${p.max_swap} ↔ ${p.max_swap} →`));
    link.append(head, el('p', '', `${p.for_me} für dich · ${p.from_me} von dir`), el('small', '', `${p.albums.length} gemeinsame Alben · ${p.total_duplicates.toLocaleString('de-DE')} Doppelte`));target.append(link);
  }
}
if (screen === 'home') {
  const table = document.getElementById('top-table');
  let local;try{local=readState(sessionStorage);}catch(_){local={requests:{}};}
  let offers=[];try{offers=visibleDeals(data.deals,local,dismissed(sessionStorage));}catch(_){document.getElementById('discovery-error').textContent='Der lokale Vorschlagsstand ist nicht verfügbar.';}
  for (const deal of offers) {
    const offer = el('article', 'top-offer');offer.dataset.deal = deal.id;
    const toggle = el('a', 'top-toggle');toggle.href = `/trade-v2/deals/${deal.partner_slug}`;
    toggle.setAttribute('aria-label', `Tausch mit ${deal.partner}: ${deal.receive_count} gegen ${deal.give_count} Sticker, ${deal.album_count} Alben`);
    const stack = el('span', 'top-stack');stack.append(card(deal.receive.flatMap(a => a.items), true));
    toggle.append(stack, el('span', 'top-name', deal.partner), el('span', 'top-meta', `${deal.receive_count} ↔ ${deal.give_count}`), el('span', 'top-albums', `${deal.album_count} Alben`));
    toggle.addEventListener('keydown', event => {
      if (event.key === ' ') {event.preventDefault();if (!event.repeat) toggle.click();}
    });
    offer.append(toggle);table.append(offer);
  }

  const {renderHistory}=await import('./receipt_history.js');renderHistory(local);
}
if(screen==='active'){const {startOverview}=await import('./overview_view.js');startOverview(data);}
if (screen === 'partners') {
  const sort = document.getElementById('sort'), album = document.getElementById('album');
  const update = () => {const partners = sortedPartners(data.partners, sort.value, album.value);partnerRows(partners);document.getElementById('result-count').textContent = `${partners.length} Sammler`;};
  sort.addEventListener('change', update);album.addEventListener('change', update);update();
}
if (screen === 'deal') {
  const {startSender} = await import('./sender.js');
  const snapshot = startSender(data, screen) || data.deal;
  renderReceive(snapshot.receive);renderGive(snapshot.give);
  const {proposalDismiss}=await import('./proposal_dismiss.js');proposalDismiss(data.deal);
  if (snapshot.receive_count!==data.deal.receive_count || snapshot.give_count!==data.deal.give_count) {
    const summary=document.querySelector('.deal-summary'),albums=document.createElement('span');
    albums.textContent=`· ${snapshot.album_count} Alben`;summary.replaceChildren(`${snapshot.receive_count} ↔ ${snapshot.give_count} `,albums);
  }
}
if (screen === 'waiting') {
  const {startRequestView} = await import('./request_view.js');startRequestView(data, screen);
}
if (screen === 'next') {
  const {startPacking} = await import('./packing_view.js');startPacking(data);
}
if (screen === 'amendment') {
  const {startAmendment} = await import('./amendment_view.js');startAmendment(data);
}
if (screen === 'shipping') {
  const {startShipping} = await import('./shipping_view.js');startShipping(data);
}
if(screen==='manual-review'){const {startManualReview}=await import('./manual_review.js');startManualReview(data);}
if(screen==='receipt'){const {startReceipt}=await import('./receipt_view.js');startReceipt(data);}
if(['waiting','next','shipping','amendment'].includes(screen)){const {receiptLink}=await import('./receipt_history.js');receiptLink(data.deal);}
document.body.dataset.ready = 'true';
