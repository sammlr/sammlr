/* Local-only fixture. Canonical markup mirrored from webapp.py and sticker_list.py.
 * No production controllers, requests, storage, or domain imports. */
(() => {
'use strict';
const CEOKLAUE_STICKER_LIST_SEED = 'pax-preview-v2';
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


const $ = id => document.getElementById(id);
const data = JSON.parse($('v2-data').textContent);
const checked = {valentin:new Set(), fatima:new Set()};
let persona = 'valentin', timer = null;
const groups = side => data[persona === 'valentin' ? (side === 'receive' ? 'incoming' : 'outgoing') : (side === 'receive' ? 'outgoing' : 'incoming')];
const el = (tag, cls, text) => {const n=document.createElement(tag);n.className=cls||'';if(text!==undefined)n.textContent=text;return n;};
function face(code) {
  const [prefix,number] = code.split(' ');
  return `<span class="sticker-team">${prefix}</span><span class="sammlr-retro-number variant-v3 wall-number"><span class="sammlr-retro-number-text">${number}</span><span class="sammlr-retro-number-visual" aria-hidden="true">${[...number].map(d=>`<svg class="sammlr-retro-digit" viewBox="0 0 68 104" aria-hidden="true" focusable="false"><use class="sammlr-retro-digit-depth" transform="translate(4 5)" href="/static/sammlr-retro-digits-v3.svg#sammlr-digit-v3-${d}"></use><use class="sammlr-retro-digit-face" href="/static/sammlr-retro-digits-v3.svg#sammlr-digit-v3-${d}"></use></svg>`).join('')}</span></span>`;
}
function card(code, stack=false) {
  const frame=el('span','sticker-slot-frame');frame.style.display='block';frame.dataset.code=code;
  frame.style.setProperty('--stack-front-index',stack?4:0);
  if(stack)for(let i=0;i<4;i++){const back=el('i','sticker-wall-stack-layer');back.style.setProperty('--stack-index',i);back.setAttribute('aria-hidden','true');back.innerHTML=face(code);frame.append(back);}
  const front=el('span',`slot ${stack?'duplicate':'owned'}`);front.style.setProperty('--stack-index',stack?4:0);front.innerHTML=face(code);frame.append(front);return frame;
}
function show(screen) {
  document.querySelectorAll('[data-screen]').forEach(n=>n.hidden=n.dataset.screen!==screen);
  document.body.dataset.view=screen;
  window.scrollTo(0,0);
  document.querySelector(`[data-screen="${screen}"] h1`)?.focus({preventScroll:true});
}
function progress() {
  const count=checked[persona].size,total=groups('give').reduce((n,g)=>n+g[1].length,0);
  $('v2-progress').textContent=`${count} / ${total} geprüft`;
  $('v2-request').disabled=count!==total;
}
function collapse() {
  $('v2-fan').hidden=true;$('v2-stack-toggle').hidden=false;$('v2-tap').hidden=false;
  $('v2-stack-toggle').setAttribute('aria-expanded','false');
}
function renderBoard() {
  const partner=persona==='fatima';
  $('v2-persona').textContent=partner?'PARTNERANSICHT · DU BIST FATIMA':'DEIN SAMMLRPAX';
  $('v2-heading').textContent=partner?'Mit Valentin tauschen.':'Mit Fatima tauschen.';
  $('v2-request').textContent=partner?'Pax annehmen →':'Pax anfragen →';
  $('v2-stack').replaceChildren(card(groups('receive')[0][1][0],true));
  $('v2-cards').replaceChildren(...groups('receive').map(([album,codes])=>{
    const section=el('section','v2-card-group');section.append(el('h3','',album));
    const grid=el('div','v2-cards-grid');codes.forEach(code=>grid.append(card(code)));section.append(grid);return section;
  }));
  $('v2-notes').replaceChildren(...groups('give').map(([album,codes],g)=>{
    const note=el('section','trade-postit trade-postit-content trade-postit-give');
    const title=el('h3');stickerListWriteCeoklaue(title,album,`album-${g}`);note.append(title);
    const underline=el('img','postit-underline');underline.src='/static/ceoklaue-ui/underline.svg';underline.alt='';underline.style.width='100%';note.append(underline);
    codes.forEach((code,i)=>{
      const key=`${g}-${i}`,id=`v2-marker-${persona}-${key}`;
      const button=el('button','sticker-list-item v2-todo');button.type='button';button.dataset.code=code;button.dataset.album=album;button.dataset.listMode='give';
      const selected=checked[persona].has(key);button.classList.toggle('selected',selected);button.classList.toggle('is-restored',selected);button.setAttribute('aria-pressed',String(selected));
      stickerListWriteCeoklaue(button,code,`code-${g}-${i}`);
      button.insertAdjacentHTML('beforeend',`<svg class="sticker-selection-marker" viewBox="0 0 1000 620" aria-hidden="true"><defs><mask id="${id}"><path class="marker-draw marker-draw-cross marker-draw-one" pathLength="1" d="M150 90L850 530"/><path class="marker-draw marker-draw-cross marker-draw-two" pathLength="1" d="M850 90L150 530"/></mask></defs><image href="/static/ceoklaue-markers/give_cross/give_cross_0${(g+i)%5+1}.svg" width="1000" height="620" preserveAspectRatio="xMidYMid meet" mask="url(#${id})"/></svg>`);
      button.addEventListener('click',()=>{if(checked[persona].has(key))checked[persona].delete(key);else checked[persona].add(key);button.classList.remove('is-restored');button.classList.toggle('selected',checked[persona].has(key));button.setAttribute('aria-pressed',String(checked[persona].has(key)));progress();});
      note.append(button);
    });return note;
  }));
  collapse();progress();
  document.fonts.ready.then(()=>document.querySelectorAll('#v2-notes h3').forEach(h=>h.nextElementSibling.style.width=`${Math.ceil(h.getBoundingClientRect().width+6)}px`));
}
function reset(){clearTimeout(timer);timer=null;persona='valentin';checked.valentin.clear();checked.fatima.clear();$('pj-open').disabled=false;$('pj-open').classList.remove('is-opening');renderBoard();show('closed');}
$('pj-open').addEventListener('click',()=>{if(timer)return;$('pj-open').disabled=true;$('pj-open').classList.add('is-opening');timer=setTimeout(()=>{timer=null;$('pj-open').classList.remove('is-opening');$('pj-open').disabled=false;renderBoard();show('board');},matchMedia('(prefers-reduced-motion: reduce)').matches?0:420);});
$('v2-stack-toggle').addEventListener('click',()=>{$('v2-fan').hidden=false;$('v2-stack-toggle').hidden=true;$('v2-tap').hidden=true;$('v2-stack-toggle').setAttribute('aria-expanded','true');$('v2-collapse').focus({preventScroll:true});});
$('v2-collapse').addEventListener('click',()=>{collapse();$('v2-stack-toggle').focus({preventScroll:true});});
$('v2-request').addEventListener('click',()=>{if($('v2-request').disabled)return;show(persona==='fatima'?'shipping':'sent');});
$('v2-partner').addEventListener('click',()=>{persona='fatima';renderBoard();show('board');});
$('v2-send').addEventListener('click',()=>show('done'));
$('v2-reset').addEventListener('click',reset);$('v2-again').addEventListener('click',reset);reset();
})();
