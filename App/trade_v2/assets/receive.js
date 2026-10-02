// Reuse the canonical faces, layering and deterministic poses without changing Pax.
import {renderReceive as canonicalReceive} from '/static/pax/pax.js';
import {installReceiveMotion,clearReceiveMotion} from './receive_motion.js';
export function renderReceive(albums){
  clearReceiveMotion();
  const root=document.getElementById('pax-receive-albums');root.replaceChildren();
  const display=albums.map(a=>({...a,items:a.items.map(i=>/^\d+$/.test(i.code)?{...i,code:' '+i.code}:i)}));
  canonicalReceive(display);
  root.querySelectorAll('.sticker-team').forEach(e=>{if(!e.textContent)e.classList.add('empty');});
  const all=document.createElement('button');all.type='button';all.className='action secondary receive-all';all.textContent='Alle anzeigen';root.before(all);
  root.parentElement.querySelectorAll('.receive-all').forEach(b=>{if(b!==all)b.remove();});
  root.querySelectorAll('.pj-tap').forEach(e=>e.remove());
  installReceiveMotion(root,all);
}
