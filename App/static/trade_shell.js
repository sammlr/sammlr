import {expandCards, settleMotion} from './trade_shell_motion.js';

// Production wall measurement, independent of proposal count and open/closed state.
function syncGeometry() {
  const cell = document.querySelector('.trade-wall-measure .wall > div');
  if (cell) document.documentElement.style.setProperty('--trade-card-width', `${cell.getBoundingClientRect().width}px`);
  const group = document.querySelector('.trade-top');
  if (group && !group.hidden) {
    group.style.setProperty('--trade-center-offset', '0px');
    const faces = [...group.querySelectorAll('.slot,.sticker-wall-stack-layer')].map(e => e.getBoundingClientRect());
    if (faces.length) {
      const bounds = group.getBoundingClientRect();
      const center = (Math.min(...faces.map(r => r.left)) + Math.max(...faces.map(r => r.right))) / 2;
      group.style.setProperty('--trade-center-offset', `${(bounds.left + bounds.right) / 2 - center}px`);
    }
  }
}
syncGeometry();
new ResizeObserver(syncGeometry).observe(document.querySelector('main.container'));

function installAlbumMotion(root) {
  root.querySelectorAll('.trade-group summary').forEach(summary => {
    summary.addEventListener('click', event => {
      event.preventDefault();
      settleMotion();
      const details = summary.parentElement;
      const origin = summary.querySelector('.sticker-slot-frame').getBoundingClientRect();
      details.open = !details.open;
      if (details.open) expandCards(origin, [...details.querySelectorAll('.trade-fan .sticker-slot-frame')]);
    });
  });
}
installAlbumMotion(document);
document.querySelector('[data-open-groups]')?.addEventListener('click', () => {
  settleMotion();
  const groups = [...document.querySelectorAll('.trade-group details')].filter(g => !g.open);
  if (!groups.length) return;
  const origin = groups[0].querySelector('.sticker-slot-frame').getBoundingClientRect();
  groups.forEach(group => { group.open = true; });
  expandCards(origin, groups.flatMap(g => [...g.querySelectorAll('.trade-fan .sticker-slot-frame')]));
});
document.querySelector('[data-close-groups]')?.addEventListener('click', () => {
  settleMotion();
  document.querySelectorAll('.trade-group details').forEach(group => { group.open = false; });
});

const group = document.querySelector('.trade-top');
const explorer = document.querySelector('.trade-explorer');
const status = document.querySelector('.trade-explorer-status');
let loading = false;
group?.querySelectorAll('.trade-proposal .slot').forEach(link => {
  link.setAttribute('aria-expanded', 'false');
  link.addEventListener('click', async event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (loading) return;
    loading = true;
    link.setAttribute('aria-busy', 'true');
    status.textContent = '';
    try {
      // Existing authenticated GET route is the only source; no new API or domain data.
      const response = await fetch(link.href, {headers:{Accept:'text/html'}});
      if (!response.ok || response.redirected) throw new Error('unavailable');
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const albums = [...doc.querySelectorAll('.trade-group')];
      if (!albums.length) throw new Error('unavailable');
      settleMotion();
      const origin = link.closest('.sticker-slot-frame').getBoundingClientRect();
      const heading = document.createElement('h2');
      heading.textContent = link.closest('.trade-proposal').querySelector('h2').textContent;
      heading.tabIndex = -1;
      const actions = document.createElement('div');
      actions.className = 'trade-explorer-actions';
      const close = document.createElement('button');
      close.type = 'button'; close.className = 'trade-return'; close.textContent = 'Zurück zu Vorschlägen';
      const deal = document.createElement('a');
      deal.href = link.href; deal.textContent = 'Tausch ansehen';
      actions.append(close, deal);
      explorer.replaceChildren(heading, ...albums, actions);
      group.hidden = true; explorer.hidden = false;
      link.setAttribute('aria-expanded', 'true');
      installAlbumMotion(explorer);
      heading.focus({preventScroll:true});
      expandCards(origin, [...explorer.querySelectorAll('summary .sticker-slot-frame')]);
      close.addEventListener('click', () => {
        settleMotion();
        explorer.hidden = true; group.hidden = false;
        link.setAttribute('aria-expanded', 'false');
        syncGeometry(); link.focus({preventScroll:true});
      });
    } catch {
      status.textContent = 'Der Vorschlag ist gerade nicht verfügbar. Bitte lade die Seite neu.';
    } finally {
      loading = false; link.removeAttribute('aria-busy');
    }
  });
});
