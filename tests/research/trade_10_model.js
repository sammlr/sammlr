export async function check(deals){
 const {projectTrade,projectOverview}=await import('/trade-v2/assets/overview.js');
 const q=await import('/trade-v2/assets/requests.js'),s=await import('/trade-v2/assets/shipping_demo.js'),a=await import('/trade-v2/assets/amendment_demo.js'),r=await import('/trade-v2/assets/receipt_demo.js');
 const packing=await import('/trade-v2/assets/packing.js'),confirmation=await import('/trade-v2/assets/packing_confirmation.js');
 const receipt=await import('/trade-v2/assets/receipts.js');let assertions=0;
 const ok=(v,message)=>{assertions++;if(!v)throw Error(message);};const now=1000000000;
 const get=(state,deal)=>state.requests[deal.id];
 for(const origin of ['TOP_SUGGESTION','SMARTDEAL','MANUAL']){
  const deal={...structuredClone(deals[0]),origin},state=q.initialState();q.send(state,deal,now);let request=get(state,deal);
  const project=(r,role='sender')=>{const before=JSON.stringify(r),p=projectTrade(r,role,now);ok(JSON.stringify(r)===before,'projection mutates');return p;};
  ok(project(request).group==='waiting','outgoing');ok(project(request,'recipient').group==='incoming','incoming');
  ok(!projectTrade(request,'sender',now+q.DAY),'absolute expiry');ok(request.status==='pending','no expiry write');
  q.decide(state,deal.id,'recipient','accept',now);ok(project(request).label==='Sticker raussuchen','packing');
  for(const role of ['sender','recipient'])ok(project(request,role).href.endsWith('/next?role='+role),'pack exact link');
  request=get(a.amendmentDemo(deal,'proposal',now),deal);
  ok(project(request).group==='waiting','amend proposer');ok(project(request,'recipient').label==='Änderung bestätigen','amend receiver');
  ok(project(request,'recipient').href.endsWith('/amendment?role=recipient'),'amend link');
  request=get(s.shippingDemo(deal,'address',now),deal);confirmation.reportMissing(request,'recipient',[packing.pieces(request,'recipient')[0].key]);ok(project(request).label==='Wartet auf Fehlmengenklärung','partner missing blocks release');ok(project(request,'recipient').label==='Fehlmenge prüfen','own missing');
  request=get(s.shippingDemo(deal,'ready',now),deal);ok(project(request).label==='Versand bestätigen','own shipping');ok(project(request).href.endsWith('/shipping?role=sender&view=prepare'),'shipping exact link');
  request=get(s.shippingDemo(deal,'consent-blocked',now),deal);ok(project(request).group==='waiting','address consent');
  request=get(s.shippingDemo(deal,'me-packing',now),deal);ok(project(request).label==='Wartet auf Versand','other shipping');ok(project(request).receiptHref.endsWith('/receipt?role=sender'),'q2 reachability');
  request=get(r.receiptDemo(deal,'waiting',now),deal);ok(project(request).label==='Empfang bestätigen','receipt');
  request=get(r.receiptDemo(deal,'unchecked',now),deal);ok(project(request).label==='Sendung prüfen','unchecked');
  request=get(r.receiptDemo(deal,'problem',now),deal);ok(project(request).group==='waiting','own problem');ok(project(request,'recipient').label==='Problem klären','partner problem');
  request=get(r.receiptDemo(deal,'resolution-pending',now),deal);ok(project(request).label==='Lösung bestätigen','own confirmation');ok(project(request,'recipient').group==='waiting','resolution wait');
  for(const scenario of ['both-ok','q2-completed','cancelled'])ok(!project(get(r.receiptDemo(deal,scenario,now),deal)),'terminal hidden');
  const declined=q.initialState();q.send(declined,deal,now);q.decide(declined,deal.id,'recipient','decline',now);ok(!project(get(declined,deal)),'declined hidden');
  const q2=r.receiptDemo(deal,'q2-waiting',now);request=get(q2,deal);
  const guard=JSON.stringify([request.shipping,request.ownShipped,request.recipientShipped,q.slots(q2,'outgoing',now),q.incomingSlots(q2,deal.partner_id,now)]);
  ok(receipt.receive(request,'sender',now),'q2 receive');ok(project(request).label==='Sendung prüfen','q2 receipt action');receipt.allReceived(request,'sender',now);
  ok(JSON.stringify([request.shipping,request.ownShipped,request.recipientShipped,q.slots(q2,'outgoing',now),q.incomingSlots(q2,deal.partner_id,now)])===guard,'q2 no shipping/slots');
 }
 const state=q.initialState();for(let i=0;i<3;i++)q.send(state,deals[i],now-i*1000);
 const before=JSON.stringify(state),rows=projectOverview(state,{[deals[0].id]:'recipient'},now);
 ok(rows[0].group==='incoming','group priority');ok(rows[1].id===deals[2].id,'oldest first');ok(JSON.stringify(state)===before,'overview pure');
 const orig=get(state,deals[0]);const projections=['TOP_SUGGESTION','SMARTDEAL','MANUAL'].map(origin=>projectTrade({...orig,origin,snapshot:{...orig.snapshot,origin}},'sender',now));ok(projections.every(p=>JSON.stringify(p)===JSON.stringify(projections[0])),'origin equal');
 return {assertions};
}
