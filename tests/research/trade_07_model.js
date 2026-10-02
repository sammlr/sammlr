export async function check(fixture) {
  const base=location.origin+'/trade-v2/assets/';
  const req=await import(base+'requests.js'),model=await import(base+'receipts.js'),rs=await import(base+'receipt_state.js'),pack=await import(base+'packing.js'),ship=await import(base+'shipping.js'),ss=await import(base+'shipping_state.js'),amend=await import(base+'amendments.js');
  const {receiptDemo}=await import(base+'receipt_demo.js'),{amendmentDemo}=await import(base+'amendment_demo.js');
  let assertions=0;const assert=(ok,label)=>{assertions++;if(!ok)throw Error(label);};
  const clone=x=>structuredClone(x),json=JSON.stringify;
  const now=Date.now();
  const guard=r=>json({snapshot:r.snapshot,history:r.dealVersions,version:r.deal_version,packing:r.packing,shipping:r.shipping,own:r.ownShipped,other:r.recipientShipped,status:r.status});
  const slots=(s,r)=>json([req.slots(s,'outgoing',now),req.incomingSlots(s,r.snapshot.partner_id,now)]);
  const reload=s=>req.readState({getItem:()=>json(s)});
  const readonly=(r,call,label)=>{const before=json(r);assert(!call(),label);assert(json(r)===before,label+' unchanged');};
  for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL'])for(const version of [1,2])for(const role of ['sender','recipient']) {
    const other=role==='sender'?'recipient':'sender',f={...clone(fixture),origin};
    const state=receiptDemo(f,version===1?'waiting':'completed-v2',now),r=state.requests[f.id];
    if(version===2){delete r.receipts;delete r.completedAt;delete r.ratings;}
    const frozen=guard(r),slotBefore=slots(state,r);
    assert(rs.expectedPositions(r,role).length===(version===1?23:21),'active expected count');
    assert(rs.expectedPositions(r,role).every(i=>r.snapshot[role==='sender'?'receive':'give'].flatMap(a=>a.items).some(p=>p.key===i.key)),'receiving role reversed');
    readonly(r,()=>model.rate(r,role,3,now),'rating before completion');
    readonly(r,()=>model.receive(r,'stranger',now),'nonparticipant receive');
    assert(model.receive(r,role,now),'receive');assert(rs.receiptSide(r,role).state==='RECEIVED_UNCHECKED','unchecked');
    readonly(r,()=>model.receive(r,role,now),'receive retry');
    readonly(r,()=>model.reportProblem(r,role,['missing'],['fantasy'],now),'invented position');
    readonly(r,()=>model.reportProblem(r,role,['missing'],[],now),'missing needs position');
    readonly(r,()=>model.reportProblem(r,role,[],[],now),'needs type');
    readonly(r,()=>model.reportProblem(r,role,['unknown'],[],now),'unknown type');
    readonly(r,()=>model.reportProblem(r,role,['missing','missing'],[],now),'duplicate types');
    const ids=rs.expectedPositions(r,role).slice(0,2).map(i=>i.positionId);
    const alternative=clone(r);assert(model.allReceived(alternative,role,now),'all OK wins');readonly(alternative,()=>model.reportProblem(alternative,role,['missing'],ids,now),'late problem loses');
    assert(model.reportProblem(r,role,['missing','damaged'],ids,now),'multiple positions and types');
    assert(rs.receiptSide(r,other).state==='WAITING','other unchanged');
    assert(json(reload(state).requests[f.id].receipts)===json(r.receipts),'problem reload');
    readonly(r,()=>model.allReceived(r,role,now),'all OK loses to problem');readonly(r,()=>model.reportProblem(r,role,['wrong'],ids,now),'problem retry');
    readonly(r,()=>model.proposeResolution(r,role,role,now),'reporter cannot self propose');
    readonly(r,()=>model.confirmResolution(r,role,now),'cannot confirm before proposal');
    assert(model.proposeResolution(r,other,role,now),'counterpart proposes');assert(rs.receiptSide(r,role).state==='RESOLUTION_PENDING','not resolved unilaterally');
    readonly(r,()=>model.proposeResolution(r,other,role,now),'proposal retry');readonly(r,()=>model.confirmResolution(r,other,now),'counterpart cannot confirm');
    assert(model.confirmResolution(r,role,now),'reporter confirms');readonly(r,()=>model.confirmResolution(r,role,now),'confirm retry');
    assert(rs.receiptSide(r,role).state==='RESOLVED'&&!rs.completed(r),'one final not complete');
    assert(model.receive(r,other,now)&&model.allReceived(r,other,now),'other OK');assert(rs.completed(r)&&r.completedAt===now,'complete mixed final');
    readonly(r,()=>model.allReceived(r,other,now),'all OK retry');readonly(r,()=>model.receive(r,role,now),'no backwards');
    assert(guard(r)===frozen&&slots(state,r)===slotBefore,'all receipt/problem/completion fields leave physical package and slots untouched');
    assert(!r.ratings,'no auto rating');
    for(const value of [0,4,5,1.5,null,'3',true])readonly(r,()=>model.rate(r,role,value,now),'invalid rating '+value);
    for(const stars of [1,2,3]){const c=clone(r);assert(model.rate(c,role,stars,now),'valid '+stars);assert(c.ratings[role].forRole===other&&c.ratings[role].stars===stars&&!c.ratings[other],'partner rating independent');readonly(c,()=>model.rate(c,role,stars===3?1:3,now),'rating immutable');}
    assert(model.rate(r,role,3,now)&&model.rate(r,other,1,now),'both rate independently');assert(rs.completed(reload(state).requests[f.id]),'completed survives reload');
    const bad=clone(r);bad.ratings[role].forRole=role;assert(!rs.validReceipt(bad),'self rating invalid on read');
    const bad2=clone(r);bad2.receipts[role].version=99;assert(!rs.validReceipt(bad2),'receipt wrong version rejected');
    const bad3=clone(r);bad3.receipts[role].problem.positionIds=['invented'];assert(!rs.validReceipt(bad3),'problem corruption rejected');
  }
  // Q2: PACKING and READY_TO_SHIP are both valid partner states, with no fabricated shipment.
  for(const scenario of ['locked','address','me-ready'])for(const role of ['sender','recipient']) {
    const {shippingDemo}=await import(base+'shipping_demo.js'),s=shippingDemo(fixture,scenario,now),r=s.requests[fixture.id];
    const before=guard(r),beforeSlots=slots(s,r);
    assert(model.receive(r,role,now),'Q2 actual receipt');
    const ids=rs.expectedPositions(r,role).slice(0,1).map(i=>i.positionId);
    assert(model.reportProblem(r,role,['wrong'],ids,now),'Q2 problem');
    const other=role==='sender'?'recipient':'sender';assert(model.proposeResolution(r,other,role,now)&&model.confirmResolution(r,role,now),'Q2 solution');
    assert(guard(r)===before&&slots(s,r)===beforeSlots,'Q2 shipping timestamps flags and slots unchanged');
    assert(rs.validReceipt(reload(s).requests[fixture.id]),'Q2 reload');
    assert(amend.proposalBlock(r,role)==='shipped','physical receipt blocks later amendment');
  }
  const q=receiptDemo(fixture,'q2-completed',now),r=q.requests[fixture.id];
  assert(rs.completed(r)&&!r.ownShipped&&!r.recipientShipped,'both receipts can complete without shipping clicks');
  assert(req.slots(q,'outgoing',now)===3&&req.incomingSlots(q,r.snapshot.partner_id,now)===1,'completion does not free slots');
  assert(model.rate(r,'sender',3,now),'Q2 completed rating');
  for(const role of ['sender','recipient']){
    pack.enterPacking(r,role);for(const i of pack.pieces(r,role))if(!pack.packSide(r,role).packed.includes(i.key))pack.togglePiece(r,role,i.key);
    if(pack.packSide(r,role).phase!=='packing_complete')pack.packAction(r,role,'finish');
    ship.releasePacking(r,role);ship.chooseMethod(r,role,'brief');assert(ship.confirmShipment(r,role,now+1),'later own shipping permitted');
  }
  assert(req.slots(q,'outgoing',now)===2&&req.incomingSlots(q,r.snapshot.partner_id,now)===0,'only own confirmations free slots');
  assert(rs.completed(r)&&rs.validReceipt(r)&&r.ratings.sender.stars===3,'late shipping preserves completion and rating');
  const cancelled=receiptDemo(fixture,'cancelled',now).requests[fixture.id];readonly(cancelled,()=>model.receive(cancelled,'sender',now),'cancelled receive');readonly(cancelled,()=>model.rate(cancelled,'sender',3,now),'cancelled rating');
  const pending=amendmentDemo(fixture,'waiting',now),p=pending.requests[fixture.id];
  assert(model.receive(p,'sender',now),'actual receipt during pending amendment');const snap=json(p.snapshot);
  assert(amend.decideAmendment(pending,p.id,'recipient','accept',now)==='shipped','pending acceptance blocked after actual receipt');
  assert(amend.decideAmendment(pending,p.id,'recipient','cancel',now)==='shipped','pending cancellation blocked after actual receipt');assert(json(p.snapshot)===snap,'snapshot not rewritten');
  return {assertions,origins:3,versions:2,roles:2,q2_shipping_and_slots:'PASS',problem_races_ratings_validation:'PASS'};
}
