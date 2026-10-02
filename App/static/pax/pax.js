/* PAX-01–03: local display state only. No storage, network commands or domain actions. */
const CEOKLAUE_STICKER_LIST_SEED = 'pax-01-03';
// Pure handwriting helpers mirrored from sticker_list.js.
function stickerListCeoklaueIndex(text, character, position, context, previousAlternate){
    const payload = CEOKLAUE_STICKER_LIST_SEED + '\0' + context + '\0' + text + '\0' + position + '\0' + character;
    let value = 2166136261;
    for(let index = 0; index < payload.length; index += 1){
        value ^= payload.charCodeAt(index);
        value = Math.imul(value, 16777619) >>> 0;
    }
    let alternate = value % 3;
    if(previousAlternate !== undefined && alternate === previousAlternate - 1){
        alternate = (alternate + 1 + ((value >>> 8) & 1)) % 3;
    }
    return alternate + 1;
}

function stickerListWriteCeoklaue(target, text, context){
    target.replaceChildren();
    const run = document.createElement('span');
    run.className = 'ceoklaue-run';
    run.setAttribute('aria-label', text);
    run.dataset.ceoklaueContext = context;
    const previousAlternates = Object.create(null);
    Array.from(text).forEach(function(character, position){
        const glyph = document.createElement('span');
        glyph.setAttribute('aria-hidden', 'true');
        glyph.textContent = character;
        if(character === ' '){
            glyph.className = 'ceoklaue-space';
        }else if('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789äöüÄÖÜß.,:;!?-+/&%()'.includes(character)){
            const alternate = stickerListCeoklaueIndex(
                text, character, position, context, previousAlternates[character]
            );
            previousAlternates[character] = alternate;
            glyph.className = 'ceoklaue-glyph ceoklaue-alt-' + alternate;
            glyph.dataset.character = character;
            glyph.dataset.alternate = String(alternate);
        }else{
            glyph.className = 'ceoklaue-fallback';
        }
        run.appendChild(glyph);
    });
    target.appendChild(run);
}


// Canonical stickerListRenderReviewMode capacities and sequential chunking.
export function splitReviewItems(items) {
  if (!items.length) return [];
  const notes = [{items: items.slice(0, 16), columnCapacity: 8, continuation: false}];
  for (let start = 16; start < items.length; start += 20) {
    notes.push({items: items.slice(start, start + 20), columnCapacity: 10, continuation: true});
  }
  return notes;
}

const node = (tag, cls, text) => {
  const result = document.createElement(tag);
  result.className = cls || '';
  if (text !== undefined) result.textContent = text;
  return result;
};

// Canonical wall face markup (webapp.py), consuming only synthetic fixture codes.
function face(code) {
  const [prefix, number] = code.split(' ');
  const fragment = document.createDocumentFragment();
  fragment.append(node('span', 'sticker-team', prefix));
  const container = node('span', 'sammlr-retro-number variant-v3 wall-number');
  container.append(node('span', 'sammlr-retro-number-text', number));
  const visual = node('span', 'sammlr-retro-number-visual');
  visual.setAttribute('aria-hidden', 'true');
  const ns = 'http://www.w3.org/2000/svg';
  for (const digit of number) {
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('class', 'sammlr-retro-digit');
    svg.setAttribute('viewBox', '0 0 68 104');
    svg.setAttribute('focusable', 'false');
    for (const layer of ['depth', 'face']) {
      const use = document.createElementNS(ns, 'use');
      use.setAttribute('class', `sammlr-retro-digit-${layer}`);
      use.setAttribute('href', `/static/sammlr-retro-digits-v3.svg#sammlr-digit-v3-${digit}`);
      if (layer === 'depth') use.setAttribute('transform', 'translate(4 5)');
      svg.append(use);
    }
    visual.append(svg);
  }
  container.append(visual);fragment.append(container);return fragment;
}

// Canonical wall geometry; only the Receive cap differs (Wall: 5, Pax: 10).
export const maxVisibleLayers = 10;
export function card(items, stack = false) {
  const layers = stack ? Math.min(items.length, maxVisibleLayers) : 1;
  const frame = node('span', 'sticker-slot-frame');
  frame.dataset.itemKey = items[0].key;
  frame.style.setProperty('--stack-front-index', layers - 1);
  for (let index = 0; index < layers - 1; index++) {
    const back = node('i', 'sticker-wall-stack-layer');
    back.style.setProperty('--stack-index', index);
    back.dataset.stackLayer = index;
    back.setAttribute('aria-hidden', 'true');back.append(face(items[0].code));frame.append(back);
  }
  const top = node('span', `slot ${layers > 1 ? 'duplicate' : 'owned'}`);
  top.style.setProperty('--stack-index', layers - 1);
  top.append(face(items[0].code));frame.append(top);return frame;
}

// Stable per-item variation, never random or dependent on render timing.
function paperPose(element, key, index, note = false) {
  let hash = 2166136261;
  for (const char of key) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619) >>> 0;
  const angle = ((index % 2) ? -1 : 1) * (0.35 + (hash % 7) / 10);
  element.style.setProperty('--pax-angle', `${angle}deg`);
  element.style.setProperty('--pax-x', `${note ? 0 : hash % 3 - 1}px`);
  element.style.setProperty('--pax-y', `${note ? 0 : (hash >>> 4) % 3 - 1}px`);
  element.classList.add(note ? 'pax-loose-note' : 'pax-loose-card');
}

export function renderReceive(albums) {
  const target = document.getElementById('pax-receive-albums');
  albums.forEach(album => {
    const section = node('section', 'pax-receive-album');
    section.dataset.album = album.id;
    const title = node('h3', '', album.title);section.append(title);
    section.append(node('p', 'pax-album-count', `${album.items.length} Sticker`));
    const toggle = node('button', 'pax-album-toggle');toggle.type = 'button';
    const fanId = `pax-fan-${album.id}`;
    toggle.setAttribute('aria-expanded', 'false');toggle.setAttribute('aria-controls', fanId);
    toggle.setAttribute('aria-label', `${album.title}: ${album.items.length} Sticker auslegen`);
    toggle.append(card(album.items, true));
    const hint = node('span', 'pj-tap', 'Antippen & auslegen');toggle.append(hint);section.append(toggle);
    const fan = node('div', 'pax-album-fan');fan.id = fanId;fan.hidden = true;
    const close = node('button', 'pj-simulation', 'Zusammenlegen ↑');close.type = 'button';fan.append(close);
    const grid = node('div', 'pax-fan-grid');
    album.items.forEach((item, index) => {const tile = card([item]);paperPose(tile, item.key, index);grid.append(tile);});fan.append(grid);section.append(fan);
    const setOpen = open => {
      fan.hidden = !open;toggle.hidden = open;
      section.classList.toggle('is-expanded', open);
      toggle.setAttribute('aria-expanded', String(open));
      (open ? close : toggle).focus({preventScroll: true});
    };
    toggle.addEventListener('click', () => setOpen(true));
    close.addEventListener('click', () => setOpen(false));
    target.append(section);
  });
}

export function renderGive(albums) {
  const target = document.getElementById('pax-give-albums');
  albums.forEach(album => {
    const group = node('section', 'pax-give-album');group.dataset.album = album.id;
    const headingId = `pax-give-title-${album.id}`;
    group.setAttribute('aria-labelledby', headingId);
    splitReviewItems(album.items).forEach((chunk, index) => {
      const note = node('div', `trade-postit trade-postit-content trade-postit-give${chunk.continuation ? ' is-continuation' : ''}`);
      paperPose(note, album.id + ':' + index, index, true);
      if (!chunk.continuation) {
        const title = node('h3');title.id = headingId;
        stickerListWriteCeoklaue(title, album.title, `album-${album.id}`);note.append(title);
        const underline = node('img', 'postit-underline');underline.src = '/static/ceoklaue-ui/underline.svg';underline.alt = '';note.append(underline);
      } else {
        note.dataset.reviewContinuation = String(index + 1);
        note.setAttribute('aria-label', `${album.title}, Fortsetzung ${index}`);
      }
      const codes = node('div', 'sticker-list-review-codes');
      codes.classList.toggle('is-two-column', chunk.items.length > chunk.columnCapacity);
      chunk.items.forEach(item => {
        const row = node('div', 'pending-review-row');row.dataset.itemKey = item.key;
        const label = node('strong', 'sticker-list-review-code');
        stickerListWriteCeoklaue(label, item.code, `review-${item.key}`);
        row.append(label);codes.append(row);
      });
      note.append(codes);group.append(note);
    });
    target.append(group);
  });
}

const dataNode = document.getElementById('pax-data');
if (dataNode) {
  import('./journey.js').then(({startJourney}) => startJourney(JSON.parse(dataNode.textContent)));
}

// Native links: one activation opens the exact candidate; no selection state.
document.querySelectorAll('.pax-counter-pack').forEach(pack => {
  pack.addEventListener('keydown', event => {
    if (event.key === ' ') {event.preventDefault();if (!event.repeat) pack.click();}
  });
});
