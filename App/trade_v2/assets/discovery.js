// Preview-only dismiss memory, separate from requests and operational capacity.
export const DISMISS_KEY='sammlr-trade-08-dismissed';
export function dismissed(storage){const raw=storage.getItem(DISMISS_KEY);if(!raw)return [];const ids=JSON.parse(raw);if(!Array.isArray(ids)||!ids.every(id=>typeof id==='string'))throw Error('Invalid dismiss state');return ids;}
export function dismiss(storage,id){const ids=dismissed(storage);if(!ids.includes(id))storage.setItem(DISMISS_KEY,JSON.stringify([...ids,id]));}
export function visibleDeals(deals,state,ids){return deals.filter(d=>!ids.includes(d.id)&&!state.requests[d.id]).slice(0,3);}
