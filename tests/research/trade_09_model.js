export async function check(contexts){
 const m=await import('/trade-v2/assets/manual_rules.js');let assertions=0;
 const ok=(v,msg)=>{assertions++;if(!v)throw Error(msg);};
 const pick=(c,side,album,n)=>m.items(c,side).filter(i=>i.albumId===album).slice(0,n).map(i=>i.key);
 for(const name of ['same','one-sided']){
  const c=contexts[name],d=m.emptyDraft(name),r=pick(c,'receive','wm06',4),g=pick(c,'give','wm06',3);
  r.slice(0,3).forEach(k=>ok(!m.toggle(c,d,'receive',k),'receive potential'));
  ok(!!m.toggle(c,d,'receive',r[3]),'fourth blocked');ok(d.receive.length===3,'no eviction');ok(!m.validate(c,d).ok,'give required');
  g.forEach(k=>m.toggle(c,d,'give',k));ok(m.validate(c,d).ok,'3/3');
  m.toggle(c,d,'receive',r[0]);ok(!m.toggle(c,d,'receive',r[3]),'removal reopens');
  m.toggle(c,d,'give',g[0]);ok(!m.validate(c,d).ok,'3/2 invalid');m.toggle(c,d,'receive',r[1]);ok(m.validate(c,d).ok,'2/2');m.toggle(c,d,'give',g[0]);ok(m.validate(c,d).ok,'2/3 allowed');
  ok(!!m.selectionBlock(c,m.emptyDraft(name),'receive',pick(c,'receive','em04',1)[0]),'no counterpart');
  ok(!m.validate(c,{scenario:name,receive:r.slice(0,3),give:pick(c,'give','buli07',5)}).ok,'restricted cannot pool');
 }
 const c=contexts.open,d={scenario:'open',receive:[...pick(c,'receive','wm06',3),...pick(c,'receive','em04',2)],give:pick(c,'give','buli07',5)};
 ok(m.validate(c,d).ok,'bilateral pooled offer');const deal=m.buildDeal(c,d);ok(deal.receive_count===5&&deal.give_count===5&&deal.album_count===3,'snapshot');
 for(const side of ['me','partner'])for(const id of ['wm06','em04','buli07'])for(const flag of ['crossAlbum','tradeEnabled']){
  const copy=structuredClone(c);copy.albums.find(a=>a.id===id)[side][flag]=false;ok(!m.validate(copy,d).ok,`${side}/${id}/${flag}`);
 }
 const smart=structuredClone(c);smart.albums.forEach(a=>{a.me.smartEnabled=false;a.partner.smartEnabled=false;});ok(m.validate(smart,d).ok,'manual independent of smart');
 for(const field of ['need','supply'])for(const value of [0,-1,1.5,true]){const copy=structuredClone(c);copy.albums[0].receive[0][field]=value;ok(!m.validate(copy,d).ok,'invalid availability');}
 for(const bad of [{receive:[],give:[]},{receive:['fake'],give:d.give},{receive:d.receive,give:[...d.give,d.give[0]]}])ok(!m.buildDeal(c,bad),'invalid cannot bind');
 return {assertions};
}
