import {completed} from './receipt_state.js';
import {perspective} from './requests.js';
import {opposite, version} from './deal_versions.js';
import {packSide} from './packing.js';
import {ownShipped, shippingSide, shippingState, bothShipped, fullyPacked} from './shipping_state.js';
import {targetAddress, releasePacking, chooseMethod, confirmShipment, reopenPacking} from './shipping.js';

const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
export function createShippingPanel(root,role,base,command,initialView='address') {
  let mode=['address','prepare','portal'].includes(initialView)?initialView:'address',request;
  const button=(text,id,action,secondary=false)=>{const b=node('button',text,`action${secondary?' secondary':''}`);b.type='button';b.id=id;b.addEventListener('click',action);return b;};
  const link=(text,href)=>{const a=node('a',text,'action secondary');a.href=href;return a;};
  function move(next){mode=next;render(request);root.querySelector('h2')?.focus();}
  function addressNote(address) {
    const note=node('div',undefined,'pax-address-note');note.id='ship-address-note';
    note.append(node('p','JETZT VERSENDEN AN','eyebrow'),node('address',address.join('\n')),node('p','Fiktive Demo-Adresse','intro'));return note;
  }
  function render(r) {
    request=r;root.replaceChildren();root.className='trade-shipping-panel';
    const view=perspective(r,role),other=opposite(role);
    const phase=shippingState(r,role);root.dataset.shippingState=phase;
    const heading=node('h2');heading.id='ship-heading';heading.tabIndex=-1;
    root.append(heading);
    if (r.status!=='accepted') {heading.textContent=r.status==='cancelled'?'Der Tausch wurde beendet.':'Noch kein aktiver Tausch';return;}
    if (completed(r) && ownShipped(r,role)) {heading.textContent='Tausch abgeschlossen ✓';root.append(link('Abschluss und Bewertung →',`${base}/receipt?role=${role}`));return;}
    if (ownShipped(r,role)) {
      heading.textContent=bothShipped(r)?'Beide Sendungen sind unterwegs ✓':'Deine Sticker sind unterwegs ✓';
      root.append(node('p',`Versendet an ${view.partner}.`));
      root.append(node('p',bothShipped(r)?'Der Tausch bleibt aktiv. Er ist noch nicht abgeschlossen.':packSide(r,other).phase==='packing_complete'?`${view.partner} hat noch nicht versendet.`:`${view.partner} packt noch.`));
      const details=node('details');details.id='ship-details';details.append(node('summary','Versanddetails anzeigen'));
      const content=node('div');details.append(content);
      details.addEventListener('toggle',()=>{
        content.replaceChildren();
        if (details.open) {const address=targetAddress(r,role);if(address)content.append(node('address',address.join('\n')));content.append(node('p','Versandart: Brief'));}
      });root.append(details);return;
    }
    if (r.amendment?.status==='pending' || ['sender','recipient'].some(side=>packSide(r,side).phase==='missing_reported')) {
      heading.textContent='Die Änderung muss zuerst geklärt werden.';root.append(link('Änderung ansehen →',`${base}/amendment?role=${role}`));return;
    }
    if (!fullyPacked(r,role)) {
      heading.textContent=ownShipped(r,other)?`${view.partner}s Sticker sind unterwegs zu dir.`:'Zuerst die eigene Packprüfung abschließen.';
      root.append(node('p','Du musst deine Sticker noch packen. Die Empfängeradresse ist noch nicht freigegeben.'));
      root.append(link('Zur Packliste →',`${base}/next?role=${role}`));return;
    }
    if (shippingSide(r,role).releasedVersion!==version(r)) {
      heading.textContent='Alles für dein Paket ist markiert.';
      root.append(node('p',`Prüfe deine ${view.give_count} Sticker und bestätige die Packfreigabe für das vereinbarte Paket.`));
      root.append(button('Packfreigabe bestätigen →','ship-release',()=>command(x=>releasePacking(x,role))));return;
    }
    const address=targetAddress(r,role);
    if (!address) {heading.textContent='Die Empfängeradresse ist noch nicht freigegeben.';root.append(node('p','Die Freigabe durch den Adressinhaber steht noch aus.'));return;}
    heading.textContent=mode==='address'?'Hier geht dein Paket hin.':mode==='portal'?'Versandportal · Demo':'Auf den Weg bringen.';
    // Only this authorized branch creates address nodes. No hidden or serialized address DOM.
    root.append(addressNote(address));
    if (mode==='address') {
      root.append(button('Versand vorbereiten →','ship-prepare',()=>move('prepare')));
      root.append(button('Packliste nochmals prüfen','ship-reopen',()=>command(x=>reopenPacking(x,role)),true));return;
    }
    if (mode==='portal') {
      root.append(node('p','Hier würdest du deinen Versand außerhalb von Sammlr vorbereiten. Diese lokale Vorschau öffnet keinen Anbieter, kauft keine Marke und überträgt keine Adresse. Dein Versand ist noch nicht bestätigt.'));
      root.append(button('Zurück zum Versand','ship-portal-back',()=>move('prepare')));return;
    }
    const label=node('label','Versand');label.htmlFor='ship-method';
    const select=node('select');select.id='ship-method';
    for(const [value,text] of [['','Bitte wählen'],['brief','Brief']]){const option=node('option',text);option.value=value;select.append(option);}
    select.value=shippingSide(r,role).method || '';
    select.addEventListener('change',()=>{command(x=>chooseMethod(x,role,select.value || null));root.querySelector('#ship-method')?.focus();});
    root.append(label,select,button('Versandportal ansehen ↗','ship-portal',()=>move('portal'),true));
    root.append(node('p','Nur lokale Vorschau. Du kannst auch eine eigene Briefmarke verwenden, eine Filiale nutzen oder bereits frankiert haben. Das Portal ist optional.','intro'));
    root.append(node('p','Bestätige erst, wenn du deine Sendung tatsächlich aufgegeben hast.'));
    const confirm=button('Versand bestätigen','ship-confirm',()=>command(x=>confirmShipment(x,role)));
    confirm.disabled=shippingSide(r,role).method!=='brief';root.append(confirm);
  }
  return {render};
}
export function shippingDev(r,role) {
  const other=opposite(role);
  return `Active deal version: ${version(r)}\nMy packing state: ${packSide(r,role).phase}\nPartner packing state: ${packSide(r,other).phase}\nMy shipping state: ${shippingState(r,role)}\nPartner shipping state: ${shippingState(r,other)}\nBoth shipped: ${bothShipped(r)}\nMy operational slot occupied: ${r.status==='accepted' && !ownShipped(r,role)}\nPartner operational slot occupied: ${r.status==='accepted' && !ownShipped(r,other)}\nAddress released for me: ${Boolean(targetAddress(r,role))}\nAddress released for partner: ${Boolean(targetAddress(r,other))}`;
}
