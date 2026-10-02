// Trade-v2-specific bilateral contract; no production availability or optimizer logic.
export const CONTRACT='trade-v2-manual-09';
export const allowedAlbum=a=>a.me?.tradeEnabled===true&&a.partner?.tradeEnabled===true;
export const crossAlbum=a=>a.me?.crossAlbum===true&&a.partner?.crossAlbum===true;
export const group=a=>crossAlbum(a)?'open':a.id;
export const eligible=i=>Number.isInteger(i.supply)&&i.supply>0&&Number.isInteger(i.need)&&i.need>0&&Number.isInteger(i.instance)&&i.instance>0;
export const items=(context,side)=>context.albums.filter(allowedAlbum).flatMap(a=>a[side].filter(eligible).map(i=>({...i,albumId:a.id,album:a.title,group:group(a)})));
export const emptyDraft=scenario=>({scenario,receive:[],give:[]});
export const storageKey=slug=>'sammlr-trade-09-draft/'+slug;
export function readDraft(storage,slug,contexts){
  const raw=storage.getItem(storageKey(slug));if(!raw)return emptyDraft('same');
  const d=JSON.parse(raw);if(!d||!Object.hasOwn(contexts,d.scenario)||!['receive','give'].every(side=>Array.isArray(d[side])&&d[side].every(k=>typeof k==='string')&&new Set(d[side]).size===d[side].length))throw Error('Invalid manual draft');return d;
}
export function saveDraft(storage,slug,d){storage.setItem(storageKey(slug),JSON.stringify(d));}
function validKeys(c,d){
  return ['receive','give'].every(side=>Array.isArray(d[side])&&new Set(d[side]).size===d[side].length&&d[side].every(k=>items(c,side).some(i=>i.key===k))&&
    [...new Set(items(c,side).map(i=>i.albumId+'::'+i.code))].every(code=>{
      const chosen=items(c,side).filter(i=>d[side].includes(i.key)&&i.albumId+'::'+i.code===code);
      return !chosen.length||chosen.length<=Math.min(...chosen.map(i=>Math.min(i.supply,i.need)));
    }));
}
export function validate(c,d){
  if(!c||!d||!validKeys(c,d))return {ok:false,message:'Die Auswahl ist nicht mehr verfügbar. Bitte neu auswählen.'};
  if(!d.receive.length||!d.give.length)return {ok:false,message:'Wähle Sticker zum Erhalten und zum Abgeben.'};
  const receive=items(c,'receive').filter(i=>d.receive.includes(i.key)),give=items(c,'give').filter(i=>d.give.includes(i.key));
  for(const key of new Set(receive.map(i=>i.group))){
    if(receive.filter(i=>i.group===key).length>give.filter(i=>i.group===key).length)return {ok:false,message:key==='open'?'Gib noch passende Sticker aus freigegebenen Alben ab.':'Gib noch passende Sticker aus demselben Album ab.'};
  }
  return {ok:true,message:''};
}
export function selectionBlock(c,d,side,key){
  if(!['receive','give'].includes(side)||!validKeys(c,d))return 'Die Auswahl ist nicht mehr verfügbar.';
  if(d[side].includes(key))return '';
  const item=items(c,side).find(i=>i.key===key);if(!item)return 'Dieser Sticker ist für diesen Tausch nicht verfügbar.';
  const same=items(c,side).filter(i=>i.albumId===item.albumId&&i.code===item.code&&d[side].includes(i.key)).length;
  if(same>=Math.min(item.supply,item.need))return 'Diese fehlende Nummer ist bereits berücksichtigt.';
  if(side==='receive'){
    const supply=items(c,'give').filter(i=>i.group===item.group);
    const capacity=[...new Set(supply.map(i=>i.albumId+'::'+i.code))].reduce((n,code)=>{const copies=supply.filter(i=>i.albumId+'::'+i.code===code);return n+Math.min(copies.length,...copies.map(i=>Math.min(i.supply,i.need)));},0);
    const count=items(c,'receive').filter(i=>i.group===item.group&&d.receive.includes(i.key)).length;
    if(count>=capacity)return item.group==='open'?`Für diese Alben sind ${capacity} Sticker möglich. Entferne einen erhaltenen Sticker.`:`Für dieses Album sind ${capacity} Sticker möglich. Entferne einen oder gib einen weiteren passenden Sticker aus diesem Album ab.`;
  }
  return '';
}
export function toggle(c,d,side,key){
  const block=selectionBlock(c,d,side,key);if(block)return block;
  d[side]=d[side].includes(key)?d[side].filter(k=>k!==key):[...d[side],key];return '';
}
export function buildDeal(c,d){
  if(!validate(c,d).ok)return null;
  const groups=side=>c.albums.filter(allowedAlbum).map(a=>({id:a.id,title:a.title,items:a[side].filter(i=>d[side].includes(i.key)).map(({key,code,instance})=>({key,code,instance}))})).filter(a=>a.items.length);
  const receive=groups('receive'),give=groups('give');
  return {id:'manual-'+c.profile_slug,partner_id:c.partner_id,partner:c.partner,partner_slug:'manual-'+c.profile_slug,profile_slug:c.profile_slug,origin:'MANUAL',manualContract:CONTRACT,
    manualTerms:c.albums.filter(allowedAlbum).map(a=>({album:a.id,me:{...a.me},partner:{...a.partner}})),receive,give,receive_count:d.receive.length,give_count:d.give.length,album_count:new Set([...receive,...give].map(a=>a.id)).size};
}
