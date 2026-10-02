import {hasReceipt} from './receipt_state.js';
import {freezeSnapshot, positions, opposite, ROLES, version, shipped, reduction, validVersions} from './deal_versions.js';
import {packSide, validPacking} from './packing.js';

export function proposalBlock(request, role) {
  if (!request || request.status!=='accepted' || !ROLES.includes(role)) return 'unavailable';
  if (shipped(request) || hasReceipt(request)) return 'shipped';
  if (!validVersions(request) || !validPacking(request)) return 'invalid';
  if (version(request)!==1) return 'further_change';
  if (request.amendment) return 'existing';
  if (packSide(request,role).phase!=='missing_reported') return 'not_reported';
  if (packSide(request,opposite(role)).phase==='missing_reported') return 'both_reported';
  return null;
}
export function proposeAmendment(request, role, now=Date.now()) {
  const blocked=proposalBlock(request,role);
  if (blocked) return blocked;
  const missingKeys=packSide(request,role).missingReported.slice();
  const proposal=reduction(request.snapshot,role,missingKeys);
  if (!proposal) return 'unmatched_positions';
  // V1 remains the active snapshot until the other participant explicitly agrees.
  const original=request.snapshot;
  Object.assign(request,{
    deal_version:1,
    dealVersions:freezeSnapshot([{version:1,snapshot:original}]),
    positionOrder:freezeSnapshot({sender:positions(original,'sender'),recipient:positions(original,'recipient')}),
    amendment:{id:`${request.id}/amendment/1`,baseVersion:1,status:'pending',proposer:role,proposedAt:now,
      missingKeys,proposal:freezeSnapshot(proposal)},
  });
  return 'pending';
}
export function decideAmendment(state, id, role, action, now=Date.now(), expectedId=null) {
  const r=state.requests[id],a=r?.amendment;
  if (!a || !ROLES.includes(role) || role!==opposite(a.proposer) || !['accept','cancel'].includes(action)) return 'forbidden';
  if (expectedId && expectedId!==a.id) return 'stale';
  if (a.status!=='pending') return a.status; // First decision wins, including opposite retries.
  if (shipped(r) || hasReceipt(r)) return 'shipped';
  if (r.status!=='accepted' || !validVersions(r) || !validPacking(r)) return 'invalid';
  if (action==='accept' && !a.proposal.continuable) return 'empty';
  // A second independent missing report requires resolution, not silent deletion/acceptance.
  if (action==='accept' && packSide(r,role).missingReported.some(key=>positions(a.proposal.snapshot,role).some(i=>i.key===key))) return 'further_change';
  const next=structuredClone(r);
  next.amendment.decidedAt=now;
  if (action==='cancel') {
    next.status='cancelled';next.cancelledAt=now;
    next.amendment.status='cancelled';next.amendment.cancelledBy=role;
  } else {
    next.amendment.status='accepted';next.amendment.acceptedBy=role;
    // A changed physical package requires a fresh conscious release in each direction.
    if (next.shipping) next.shipping={sender:{releasedVersion:null,method:null,shippedAt:null},recipient:{releasedVersion:null,method:null,shippedAt:null}};
    next.deal_version=2;next.snapshot=freezeSnapshot(structuredClone(a.proposal.snapshot));
    next.dealVersions.push({version:2,snapshot:next.snapshot,acceptedAt:now,acceptedBy:role});
    for (const side of ROLES) {
      const keep=new Set(positions(next.snapshot,side).map(i=>i.key));
      const packed=packSide(r,side).packed.filter(key=>keep.has(key));
      next.packing[side]={phase:packed.length===keep.size?'packing_complete':'packing',packed,missingReported:[]};
    }
  }
  freezeSnapshot(next.snapshot);freezeSnapshot(next.dealVersions);freezeSnapshot(next.positionOrder);freezeSnapshot(next.amendment.proposal);
  if (!validVersions(next)) return 'invalid';
  state.requests[id]=next; // One synchronous replacement, one subsequent sessionStorage write.
  return next.amendment.status;
}
