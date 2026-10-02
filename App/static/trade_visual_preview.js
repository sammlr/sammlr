'use strict';
document.querySelectorAll('.pax').forEach(pax => {
  const opener = pax.querySelector('.pack');
  const panel = document.getElementById(opener.getAttribute('aria-controls'));
  function expand(open) {
    opener.setAttribute('aria-expanded', String(open));
    panel.hidden = !open;
    pax.classList.toggle('is-open', open);
    if (!pax.dataset.state) pax.querySelector('.pack-invitation').textContent = open ? 'Schließen −' : 'Öffnen ↗';
  }
  opener.addEventListener('click', () => expand(opener.getAttribute('aria-expanded') !== 'true'));
  pax.querySelector('.close-pack').addEventListener('click', () => { expand(false); opener.focus(); });
  pax.querySelector('.request-preview').addEventListener('click', event => {
    pax.querySelector('.request-result').hidden = false;
    event.currentTarget.hidden = true;
    pax.dataset.state = 'requested';
    pax.querySelector('.pack-invitation').textContent = 'Angefragt ✓';
  });
  pax.querySelector('.mutual-preview').addEventListener('click', () => {
    pax.querySelector('.request-result').hidden = true;
    pax.querySelector('.mutual-result').hidden = false;
    pax.dataset.state = 'matched';
    pax.querySelector('.pack-invitation').textContent = 'Tausch steht!';
  });
});
const about = document.querySelector('.about');
if (about) about.addEventListener('click', () => {
  const open = about.getAttribute('aria-expanded') !== 'true';
  about.setAttribute('aria-expanded', String(open));
  document.querySelector('#pax-explanation').hidden = !open;
});
const notice = document.querySelector('#preview-notice');
function inform(text) { notice.querySelector('span').textContent = text; notice.hidden = false; }
document.querySelectorAll('[data-notice]').forEach(button => button.addEventListener('click', () => inform(button.dataset.notice)));
notice.querySelector('button').addEventListener('click', () => { notice.hidden = true; });
document.addEventListener('keydown', event => { if (event.key === 'Escape') notice.hidden = true; });
document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-filter]').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
  inform('Filtervorschau: Die Beispieldaten bleiben unverändert.');
}));

// Package stacks summarize different fixture stickers; they do not edit quantities.
document.querySelectorAll('.pax-stack').forEach(button => button.addEventListener('click', () => {
  const open = button.getAttribute('aria-expanded') !== 'true';
  button.setAttribute('aria-expanded', String(open));
  document.getElementById(button.getAttribute('aria-controls')).hidden = !open;
  button.closest('.board-side').classList.toggle('is-laid-out', open);
  button.nextElementSibling.textContent = open ? 'Wieder stapeln ↑' : 'Sticker auslegen ↗';
}));
document.querySelectorAll('.board-variant').forEach(button => button.addEventListener('click', () => {
  const board = button.closest('.board');
  board.dataset.variant = button.dataset.variant;
  board.querySelectorAll('.board-variant').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
}));
