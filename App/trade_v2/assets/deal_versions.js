// Pure snapshot/version helpers. No catalog, optimizer, DOM order or production service.
export const ROLES = ['sender', 'recipient'];
export const opposite = role => role === 'sender' ? 'recipient' : 'sender';
export const version = request => request.deal_version ?? 1;
export const shipped = request => Boolean(request.ownShipped || request.recipientShipped);
export function freezeSnapshot(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(freezeSnapshot);Object.freeze(value);
  }
  return value;
}
export function positions(snapshot, role) {
  const albums = role === 'sender' ? snapshot.give : snapshot.receive;
  return albums.flatMap(a=>a.items.map(item=>({...item, album:a.title, albumId:a.id})))
    .map((item,index)=>({...item, index:index+1, positionId:`${snapshot.id}/${role}/${index+1}`}));
}
export function reduction(snapshot, proposer, keys) {
  if (!ROLES.includes(proposer) || !Array.isArray(keys) || !keys.length || new Set(keys).size !== keys.length) return null;
  const own=positions(snapshot,proposer), counter=positions(snapshot,opposite(proposer));
  if (!keys.every(k=>own.some(i=>i.key===k))) return null;
  const indexes=own.filter(i=>keys.includes(i.key)).map(i=>i.index);
  if (indexes.some(index=>!counter[index-1])) return null; // Never invent another counter-position.
  const removed={sender:positions(snapshot,'sender').filter(i=>indexes.includes(i.index)),recipient:positions(snapshot,'recipient').filter(i=>indexes.includes(i.index))};
  const next=structuredClone(snapshot);
  for (const [role,side] of [['sender','give'],['recipient','receive']]) {
    const removedKeys=new Set(removed[role].map(i=>i.key));
    next[side]=next[side].map(a=>({...a,items:a.items.filter(i=>!removedKeys.has(i.key))})).filter(a=>a.items.length);
    next[side+'_count']=next[side].reduce((n,a)=>n+a.items.length,0);
  }
  next.album_count=new Set([...next.give,...next.receive].map(a=>a.id)).size;
  return {indexes,removed,snapshot:next,continuable:next.give_count>0 && next.receive_count>0};
}
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function validVersions(r) {
  if (![1,2].includes(version(r))) return false;
  if (!r.amendment) return version(r)===1 && !r.dealVersions && !r.positionOrder && r.status!=='cancelled';
  const a=r.amendment, history=r.dealVersions, original=history?.[0]?.snapshot;
  if (!original || history[0].version!==1 || !ROLES.includes(a.proposer) || a.id!==`${r.id}/amendment/1`
      || a.baseVersion!==1 || !Number.isFinite(a.proposedAt) || !['pending','accepted','cancelled'].includes(a.status)) return false;
  if (!equal(r.positionOrder,{sender:positions(original,'sender'),recipient:positions(original,'recipient')})) return false;
  const expected=reduction(original,a.proposer,a.missingKeys);
  if (!expected || !equal(a.proposal,expected)) return false;
  if (a.status==='accepted') return r.status==='accepted' && version(r)===2 && history.length===2
    && history[1].version===2 && equal(history[1].snapshot,expected.snapshot) && equal(r.snapshot,expected.snapshot)
    && a.acceptedBy===opposite(a.proposer) && Number.isFinite(a.decidedAt) && expected.continuable;
  if (version(r)!==1 || history.length!==1 || !equal(r.snapshot,original)) return false;
  return a.status==='pending' ? r.status==='accepted' && equal(r.packing?.[a.proposer]?.missingReported,a.missingKeys) : r.status==='cancelled' && a.cancelledBy===opposite(a.proposer) && Number.isFinite(a.decidedAt);
}
