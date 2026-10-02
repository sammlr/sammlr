// Presentation-only FLIP: fixed-size canonical cards travel; no scale keyframes.
export const MOVE_MS=440;
let finishCurrent=()=>{};
const center=e=>{const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};};
const stackPoints=e=>[...e.querySelectorAll('.sticker-wall-stack-layer,.slot')].reverse().map(center);
const stackAngle=e=>{const m=new DOMMatrix(getComputedStyle(e).transform);return Math.atan2(m.b,m.a)*180/Math.PI;};
const angle=e=>parseFloat(e.style.getPropertyValue('--pax-angle'))||0;
export function installReceiveMotion(root,all){
 const sections=[...root.querySelectorAll('.pax-receive-album')];
 function move(changes,focus){
  finishCurrent();
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const plans=changes.filter(([s,open])=>s.classList.contains('is-expanded')!==open).map(([s,open])=>{
   const toggle=s.querySelector('.pax-album-toggle'),fan=s.querySelector('.pax-album-fan'),tiles=[...fan.querySelectorAll('.pax-fan-grid>.sticker-slot-frame')];
   return {s,open,toggle,fan,tiles,old:open?stackPoints(toggle):tiles.map(center),closedAngle:open?stackAngle(toggle):null};
  });
  if(!plans.length)return;
  const stationary=[...root.querySelectorAll('.sticker-slot-frame')].filter(e=>e.getClientRects().length&&!plans.some(p=>p.s.contains(e))).map(e=>({e,at:center(e)}));
  for(const p of plans){p.s.classList.toggle('is-expanded',p.open);p.fan.hidden=!p.open;p.toggle.hidden=p.open;p.toggle.setAttribute('aria-expanded',String(p.open));}
  focus?.focus({preventScroll:true});
  if(reduced)return;
  const layer=document.createElement('div');layer.className='pax-board trade-flight-layer';layer.setAttribute('aria-hidden','true');document.body.append(layer);
  const stage=document.createElement('div');stage.className='s30-album-page';layer.append(stage);
  const animations=[],restore=[];
  for(const p of plans){
   const stack=p.open?p.old:stackPoints(p.toggle),closedAngle=p.open?p.closedAngle:stackAngle(p.toggle);
   const positions=p.open?p.tiles.map(center):p.old;
   p.tiles.forEach((tile,index)=>{
    const clone=tile.cloneNode(true);clone.style.visibility='';
    // Closed hidden grid has no computed pixel width; the measured canonical width is authoritative.
    clone.style.width=getComputedStyle(document.documentElement).getPropertyValue('--trade-card-width');
    const width=parseFloat(clone.style.width),anchor=stack[Math.min(index,stack.length-1)];
    const from=p.open?anchor:positions[index],to=p.open?positions[index]:anchor;
    clone.style.left='0';clone.style.top='0';clone.style.zIndex=String(p.tiles.length-index);stage.append(clone);
    const height=clone.getBoundingClientRect().height;
    const transform=(pos,a)=>`translate(${pos.x-width/2}px,${pos.y-height/2}px) rotate(${a}deg)`;
    animations.push(clone.animate([{transform:transform(from,p.open?closedAngle:angle(tile))},{transform:transform(to,p.open?angle(tile):closedAngle)}],{duration:MOVE_MS,easing:'cubic-bezier(.22,.7,.25,1)',fill:'both'}));
    if(p.open){restore.push([tile,tile.style.visibility]);tile.style.visibility='hidden';}
   });
   if(!p.open){restore.push([p.toggle,p.toggle.style.visibility]);p.toggle.style.visibility='hidden';}
  }
  for(const {e,at} of stationary){
   const next=center(e),dx=at.x-next.x,dy=at.y-next.y;
   if(dx||dy)animations.push(e.animate([{translate:`${dx}px ${dy}px`},{translate:'0px 0px'}],{duration:MOVE_MS,easing:'cubic-bezier(.22,.7,.25,1)'}));
  }
  let done=false;
  const finish=()=>{if(done)return;done=true;animations.forEach(a=>a.cancel());restore.forEach(([e,v])=>e.style.visibility=v);layer.remove();};
  finishCurrent=finish;Promise.all(animations.map(a=>a.finished.catch(()=>{}))).then(finish);
 }
 for(const section of sections){
  const toggle=section.querySelector('.pax-album-toggle'),close=section.querySelector('.pj-simulation');
  toggle.addEventListener('click',event=>{event.stopImmediatePropagation();move([[section,true]],close);},true);
  close.addEventListener('click',event=>{event.stopImmediatePropagation();move([[section,false]],toggle);},true);
 }
 all.addEventListener('click',()=>move(sections.map(s=>[s,true]),all));
}
export function clearReceiveMotion(){finishCurrent();}

matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',()=>finishCurrent());
