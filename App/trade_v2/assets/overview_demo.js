// Explicit QA scenarios. Uses existing commands; role metadata is not a domain field.
import {initialState,send,decide} from './requests.js';
import {shippingDemo} from './shipping_demo.js';
import {receiptDemo} from './receipt_demo.js';
import {amendmentDemo} from './amendment_demo.js';
export const ROLE_KEY='sammlr-trade-10-preview-roles';
export const SCENARIOS=['mixed','incoming','action','waiting','amendment','amendment-wait','shipping','receipt','problem','problem-wait','q2','empty'];
export function overviewDemo(deals,scenario,now=Date.now()){
  const state=initialState(),roles={};
  const add=(deal,type,role='sender')=>{
    const at=now-60*60*1000*(Object.keys(state.requests).length+1);let source;
    if(['incoming','waiting','packing'].includes(type)){
      source=initialState();send(source,deal,at);if(type==='packing')decide(source,deal.id,'recipient','accept',at);
    }else if(type==='amendment')source=amendmentDemo(deal,'proposal',at);
    else if(type==='shipping')source=shippingDemo(deal,'ready',at);
    else if(type==='transit')source=shippingDemo(deal,'me-packing',at);
    else source=receiptDemo(deal,type==='q2'?'q2-waiting':type==='receipt'?'waiting':'problem',at);
    state.requests[deal.id]=source.requests[deal.id];roles[deal.id]=role;
  };
  if(scenario==='mixed'){
    add(deals[0],'incoming','recipient');add(deals[1],'packing');add(deals[2],'shipping');
    add(deals[3],'amendment');add(deals[4],'transit');add(deals[5],'problem','recipient');
  }else if(scenario!=='empty'){
    const type={action:'packing','amendment-wait':'amendment','problem-wait':'problem'}[scenario]||scenario;
    add(deals[0],type,['incoming','amendment','problem'].includes(scenario)?'recipient':'sender');
  }
  return {state,roles};
}
