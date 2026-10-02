// Loaded by the browser gate; production modules remain the actual units under test.
export async function check(fixture) {
  const m=await import(location.origin+'/trade-v2/assets/requests.js');
  const p=await import(location.origin+'/trade-v2/assets/packing.js');
  const a=await import(location.origin+'/trade-v2/assets/amendments.js');
  const v=await import(location.origin+'/trade-v2/assets/deal_versions.js');
  let assertions=0;
  const ok=(condition,label)=>{assertions++;if(!condition)throw Error(label);};
  const json=JSON.stringify;
  const setup=(deal=fixture,role='sender',indexes=[22,23],counterPacked=[])=>{
    const state=m.initialState(2,1000),r=m.send(state,deal,1000).request;
    m.decide(state,r.id,'recipient','accept',1001);p.enterPacking(r,'sender');p.enterPacking(r,'recipient');
    p.pieces(r,role).forEach((item,i)=>{if(!indexes.includes(i+1))p.togglePiece(r,role,item.key);});
    counterPacked.forEach(i=>p.togglePiece(r,v.opposite(role),p.pieces(r,v.opposite(role))[i-1].key));
    p.packAction(r,role,'review');p.packAction(r,role,'report');return {state,r};
  };
  for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL']) for(const proposer of ['sender','recipient']){
    const {state,r}=setup({...fixture,origin},proposer);
    const original=json(r.snapshot),missing=p.packSide(r,proposer).missingReported.slice();
    ok(r.deal_version===1 && r.snapshot.give_count===23,'missing report preserves V1');
    ok(a.proposeAmendment(r,proposer,1002)==='pending','create pending');
    ok(json(r.snapshot)===original,'pending snapshot unchanged');
    ok(r.amendment.proposal.snapshot.give_count===21 && r.amendment.proposal.snapshot.receive_count===21,'balanced 21');
    ok(json(r.amendment.proposal.removed[proposer].map(i=>i.key))===json(missing),'exact missing IDs');
    ok(json(r.amendment.proposal.indexes)==='[22,23]','original ordinal pair');
    ok(json(r.amendment.proposal.removed[v.opposite(proposer)].map(i=>i.key))===json(p.pieces(r,v.opposite(proposer)).slice(-2).map(i=>i.key)),'exact counter IDs');
    const pending=json(r);a.proposeAmendment(r,proposer,9999);ok(json(r)===pending,'proposal retry stable');
    ok(!p.togglePiece(r,v.opposite(proposer),p.pieces(r,v.opposite(proposer))[0].key),'pending packing frozen');
    ok(a.decideAmendment(state,r.id,proposer,'accept',1003)==='forbidden','no self accept');
    ok(a.decideAmendment(state,r.id,'outsider','cancel',1003)==='forbidden','no third role');
    ok(a.decideAmendment(state,r.id,v.opposite(proposer),'accept',1003,'wrong-id')==='stale','stale command');
    ok(json(state.requests[r.id])===pending,'denied actions unchanged');
    ok(a.decideAmendment(state,r.id,v.opposite(proposer),'accept',1004)==='accepted','other party accept');
    const active=state.requests[r.id];
    ok(active.deal_version===2 && active.dealVersions.length===2,'one active V2');
    ok(active.snapshot===active.dealVersions[1].snapshot,'same active history reference');
    ok(json(active.dealVersions[0].snapshot)===original,'V1 retained byte equivalent');
    ok(Object.isFrozen(active.snapshot.give[0].items[0]) && Object.isFrozen(active.dealVersions[0].snapshot),'both versions immutable');
    ok(p.pieces(active,proposer).length===21 && p.packSide(active,proposer).packed.length===21,'reporter 21/21');
    ok(p.packSide(active,proposer).phase==='packing_complete','reporter complete');
    ok(p.pieces(active,v.opposite(proposer)).length===21 && p.packSide(active,v.opposite(proposer)).packed.length===0,'other packlist independent');
    const sender=m.perspective(active,'sender'),recipient=m.perspective(active,'recipient');
    ok(sender.give===recipient.receive && sender.receive===recipient.give,'exact mirrored identities');
    ok(m.slots(state,'outgoing',2000)===3 && m.incomingSlots(state,fixture.partner_id,2000)===1,'accept keeps both slots');
    ok(Object.keys(state.requests).length===3,'no second trade');
    const accepted=json(active);
    for(let i=0;i<10;i++)a.decideAmendment(state,r.id,v.opposite(proposer),i%2?'cancel':'accept',2000+i);
    ok(json(state.requests[r.id])===accepted,'accept then cancel/repeated accept stable');
    m.expire(state,1000+2*m.DAY);ok(state.requests[r.id].status==='accepted','no new request deadline');
    const storage={getItem:()=>json(state)};
    const read=m.readState(storage);ok(read.requests[r.id].deal_version===2 && Object.isFrozen(read.requests[r.id].snapshot),'reload V2 frozen');
  }
  for(const [counter,expected] of [[Array.from({length:12},(_,i)=>i+1),12],[[...Array.from({length:11},(_,i)=>i+1),22],11],[[...Array.from({length:10},(_,i)=>i+1),22,23],10]]){
    const {state,r}=setup(fixture,'sender',[22,23],counter);a.proposeAmendment(r,'sender',1002);
    const before=p.packSide(r,'recipient').packed.slice();a.decideAmendment(state,r.id,'recipient','accept',1003);
    const active=state.requests[r.id],kept=new Set(p.pieces(active,'recipient').map(i=>i.key));
    ok(p.packSide(active,'recipient').packed.length===expected,'12/11/10 by actual positions');
    ok(json(p.packSide(active,'recipient').packed)===json(before.filter(k=>kept.has(k))),'marks exact intersection');
    p.packAction(active,'recipient','review');p.packAction(active,'recipient','report');
    const unchanged=json(active);ok(a.proposeAmendment(active,'recipient',2000)==='further_change','one round boundary');
    ok(json(active)===unchanged && active.deal_version===2,'second report does not create V3');
  }
  for(const proposer of ['sender','recipient']){
    const {state,r}=setup(fixture,proposer);a.proposeAmendment(r,proposer,1002);const original=json(r.snapshot);
    ok(a.decideAmendment(state,r.id,v.opposite(proposer),'cancel',1003)==='cancelled','cancel');
    const cancelled=json(state.requests[r.id]);
    for(const command of ['cancel','accept','cancel'])a.decideAmendment(state,r.id,v.opposite(proposer),command,1004);
    ok(json(state.requests[r.id])===cancelled,'cancel then accept stable');
    ok(state.requests[r.id].status==='cancelled' && json(state.requests[r.id].snapshot)===original,'whole trade ended, history intact');
    ok(m.slots(state,'outgoing',2000)===2 && m.incomingSlots(state,fixture.partner_id,2000)===0,'both operative slots released');
    ok(m.readState({getItem:()=>json(state)}).requests[r.id].status==='cancelled','cancel reload');
  }
  for(const field of ['ownShipped','recipientShipped']) for(const timing of ['before','after']) {
    const {state,r}=setup();if(timing==='after')a.proposeAmendment(r,'sender',1002);r[field]=true;
    const original=json(state);
    if(timing==='before')ok(a.proposeAmendment(r,'sender',1003)==='shipped','shipped blocks creation');
    else for(const action of ['accept','cancel'])ok(a.decideAmendment(state,r.id,'recipient',action,1003)==='shipped','shipped blocks decision');
    ok(json(state)===original,'shipped state not mutated');
  }
  const {state:emptyState,r:empty}=setup(fixture,'sender',Array.from({length:23},(_,i)=>i+1));
  a.proposeAmendment(empty,'sender',1002);ok(!empty.amendment.proposal.continuable,'empty not continuable');
  ok(a.decideAmendment(emptyState,empty.id,'recipient','accept',1003)==='empty','no zero active deal');
  ok(emptyState.requests[empty.id].deal_version===1,'empty remains unbound proposal');
  a.decideAmendment(emptyState,empty.id,'recipient','cancel',1004);ok(m.slots(emptyState,'outgoing',2000)===2,'empty cancel frees slot');
  const {state:smallState,r:small}=setup(fixture,'sender',Array.from({length:22},(_,i)=>i+1));
  a.proposeAmendment(small,'sender',1002);a.decideAmendment(smallState,small.id,'recipient','accept',1003);
  ok(smallState.requests[small.id].snapshot.give_count===1,'no invented amendment minimum; initial automatic min5 unchanged');
  // Existing physical instances are separate positions; no change to generator Need rules.
  const copies=structuredClone(fixture);
  for(const side of ['give','receive']) {
    const album=copies[side][0],item=album.items[0];
    copies[side]=[{...album,items:Array.from({length:37},(_,i)=>({...item,key:`${item.key}/copy/${i+1}`,instance:i+1}))}];copies[side+'_count']=37;
  }
  copies.album_count=1;
  const {state:copyState,r:copy}=setup(copies,'sender',[3,37]);a.proposeAmendment(copy,'sender',1002);
  ok(json(copy.amendment.proposal.indexes)==='[3,37]','original positions 3 and 37');
  a.decideAmendment(copyState,copy.id,'recipient','accept',1003);
  ok(copyState.requests[copy.id].snapshot.give_count===35,'only two copies removed');
  ok(p.pieces(copyState.requests[copy.id],'sender').some(i=>i.instance===2) && !p.pieces(copyState.requests[copy.id],'sender').some(i=>i.instance===3),'instance-specific removal');
  const {r:damaged}=setup();a.proposeAmendment(damaged,'sender',1002);
  const altered=structuredClone(damaged);altered.amendment.proposal.removed.recipient[0].key='invented';
  ok(!v.validVersions(altered),'tampered counter rejected');
  let rejected=false;try{m.readState({getItem:()=>json({version:1,requests:{[altered.id]:altered}})});}catch(_){rejected=true;}
  ok(rejected,'tampered persisted proposal fails closed');
  const {r:both}=setup();p.packAction(both,'recipient','review');p.packAction(both,'recipient','report');
  ok(a.proposeAmendment(both,'sender',1002)==='both_reported','concurrent missing reports not silently merged');
  return {assertions,result:'PASS',coverage:'both roles, all origins, missing IDs, original ordinals, copies, V1/V2, marks, races, slots, shipped, empty, second report, tampered storage'};
}
