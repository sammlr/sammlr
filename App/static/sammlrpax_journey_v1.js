/* Isolated design fixture. No network calls, persistence or domain actions. */
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('pj-data').textContent);
  const root = document.querySelector('.pj');
  const views = [...root.querySelectorAll('[data-screen]')];
  let perspective = 'valentin';
  let opening = null;
  let activeFan = null;
  const checked = new Set();
  const $ = id => document.getElementById(id);
  const node = (tag, cls, text) => { const el = document.createElement(tag); if (cls) el.className = cls; if (text !== undefined) el.textContent = text; return el; };
  const groupsFor = side => data[perspective === 'fatima' ? (side === 'receive' ? 'outgoing' : 'incoming') : (side === 'receive' ? 'incoming' : 'outgoing')];
  const face = (album, code, index = 0) => {
    const card = node('span', 'pj-face');
    card.style.setProperty('--pj-layer', index);
    card.dataset.code = code;
    const split = code.lastIndexOf(' ');
    card.append(node('span', 'pj-face-brand', 'sammlr.'), node('span', 'pj-face-prefix', code.slice(0, split)), node('strong', 'pj-face-number', code.slice(split + 1)), node('span', 'pj-face-album', album));
    return card;
  };
  const closeFan = () => {
    $('pj-fan').hidden = true;
    activeFan = null;
    root.querySelectorAll('[data-fan]').forEach(button => button.setAttribute('aria-expanded', 'false'));
  };
  function renderStacks() {
    root.querySelectorAll('[data-fan]').forEach(button => {
      const groups = groupsFor(button.dataset.fan);
      const stickers = groups.flatMap(([album, codes]) => codes.map(code => [album, code]));
      button.replaceChildren(...stickers.slice(0, 5).map(([album, code], i) => face(album, code, i)));
    });
  }
  function show(view) {
    if (opening) { clearTimeout(opening); opening = null; }
    $('pj-open').classList.remove('is-opening');
    $('pj-open').disabled = false;
    closeFan();
    perspective = view === 'partner' ? 'fatima' : 'valentin';
    const screen = view === 'partner' ? 'closed' : view;
    views.forEach(section => { section.hidden = section.dataset.screen !== screen; });
    root.dataset.view = view;
    root.querySelectorAll('.pj-tools [data-view]').forEach(button => {
      if (button.dataset.view === view) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    const partner = perspective === 'fatima';
    $('pj-persona').textContent = partner ? 'PARTNERANSICHT · DU BIST FATIMA' : 'DEIN NÄCHSTER TAUSCH';
    $('pj-pack-heading').textContent = partner ? 'Ein Pax von Valentin.' : 'Da steckt was für dich drin.';
    $('pj-pack-subtitle').textContent = partner ? '23 Sticker warten auf dich.' : 'Ein Pax. Sechs Alben. 23 neue Sticker.';
    $('pj-pack-partner').textContent = partner ? 'mit Valentin' : 'mit Fatima';
    $('pj-open').setAttribute('aria-label', `SammlrPax mit ${partner ? 'Valentin' : 'Fatima'} öffnen`);
    renderStacks();
    updateChecks();
    window.scrollTo({top: 0, behavior: 'instant'});
  }
  function openPack() {
    if (opening) return;
    const pack = $('pj-open');
    pack.disabled = true;
    pack.classList.add('is-opening');
    opening = setTimeout(() => {
      opening = null;
      pack.classList.remove('is-opening');
      pack.disabled = false;
      views.forEach(section => { section.hidden = section.dataset.screen !== 'board'; });
      root.dataset.view = perspective === 'fatima' ? 'partner-open' : 'board';
      root.querySelectorAll('.pj-tools [data-view]').forEach(button => {
        if (button.dataset.view === (perspective === 'fatima' ? 'partner' : 'board')) button.setAttribute('aria-current', 'step');
        else button.removeAttribute('aria-current');
      });
      renderBoardText();
      renderStacks();
      $('pj-board-heading').focus({preventScroll:true});
    }, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 420);
  }
  function renderBoardText() {
    const partner = perspective === 'fatima';
    $('pj-board-persona').textContent = partner ? 'PARTNERANSICHT · DU BIST FATIMA' : 'DEIN SAMMLRPAX';
    $('pj-board-heading').textContent = partner ? 'Mit Valentin tauschen.' : 'Mit Fatima tauschen.';
    $('pj-board-heading').nextElementSibling.textContent = partner ? '23 für dich. 23 für ihn.' : '23 für dich. 23 für sie.';
    $('pj-request').replaceChildren(document.createTextNode(partner ? 'Pax annehmen ' : 'Pax anfragen '), node('span', '', '↗'));
  }
  function fan(side) {
    if (activeFan === side) { closeFan(); return; }
    activeFan = side;
    root.querySelectorAll('[data-fan]').forEach(button => button.setAttribute('aria-expanded', String(button.dataset.fan === side)));
    $('pj-fan-title').textContent = side === 'receive' ? 'Die sind für dich.' : 'Die gibst du weiter.';
    const groups = groupsFor(side).map(([album, codes]) => {
      const group = node('section', 'pj-fan-group');
      group.append(node('h4', '', `${album} · ${codes.length} Sticker`));
      const grid = node('div', 'pj-fan-grid');
      codes.forEach((code, index) => {
        const card = node('div', 'pj-fan-card');
        card.style.setProperty('--pj-tilt', `${[-2, 1.5, -.7][index % 3]}deg`);
        card.append(face(album, code)); grid.append(card);
      });
      group.append(grid); return group;
    });
    $('pj-fan-cards').replaceChildren(...groups);
    $('pj-fan').hidden = false;
    $('pj-fan').scrollIntoView({block:'start', behavior:'instant'});
  }
  function updateChecks() {
    const remaining = 23 - checked.size;
    $('pj-check-count').textContent = `${checked.size} / 23`;
    $('pj-progress').textContent = remaining ? `Noch ${remaining} Sticker auf deiner Packliste.` : 'Alle 23 Sticker sind eingepackt.';
    $('pj-send').disabled = remaining !== 0;
  }
  data.outgoing.forEach(([album, codes], groupIndex) => {
    const group = node('section', 'pj-check-group');
    group.append(node('h3', '', album));
    codes.forEach((code, index) => {
      const label = node('label');
      const input = document.createElement('input'); input.type = 'checkbox'; input.value = `${groupIndex}-${index}`;
      input.addEventListener('change', () => {
        if (input.checked) checked.add(input.value); else checked.delete(input.value);
        updateChecks();
      });
      label.append(input, node('span', '', code)); group.append(label);
    });
    $('pj-checklist').append(group);
  });
  $('pj-expected-codes').textContent = `${data.incoming[0][1].slice(0, 2).join(' · ')} + 21`;
  const firstIncoming = data.incoming[0][1][0].split(' ');
  root.querySelector('.pj-little-card span').textContent = firstIncoming[0];
  root.querySelector('.pj-little-card strong').textContent = firstIncoming[1];
  root.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => { show(button.dataset.view); renderBoardText(); }));
  root.querySelectorAll('[data-fan]').forEach(button => button.addEventListener('click', () => fan(button.dataset.fan)));
  $('pj-close-fan').addEventListener('click', closeFan);
  $('pj-open').addEventListener('click', openPack);
  $('pj-request').addEventListener('click', () => {
    if (perspective === 'fatima') {
      show('shipping'); $('pj-live').textContent = 'Pax angenommen. Versandbrett aus Valentins Perspektive.';
    } else { show('sent'); $('pj-live').textContent = 'Pax an Fatima geschickt.'; }
  });
  $('pj-partner').addEventListener('click', () => show('partner'));
  $('pj-check-toggle').addEventListener('click', () => {
    const open = $('pj-checklist').hidden;
    $('pj-checklist').hidden = !open; $('pj-check-toggle').setAttribute('aria-expanded', String(open));
  });
  $('pj-send').addEventListener('click', () => {
    if (checked.size !== 23) return;
    show('done'); $('pj-live').textContent = 'Versand bestätigt. Deine Sticker sind unterwegs.';
  });
  show('closed');
  renderBoardText();
})();
