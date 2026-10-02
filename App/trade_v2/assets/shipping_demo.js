// Explicit QA entry points only; no real addresses, labels or carrier actions.
import {initialState,send,decide} from './requests.js';
import {enterPacking,pieces,togglePiece,packAction,packSide} from './packing.js';
import {amendmentDemo} from './amendment_demo.js';
import {releasePacking,chooseMethod,confirmShipment} from './shipping.js';
export const SHIPPING_DEMOS=['address','ready','me-packing','me-complete','me-ready','both','partner-first','v2-address','v2-ready','v2-shipped','locked','amendment-blocked','long','consent-blocked','full-unreleased'];
export function shippingDemo(deal,scenario,now=Date.now()) {
  let state,r;
  if (scenario.startsWith('v2-')) {state=amendmentDemo(deal,'accepted',now);r=state.requests[deal.id];}
  else {state=initialState(2,now);r=send(state,deal,now).request;decide(state,r.id,'recipient','accept',now);enterPacking(r,'sender');enterPacking(r,'recipient');}
  const complete=role=>{if(packSide(r,role).phase==='packing_complete')return;for(const i of pieces(r,role))if(!packSide(r,role).packed.includes(i.key))togglePiece(r,role,i.key);packAction(r,role,'finish');};
  const ready=role=>{complete(role);releasePacking(r,role);};
  const ship=role=>{ready(role);chooseMethod(r,role,'brief');confirmShipment(r,role,now);};
  if (scenario==='locked') pieces(r,'sender').slice(0,22).forEach(i=>togglePiece(r,'sender',i.key));
  else if (scenario==='full-unreleased') pieces(r,'sender').forEach(i=>togglePiece(r,'sender',i.key));
  else if (scenario==='partner-first') ship('recipient');
  else {
    ready('sender');
    if (['ready','v2-ready'].includes(scenario)) chooseMethod(r,'sender','brief');
    if (['me-packing','me-complete','me-ready','both','v2-shipped','amendment-blocked'].includes(scenario)) ship('sender');
    if (scenario==='me-complete') complete('recipient');
    if (scenario==='me-ready') ready('recipient');
    if (scenario==='both') ship('recipient');
    if (['me-packing','amendment-blocked'].includes(scenario)) pieces(r,'recipient').slice(0,12).forEach(i=>togglePiece(r,'recipient',i.key));
  }
  if (scenario==='amendment-blocked') {packAction(r,'recipient','review');packAction(r,'recipient','report');}
  if (scenario==='long')r.demoLongAddress=true;
  if (scenario==='consent-blocked')r.demoAddressConsent={recipient:false,sender:true};
  return state;
}
