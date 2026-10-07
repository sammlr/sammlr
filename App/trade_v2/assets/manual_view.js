import {stickerListWriteCeoklaue as ink,listItem,bracket} from './manual_ink.js';
import {allowedAlbum,items,emptyDraft,readDraft,saveDraft,toggle,selectionBlock,validate} from './manual_rules.js';
const data=JSON.parse(document.getElementById('trade-data').textContent),slug=data.partner.slug,$=id=>document.getElementById(id),url=new URL(location.href);
const readState=data.live?()=>({requests:{}}):(await import('./requests.js')).readState;
let draft,context;
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text)ink(n,text,'manual-'+text);if(cls)n.className=cls;return n;};
ink($('manual-title'),`Tausch mit ${data.partner.display_name}`,'manual-title');ink($('manual-note-title'),'Aktueller Tausch','manual-note');bracket($('manual-review'),'Auswahl prüfen');
try{
  const scenario=url.searchParams.get('manual');
  if(Object.hasOwn(data.contexts,scenario)){draft=emptyDraft(scenario);saveDraft(sessionStorage,slug,draft);url.searchParams.delete('manual');history.replaceState(null,'',url);}else draft=readDraft(sessionStorage,slug,data.contexts);
  context=data.contexts[draft.scenario];
  const existing=readState(sessionStorage).requests['manual-'+slug];
  if(existing){$('manual-existing').hidden=false;$('manual-existing').href='/trade-v2/requests/manual-'+slug;}
  for(const album of context.albums.filter(allowedAlbum)){
    const article=node('article',undefined,'manual-album');article.dataset.album=album.id;article.append(node('h2',album.title));
    for(const side of ['receive','give']){
      const section=node('section',undefined,'sticker-list-section');section.append(node('h3',side==='receive'?'Du bekommst':'Du gibst ab'));
      const grid=node('div',undefined,'sticker-list-grid'),all=items(context,side).filter(i=>i.albumId===album.id);
      all.forEach((item,index)=>{
        const entry=listItem(item,side==='receive'?'get':'give',album.id,index<all.length-1),button=entry.querySelector('button');button.dataset.side=side;
        button.addEventListener('click',()=>{
          try{const latest=readDraft(sessionStorage,slug,data.contexts);if(latest.scenario!==draft.scenario){$('manual-status').textContent='Die Auswahl wurde geändert. Bitte lade die Seite neu.';return;}
            const error=toggle(context,latest,side,item.key);if(!error){saveDraft(sessionStorage,slug,latest);draft=latest;}update(error);if(error){button.closest('.sticker-list-grid').after($('manual-status'));$('manual-status').scrollIntoView({block:'nearest'});}
          }catch(_){$('manual-status').textContent='Die Auswahl konnte nicht lokal gespeichert werden.';}
        });grid.append(entry);
      });
      if(!all.length)grid.append(node('p','Keine passenden Sticker.','sticker-list-empty'));section.append(grid);article.append(section);
    }$('manual-albums').append(article);
  }
  function update(message=''){
    document.querySelectorAll('.sticker-list-item').forEach(b=>{const selected=draft[b.dataset.side].includes(b.dataset.key);b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));b.setAttribute('aria-disabled',String(!selected&&Boolean(selectionBlock(context,draft,b.dataset.side,b.dataset.key))));});
    $('manual-summary').replaceChildren(node('span',`${draft.receive.length} erhalten`),node('span',`${draft.give.length} abzugeben`));
    const result=validate(context,draft);$('manual-review').disabled=!result.ok||Boolean(existing);$('manual-status').textContent=message||(result.ok?'':result.message);
  }
  $('manual-clear').addEventListener('click',()=>{try{draft=emptyDraft(draft.scenario);saveDraft(sessionStorage,slug,draft);update();}catch(_){$('manual-status').textContent='Die Auswahl konnte nicht geleert werden.';}});
  $('manual-review').addEventListener('click',async()=>{
    try{
      draft=readDraft(sessionStorage,slug,data.contexts);
      if(!validate(data.contexts[draft.scenario],draft).ok){update();return;}
      if(data.live){
        $('manual-review').disabled=true;
        const response=await fetch(data.validation_url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':data.csrf},
          body:JSON.stringify({receive:draft.receive,give:draft.give,fingerprint:data.fingerprint})});
        const result=await response.json();
        if(result.ok&&result.review_url){location.assign(result.review_url);return;}
        $('manual-status').textContent=result.message||'Bitte lade die Auswahl neu.';
        $('manual-review').disabled=!result.ok;
      }else if(!readState(sessionStorage).requests['manual-'+slug])location.assign(`/trade-v2/partners/${slug}/manual/review`);
    }catch(_){$('manual-status').textContent='Bitte prüfe deine Auswahl erneut.';}
  });
  update();
}catch(_){$('manual-status').textContent='Die lokale Auswahl ist nicht verfügbar. Öffne einen manuellen Demo-Einstieg für eine neue Auswahl.';$('manual-review').disabled=true;}
document.body.dataset.ready='true';
