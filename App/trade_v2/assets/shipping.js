// Adapted PAX-06 mechanics, same-tab demo only; no network, carrier or inventory commands.
import {ROLES, opposite, version, validVersions} from './deal_versions.js';
import {validPacking} from './packing.js';
import {ownShipped, shippingSide, shippingAllowed, validShipping} from './shipping_state.js';
const empty=()=>({releasedVersion:null,method:null,shippedAt:null});
const valid=r=>validVersions(r) && validPacking(r) && validShipping(r);
export function demoAddress(r,owner) {
  // Explicitly fictional owners have consented in this demo, independently of packing.
  const participants={
    sender:{addressReleased:true,address:['Valentin Beispiel (Demo)','Erfundener Beispielweg 12','00000 Musterstadt (Demo)']},
    recipient:{addressReleased:true,address:[`${r.snapshot.partner} Beispiel (Demo)`,'Erfundene Musterstraße 89','00000 Beispielstadt (Demo)']},
  };
  if (r.demoLongAddress) participants.recipient.address=['Fatima Alexandra Muster-Beispiel (Demo)','Erfundene Straße der langen Beispieladressen 123 B','00000 Musterstadt am Beispielberg (Demo)'];
  const participant=participants[owner];
  if (r.demoAddressConsent?.[owner]===false) return null;
  return participant?.addressReleased ? participant.address : null;
}
export function targetAddress(r,role) {
  if (!ROLES.includes(role) || !valid(r) || !shippingAllowed(r,role) || shippingSide(r,role).releasedVersion!==version(r)) return null;
  return demoAddress(r,opposite(role));
}
export function releasePacking(r,role) {
  if (!ROLES.includes(role) || !valid(r) || !shippingAllowed(r,role) || ownShipped(r,role)) return false;
  r.shipping ||= {sender:empty(),recipient:empty()};
  r.shipping[role].releasedVersion=version(r);
  return true;
}
export function chooseMethod(r,role,method) {
  if (!targetAddress(r,role) || ownShipped(r,role) || ![null,'brief'].includes(method)) return false;
  r.shipping[role].method=method;return true;
}
export function confirmShipment(r,role,now=Date.now()) {
  if (!ROLES.includes(role) || !Number.isFinite(now) || r.status!=='accepted' || !valid(r)) return false;
  if (ownShipped(r,role)) return false;
  if (!targetAddress(r,role) || shippingSide(r,role).method!=='brief') return false;
  r.shipping[role].shippedAt=now;
  r[role==='sender'?'ownShipped':'recipientShipped']=true;
  return true;
}
export function reopenPacking(r,role) {
  if (!ROLES.includes(role) || !valid(r) || r.status!=='accepted' || ownShipped(r,role) || r.amendment?.status==='pending' || r.packing?.[role]?.phase!=='packing_complete') return false;
  r.packing[role].phase='packing';
  if (r.shipping) r.shipping[role]=empty();
  return true;
}
