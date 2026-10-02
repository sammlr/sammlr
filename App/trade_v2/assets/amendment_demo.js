// Explicit QA fixtures only. No demo query means no reset and no invented report.
import {initialState, send, decide} from './requests.js';
import {enterPacking, pieces, togglePiece, packAction} from './packing.js';
import {proposeAmendment, decideAmendment} from './amendments.js';
export const DEMOS=['missing','waiting','proposal','accepted','cancelled','partial-before','partial-after','shipped','empty','second'];
export function amendmentDemo(deal, scenario, now=Date.now()) {
  const state=initialState(2,now), r=send(state,deal,now).request;
  decide(state,r.id,'recipient','accept',now);enterPacking(r,'sender');enterPacking(r,'recipient');
  const own=pieces(r,'sender'), counter=pieces(r,'recipient');
  if (scenario!=='empty') own.slice(0,-2).forEach(i=>togglePiece(r,'sender',i.key));
  // Twelve already packed, including exactly one of the two future removals: 12 -> 11.
  [...counter.slice(0,11),counter.at(-1)].forEach(i=>togglePiece(r,'recipient',i.key));
  packAction(r,'sender','review');packAction(r,'sender','report');
  if (scenario==='shipped') r.recipientShipped=true; // DEV guard simulation; never a shipping command.
  if (scenario!=='missing') proposeAmendment(r,'sender',now);
  if (['accepted','partial-after','second'].includes(scenario)) decideAmendment(state,r.id,'recipient','accept',now);
  if (scenario==='cancelled') decideAmendment(state,r.id,'recipient','cancel',now);
  if (scenario==='second') {const active=state.requests[r.id];packAction(active,'recipient','review');packAction(active,'recipient','report');}
  return state;
}
