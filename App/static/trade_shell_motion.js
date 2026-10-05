// Production presentation adapter of TRADE-11 receive_motion.js's FLIP approach.
// Identical 440ms translation-only travel; real faces are cloned without scaling.
export const MOVE_MS = 440;
let finishCurrent = () => {};
export function settleMotion() { finishCurrent(); }
export function expandCards(origin, frames) {
  settleMotion();
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !frames.length) return;
  const layer = document.createElement('div');
  layer.className = 'trade-flight-layer';
  layer.setAttribute('aria-hidden', 'true');
  layer.inert = true;
  document.body.append(layer);
  const animations = [], restore = [];
  for (const frame of frames) {
    const rect = frame.getBoundingClientRect();
    const clone = frame.cloneNode(true);
    clone.querySelectorAll('[id]').forEach(e => e.removeAttribute('id'));
    clone.style.width = `${rect.width}px`;
    clone.style.left = `${rect.left}px`;
    clone.style.top = `${rect.top}px`;
    clone.style.visibility = '';
    layer.append(clone);
    const dx = origin.left + origin.width / 2 - rect.left - rect.width / 2;
    const dy = origin.top + origin.height / 2 - rect.top - rect.height / 2;
    animations.push(clone.animate([
      {translate:`${dx}px ${dy}px`}, {translate:'0px 0px'}
    ], {duration:MOVE_MS, easing:'cubic-bezier(.22,.7,.25,1)', fill:'both'}));
    restore.push([frame, frame.style.visibility]);
    frame.style.visibility = 'hidden';
  }
  let done = false;
  finishCurrent = () => {
    if (done) return;
    done = true;
    animations.forEach(a => a.cancel());
    restore.forEach(([e,v]) => { e.style.visibility = v; });
    layer.remove();
  };
  const finish = finishCurrent;
  Promise.all(animations.map(a => a.finished.catch(() => {}))).then(finish);
}
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', settleMotion);
window.addEventListener('resize', settleMotion);
window.addEventListener('scroll', settleMotion, {passive:true});
