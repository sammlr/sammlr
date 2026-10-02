// Local demo commands: no shipping, packing, slot, snapshot or inventory mutation.
import {ROLES,opposite,validVersions,version} from './deal_versions.js';
import {validPacking} from './packing.js';
import {validShipping} from './shipping_state.js';
import {receiptSide,completed,validReceipt,validProblem} from './receipt_state.js';
const valid=r=>r?.status==='accepted' && validVersions(r) && validPacking(r) && validShipping(r) && validReceipt(r);
const empty=()=>({state:'WAITING',receivedAt:null,version:null,problem:null});
function finish(r,now){if(completed(r) && r.completedAt===undefined)r.completedAt=now;}
export function receive(r,role,now=Date.now()) {
  if(!ROLES.includes(role)||!valid(r)||!Number.isFinite(now)||receiptSide(r,role).state!=='WAITING')return false;
  r.receipts ||= {sender:empty(),recipient:empty()};
  Object.assign(r.receipts[role],{state:'RECEIVED_UNCHECKED',receivedAt:now,version:version(r)});return true;
}
export function allReceived(r,role,now=Date.now()) {
  if(!ROLES.includes(role)||!valid(r)||!Number.isFinite(now)||receiptSide(r,role).state!=='RECEIVED_UNCHECKED'||now<receiptSide(r,role).receivedAt)return false;
  r.receipts[role].state='RECEIVED_OK';finish(r,now);return true;
}
export function reportProblem(r,role,types,positionIds,now=Date.now()) {
  if(!ROLES.includes(role)||!valid(r)||!Number.isFinite(now)||receiptSide(r,role).state!=='RECEIVED_UNCHECKED'||now<receiptSide(r,role).receivedAt)return false;
  const problem={reporter:role,version:version(r),types,positionIds,reportedAt:now,proposedAt:null,resolvedAt:null};
  if(!validProblem(r,role,problem))return false;
  r.receipts[role].problem=structuredClone(problem);r.receipts[role].state='PROBLEM_REPORTED';return true;
}
export function proposeResolution(r,actor,reporter,now=Date.now()) {
  if(!ROLES.includes(actor)||!ROLES.includes(reporter)||actor!==opposite(reporter)||!valid(r)||!Number.isFinite(now))return false;
  const s=receiptSide(r,reporter);
  if(s.state!=='PROBLEM_REPORTED'||now<s.problem.reportedAt)return false;
  s.state='RESOLUTION_PENDING';s.problem.proposedAt=now;s.problem.proposedBy=actor;return true;
}
export function confirmResolution(r,actor,now=Date.now()) {
  if(!ROLES.includes(actor)||!valid(r)||!Number.isFinite(now))return false;
  const s=receiptSide(r,actor);
  if(s.state!=='RESOLUTION_PENDING'||now<s.problem.proposedAt)return false;
  s.state='RESOLVED';s.problem.resolvedAt=now;s.problem.resolvedBy=actor;finish(r,now);return true;
}
export function rate(r,role,stars,now=Date.now()) {
  if(!ROLES.includes(role)||!valid(r)||!completed(r)||!Number.isInteger(stars)||stars<1||stars>3||!Number.isFinite(now)||now<r.completedAt||r.ratings?.[role])return false;
  r.ratings ||= {};r.ratings[role]={stars,forRole:opposite(role),savedAt:now};return true;
}
