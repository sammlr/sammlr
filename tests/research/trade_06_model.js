export async function check(fixture) {
  const m=await import(location.origin+'/trade-v2/assets/requests.js');
  const p=await import(location.origin+'/trade-v2/assets/packing.js');
  const a=await import(location.origin+'/trade-v2/assets/amendments.js');
  const s=await import(location.origin+'/trade-v2/assets/shipping.js');
  const v=await import(location.origin+'/trade-v2/assets/shipping_state.js');
  const {amendmentDemo}=await import(location.origin+'/trade-v2/assets/amendment_demo.js');
  let assertions=0;const ok=(condition,label)=>{assertions++;if(!condition)throw Error(label);};const json=JSON.stringify;
  const setup=(origin='TOP_SUGGESTION')=>{const state=m.initialState(2,1000),r=m.send(state,{...fixture,origin},1000).request;m.decide(state,r.id,'recipient','accept',1001);p.enterPacking(r,'sender');p.enterPacking(r,'recipient');return {state,r};};
  const pack=(r,role)=>{for(const item of p.pieces(r,role))if(!p.packSide(r,role).packed.includes(item.key))p.togglePiece(r,role,item.key);p.packAction(r,role,'finish');};
  for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL']) for(const first of ['sender','recipient']) {
    const second=first==='sender'?'recipient':'sender';const {state,r}=setup(origin);const snapshot=json(r.snapshot),partnerInitial=json(p.packSide(r,second));
    ok(!s.targetAddress(r,first),'no initial address');ok(!s.releasePacking(r,first),'no incomplete release');
    p.pieces(r,first).slice(0,22).forEach(i=>p.togglePiece(r,first,i.key));
    ok(!p.packAction(r,first,'finish') && !s.targetAddress(r,first),'22 not complete');
    p.togglePiece(r,first,p.pieces(r,first)[22].key);
    ok(!s.targetAddress(r,first) && !s.releasePacking(r,first),'23 marks without approval no address');
    ok(p.packAction(r,first,'finish'),'explicit pack finish');
    ok(v.shippingState(r,first)==='PACKING_COMPLETE' && !s.targetAddress(r,first),'complete distinct from release');
    ok(m.slots(state,'outgoing',2000)===3 && m.incomingSlots(state,fixture.partner_id,2000)===1,'pack keeps both slots');
    ok(s.releasePacking(r,first),'release');ok(v.shippingState(r,first)==='READY_TO_SHIP','ready');
    ok(json(s.targetAddress(r,first))===json(s.demoAddress(r,second)),'exact other address');
    ok(json(s.targetAddress(r,first))!==json(s.demoAddress(r,first)),'never own address');
    ok(!s.targetAddress(r,second),'partner incomplete blocked');
    ok(json(p.packSide(r,second))===partnerInitial,'partner packing unchanged');
    ok(!s.confirmShipment(r,first,1002),'method still unchosen');ok(!s.chooseMethod(r,first,'parcel'),'no new carrier product');
    ok(s.chooseMethod(r,first,'brief'),'existing Brief');
    ok(m.slots(state,'outgoing',2000)===3 && m.incomingSlots(state,fixture.partner_id,2000)===1,'method selection keeps slots');
    ok(!s.confirmShipment(r,'outsider',1003),'unknown role denied');
    ok(s.confirmShipment(r,first,1003),'own explicit shipping');
    ok(v.shippingState(r,first)==='SHIPPED' && v.shippingState(r,second)==='PACKING','one direction only');
    ok(!v.bothShipped(r) && r.status==='accepted','not both or completed');
    ok(m.slots(state,'outgoing',2000)===(first==='sender'?2:3),'own outgoing projection');
    ok(m.incomingSlots(state,fixture.partner_id,2000)===(first==='recipient'?0:1),'own incoming projection');
    const shipped=json(r);
    for(let i=0;i<20;i++)s.confirmShipment(r,first,1004+i);
    ok(json(r)===shipped,'repeated shipping no mutation or time change');
    ok(!p.togglePiece(r,first,p.pieces(r,first)[0].key),'shipped markers frozen');
    for(const action of ['finish','review','report','back'])ok(!p.packAction(r,first,action),'no pack edits after own shipped');
    ok(!s.reopenPacking(r,first),'cannot reopen shipped');
    ok(!s.chooseMethod(r,first,null),'cannot unchoose shipped method');
    ok(json(r)===shipped,'own editing attempts no mutation');
    ok(p.togglePiece(r,second,p.pieces(r,second)[0].key),'other packing remains editable');
    pack(r,second);s.releasePacking(r,second);s.chooseMethod(r,second,'brief');
    ok(v.shippingState(r,second)==='READY_TO_SHIP','other ready independently');
    const firstRecord=json(r.shipping[first]);s.confirmShipment(r,second,1100);
    ok(v.bothShipped(r) && r.status==='accepted','both shipped still active');
    ok(json(r.shipping[first])===firstRecord,'second ship preserves first time');
    ok(m.slots(state,'outgoing',2000)===2 && m.incomingSlots(state,fixture.partner_id,2000)===0,'both individual slots free once');
    ok(json(r.snapshot)===snapshot && r.deal_version===1,'deal content/version unchanged');
    const read=m.readState({getItem:()=>json(state)});ok(v.bothShipped(read.requests[r.id]),'reload preserves both');
    ok(Object.keys(state.requests).length===3,'no second trade');
  }
  const {r:consent}=setup();pack(consent,'sender');s.releasePacking(consent,'sender');consent.demoAddressConsent={recipient:false};
  ok(!s.targetAddress(consent,'sender'),'separate owner consent');ok(!s.chooseMethod(consent,'sender','brief') && !s.confirmShipment(consent,'sender',2000),'consent protects commands');
  delete consent.demoAddressConsent;ok(s.targetAddress(consent,'sender'),'explicit fictional fixture consent');
  s.chooseMethod(consent,'sender','brief');ok(s.reopenPacking(consent,'sender'),'reopen before ship');
  ok(!s.targetAddress(consent,'sender') && consent.shipping.sender.method===null && consent.packing.sender.packed.length===23,'reopen clears release, preserves marks');
  ok(p.togglePiece(consent,'sender',p.pieces(consent,'sender')[0].key),'reopened pack editable');
  // V2's automatically complete intersection still needs conscious release of that version.
  const state2=amendmentDemo(fixture,'accepted',1000),r2=state2.requests[fixture.id];
  ok(r2.deal_version===2 && p.pieces(r2,'sender').length===21,'V2 21 positions');
  ok(!s.targetAddress(r2,'sender'),'V2 no implicit address release');
  ok(s.releasePacking(r2,'sender') && s.targetAddress(r2,'sender'),'V2 conscious release');
  s.chooseMethod(r2,'sender','brief');const versions=json(r2.dealVersions);s.confirmShipment(r2,'sender',2000);
  ok(v.ownShipped(r2,'sender') && json(r2.dealVersions)===versions,'V2 ship preserves history');
  ok(p.packSide(r2,'recipient').packed.length===11,'V2 partner progress untouched');
  p.packAction(r2,'recipient','review');p.packAction(r2,'recipient','report');const afterReport=json(r2);
  ok(a.proposeAmendment(r2,'recipient',2001)==='shipped' && json(r2)===afterReport,'amendment blocked after actual shipment');
  // A pending amendment locks an already released address; acceptance requires new release.
  const {state:amendState,r:amend}=setup();pack(amend,'recipient');s.releasePacking(amend,'recipient');s.chooseMethod(amend,'recipient','brief');
  p.pieces(amend,'sender').slice(0,21).forEach(i=>p.togglePiece(amend,'sender',i.key));p.packAction(amend,'sender','review');p.packAction(amend,'sender','report');a.proposeAmendment(amend,'sender',1002);
  ok(!s.targetAddress(amend,'recipient') && !s.confirmShipment(amend,'recipient',1003),'pending blocks address and shipment');
  a.decideAmendment(amendState,amend.id,'recipient','accept',1004);const revised=amendState.requests[amend.id];
  ok(revised.shipping.recipient.releasedVersion===null && !s.targetAddress(revised,'recipient'),'V2 invalidates V1 release');
  ok(s.releasePacking(revised,'recipient') && revised.shipping.recipient.releasedVersion===2,'fresh release of 21');
  revised.shipping.recipient.releasedVersion=1;
  ok(!v.validShipping(revised) && !s.confirmShipment(revised,'recipient',1005),'stale version fails closed');
  let rejected=false;try{m.readState({getItem:()=>json(amendState)});}catch(_){rejected=true;}ok(rejected,'invalid persisted shipping rejected');
  for(const first of ['sender','recipient']) {
    const {r}=setup();pack(r,first);s.releasePacking(r,first);s.chooseMethod(r,first,'brief');s.confirmShipment(r,first,1003);
    const other=first==='sender'?'recipient':'sender';p.packAction(r,other,'review');p.packAction(r,other,'report');const original=json(r);
    ok(a.proposeAmendment(r,other,1004)==='shipped' && json(r)===original,'either physical direction blocks amendment');
  }
  return {assertions,result:'PASS',coverage:'V1/V2, both roles/origins, own approval + owner consent, directional shipping, frozen own packing, independent partner, derived slots, idempotency, version invalidation, amendment lock, no completion'};
}
