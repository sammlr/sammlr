// Pure handwriting functions adapted verbatim from frozen sticker_list.js.
const CEOKLAUE_STICKER_LIST_SEED="sammlr-ceoklaue-stickerlist-v1";
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

export function stickerListWriteCeoklaue(target, text, context){
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


export const MARKERS={"receive_circle": [{"variant": "01", "url": "/static/ceoklaue-markers/receive_circle/receive_circle_01.svg"}, {"variant": "02", "url": "/static/ceoklaue-markers/receive_circle/receive_circle_02.svg"}, {"variant": "04", "url": "/static/ceoklaue-markers/receive_circle/receive_circle_04.svg"}, {"variant": "03", "url": "/static/ceoklaue-markers/receive_circle/receive_circle_03.svg"}, {"variant": "05", "url": "/static/ceoklaue-markers/receive_circle/receive_circle_05.svg"}], "give_cross": [{"variant": "05", "url": "/static/ceoklaue-markers/give_cross/give_cross_05.svg"}, {"variant": "03", "url": "/static/ceoklaue-markers/give_cross/give_cross_03.svg"}, {"variant": "04", "url": "/static/ceoklaue-markers/give_cross/give_cross_04.svg"}, {"variant": "01", "url": "/static/ceoklaue-markers/give_cross/give_cross_01.svg"}, {"variant": "02", "url": "/static/ceoklaue-markers/give_cross/give_cross_02.svg"}]};
// Frozen sticker_list.py list_item structure, with album-qualified DOM/selection identity.
const node=(tag,cls)=>{const e=document.createElement(tag);if(cls)e.className=cls;return e;};
export function listItem(item,mode,album,separator){
  const wrap=node('span','sticker-list-entry');wrap.dataset.semanticSeparator=separator?'after':'none';
  const button=node('button','sticker-list-item');button.type='button';Object.assign(button.dataset,{listMode:mode,code:item.code,display:item.code,instance:item.instance,key:item.key,album});button.setAttribute('aria-pressed','false');button.setAttribute('aria-label',`${album}, ${item.code}, ${mode==='get'?'erhalten':'abgeben'}, Exemplar ${item.instance}`);
  stickerListWriteCeoklaue(button,item.code,`sticker-list-${album}-code-${mode}-${item.code}-${item.instance}`);
  const family=mode==='get'?'receive_circle':'give_cross',payload=`sammlr-ceoklaue-stickerlist-markers-v1\0sticker-list-${album}-marker\0${family}\0${item.code}\0${item.instance}`;
  let hash=2166136261;for(const char of payload)hash=Math.imul(hash^char.codePointAt(0),16777619)>>>0;
  const marker=MARKERS[family][hash%5];button.dataset.markerFamily=family;button.dataset.markerVariant=marker.variant;
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.classList.add('sticker-selection-marker');svg.setAttribute('viewBox','0 0 1000 620');svg.setAttribute('aria-hidden','true');
  const image=document.createElementNS(ns,'image');image.setAttribute('href',marker.url);image.setAttribute('width','1000');image.setAttribute('height','620');image.setAttribute('preserveAspectRatio','xMidYMid meet');
  if(mode==='get')svg.dataset.markerRendering='static';else{
    svg.dataset.drawDirection='top-left-to-bottom-right-then-top-right-to-bottom-left';
    const defs=document.createElementNS(ns,'defs'),mask=document.createElementNS(ns,'mask');mask.id=`marker-${album}-${mode}-${item.code.replace(/[^A-Za-z0-9_-]/g,'-')}-${item.instance}`;
    for(const [index,d] of ['M150 90L850 530','M850 90L150 530'].entries()) {const path=document.createElementNS(ns,'path');path.setAttribute('class',`marker-draw marker-draw-cross marker-draw-${index?'two':'one'}`);path.setAttribute('pathLength','1');path.setAttribute('d',d);mask.append(path);}
    defs.append(mask);svg.append(defs);image.setAttribute('mask',`url(#${mask.id})`);
  }
  svg.append(image);button.append(svg);wrap.append(button);
  if(separator){const comma=node('span','sticker-list-comma');comma.setAttribute('aria-hidden','true');stickerListWriteCeoklaue(comma,',',`sticker-list-${album}-comma-${mode}-${item.code}-${item.instance}`);wrap.append(comma);}
  return wrap;
}
export function bracket(target,label){
  const content=node('span','analog-bracket-content');content.dataset.bracketPair='01';
  const text=node('span','analog-bracket-label');stickerListWriteCeoklaue(text,label,'trade-manual-'+label);
  for(const side of ['left','right']) {const img=node('img','analog-bracket analog-bracket-'+side);img.src=`/static/ceoklaue-ui/button-brackets/button_bracket_01_${side}.svg`;img.alt='';if(side==='left')content.append(img,text);else content.append(img);}
  target.replaceChildren(content);
}
