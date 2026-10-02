import {shippingDemo} from './shipping_demo.js';
import {amendmentDemo} from './amendment_demo.js';
import {receive,allReceived,reportProblem,proposeResolution,confirmResolution,rate} from './receipts.js';
import {expectedPositions} from './receipt_state.js';
import {enterPacking,pieces,packSide,togglePiece,packAction} from './packing.js';
import {releasePacking,chooseMethod,confirmShipment} from './shipping.js';
export const RECEIPT_DEMOS=['waiting','unchecked','all-ok','problem-form','positions','problem','partner-problem','resolution-pending','confirm-resolution','resolved','one-final','both-ok','completed-v1','completed-v2','rating-empty','rating-1','rating-2','rating-3','rated','one-rated','history','cancelled','q2-waiting','q2-received','q2-ok','q2-ready-received','q2-problem','q2-completed'];
export function receiptDemo(deal,scenario,now=Date.now()) {
  if(scenario==='cancelled')return amendmentDemo(deal,'cancelled',now);
  const state=shippingDemo(deal,scenario==='q2-ready-received'?'me-ready':scenario.startsWith('q2-')?'address':scenario==='completed-v2'?'v2-shipped':'both',now),r=state.requests[deal.id];
  if(scenario==='completed-v2') {
    enterPacking(r,'recipient');for(const item of pieces(r,'recipient'))if(!packSide(r,'recipient').packed.includes(item.key))togglePiece(r,'recipient',item.key);
    packAction(r,'recipient','finish');releasePacking(r,'recipient');chooseMethod(r,'recipient','brief');confirmShipment(r,'recipient',now);
  }
  if(['waiting','q2-waiting'].includes(scenario))return state;
  receive(r,'sender',now);
  if(['unchecked','problem-form','positions','q2-received'].includes(scenario))return state;
  if(['problem','partner-problem','resolution-pending','confirm-resolution','resolved','q2-problem'].includes(scenario)) {
    reportProblem(r,'sender',['missing'],[expectedPositions(r,'sender')[2].positionId],now);
    if(['resolution-pending','confirm-resolution','resolved'].includes(scenario))proposeResolution(r,'recipient','sender',now);
    if(scenario==='resolved')confirmResolution(r,'sender',now);
    return state;
  }
  allReceived(r,'sender',now);
  if(['all-ok','one-final','q2-ok','q2-ready-received'].includes(scenario))return state;
  receive(r,'recipient',now);allReceived(r,'recipient',now);
  if(['rated','one-rated','history'].includes(scenario))rate(r,'sender',3,now);
  return state;
}
