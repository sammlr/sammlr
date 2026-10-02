// Read the real wall's responsive layout, not a second hardcoded card size.
// The hidden read-only probe uses the exact owner-wall ancestor structure and stylesheet.
import {card} from '/static/pax/pax.js';
let ready;
export function prepareStickerPhysics(){
 if(ready)return ready;
 ready=new Promise((resolve,reject)=>{
  const probe=document.createElement('iframe');probe.id='trade-wall-measure';probe.title='';probe.tabIndex=-1;probe.setAttribute('aria-hidden','true');probe.inert=true;
  Object.assign(probe.style,{position:'fixed',left:'-200vw',top:'0',width:'100vw',height:'100vh',border:'0',visibility:'hidden',pointerEvents:'none'});
  probe.onload=async()=>{
   const doc=probe.contentDocument;await doc.fonts.ready;
   const read=()=>{const slot=doc.querySelector('.slot');if(!slot)return;
    const width=getComputedStyle(slot).width;
    document.documentElement.style.setProperty('--trade-card-width',width);
    document.documentElement.dataset.stickerPhysics='canonical-wall';
   };
   read();new ResizeObserver(read).observe(doc.querySelector('.wall'));resolve();
  };
  probe.onerror=reject;
  const sample=card([{key:'wall-measure',code:'BRA 1'}]);
  probe.srcdoc='<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"></head><body class="s31-product-page s30-reference-page s30-album-page"><div class="container"><div class="card sticker-wall-card"><div class="canonical-sticker-wall"><div class="wall">'+sample.outerHTML+'</div></div></div></div></body></html>';
  document.body.append(probe);
 });return ready;
}
