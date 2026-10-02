import {hasReceipt} from './receipt_state.js';
import {initialState, readState, saveState, slots, incomingSlots, perspective} from './requests.js';
import {loadSession} from './session.js';
import {version, shipped, opposite, positions} from './deal_versions.js';
import {packSide} from './packing.js';
import {proposeAmendment, decideAmendment, proposalBlock} from './amendments.js';
import {DEMOS, amendmentDemo} from './amendment_demo.js';

export function startAmendment(data) {
  const $=id=>document.getElementById(id),url=new URL(location.href);
  const role=url.searchParams.get('role')==='recipient'?'recipient':'sender';
  const base=`/trade-v2/requests/${data.deal.partner_slug}`;
  let state, request, blocked=null, navigationReadyAt=0;
  $('role-sender').href=`${base}/amendment?role=sender`;$('role-recipient').href=`${base}/amendment?role=recipient`;
  $('role-'+role).setAttribute('aria-current','page');$('amend-back').href=`${base}?role=${role}`;
  $('amend-pack').href=`${base}/next?role=${role}&view=packed`;
  function fail(){ $('amend-title').textContent='Der lokale Änderungsstand ist nicht verfügbar.';$('amend-copy').textContent='Bitte die lokale Demo zurücksetzen.';for(const id of ['amend-actions','amend-pack','amend-create','amend-diff'])$(id).hidden=true; }
  try {
    const scenario=url.searchParams.get('amend');
    if (DEMOS.includes(scenario)) {
      state=amendmentDemo(data.deal,scenario);saveState(sessionStorage,state);
      url.searchParams.delete('amend');history.replaceState(null,'',url);
    } else state=loadSession(data.deal);
    request=state.requests[data.deal.id];
    if (!request) {fail();return;}
    // A normal report already creates its proposal; old report-only states need an explicit entry action.
    const reporter=['sender','recipient'].find(side=>packSide(request,side).phase==='missing_reported');
    if (!request.amendment && reporter && scenario!=='missing') {
      blocked=proposalBlock(request,reporter);
    }
  } catch(_){fail();return;}
  function list(id,items) {
    $(id).replaceChildren(...items.map(item=>{const li=document.createElement('li');li.dataset.positionId=item.positionId;li.dataset.itemKey=item.key;li.textContent=`${item.album} · ${item.code} · Exemplar ${item.instance}`;return li;}));
  }
  function render() {
    const a=request.amendment,view=perspective(request,role),other=opposite(role);
    const own=packSide(request,role),partner=packSide(request,other);
    const original=request.dealVersions?.[0].snapshot || request.snapshot;
    document.body.dataset.role=role;document.body.dataset.amendmentState=a?.status || blocked || 'missing_reported';document.body.dataset.dealVersion=version(request);
    $('role-recipient').textContent=view.side_b;
    for (const id of ['amend-actions','amend-create','amend-pack','amend-diff']) $(id).hidden=true;
    $('amend-notice').textContent='';$('amend-eyebrow').textContent='Tausch anpassen';
    if (request.status==='cancelled') {
      $('amend-title').textContent='Der Tausch wurde beendet.';$('amend-copy').textContent='Die vorgeschlagene Änderung wurde nicht angenommen. Dieser Tausch wird nicht fortgesetzt.';
    } else if (shipped(request) || hasReceipt(request)) {
      $('amend-title').textContent='Diese Änderung ist nicht mehr möglich.';$('amend-copy').textContent='Ein Versand oder tatsächlicher Empfang ist bereits dokumentiert. Das vereinbarte Paket bleibt unverändert.';
    } else if (version(request)===2 && ['sender','recipient'].some(side=>packSide(request,side).phase==='missing_reported')) {
      $('amend-title').textContent='Weitere Änderung erforderlich';$('amend-copy').textContent='Eine weitere Fehlmenge wurde gemeldet. Der vereinbarte Tausch bleibt unverändert; eine weitere Änderungsrunde ist in dieser Preview noch nicht verfügbar.';
    } else if (a) {
      const proposer=a.proposer===role,after=a.proposal.snapshot,n=a.missingKeys.length;
      $('amend-diff').hidden=false;
      $('amend-before').textContent=`${original.give_count} ↔ ${original.receive_count}`;
      $('amend-after').textContent=`${after.give_count} ↔ ${after.receive_count}`;
      $('amend-after-label').textContent=a.status==='accepted'?'Jetzt vereinbart':'Vorgeschlagen';
      $('amend-own-label').textContent=proposer?'Bei dir entfällt':'Du bekommst nicht mehr';
      $('amend-counter-label').textContent=proposer?`Bei ${view.partner} entfällt`:'Du musst nicht mehr abgeben';
      list('amend-own-removed',a.proposal.removed[a.proposer]);list('amend-counter-removed',a.proposal.removed[opposite(a.proposer)]);
      if (a.status==='accepted') {
        $('amend-title').textContent='Die Änderung ist angenommen.';$('amend-copy').textContent=`Ihr tauscht jetzt ${after.give_count} ↔ ${after.receive_count} Sticker. Bereits gepackte, weiterhin vereinbarte Sticker bleiben markiert.`;
        $('amend-pack').hidden=false;
      } else {
        $('amend-title').textContent=proposer?`Wartet auf ${view.partner}.`:`${view.partner} möchte den Tausch anpassen.`;
        $('amend-copy').textContent=proposer?`Du kannst ${n} Sticker nicht liefern. ${view.partner} muss dem reduzierten Tausch zustimmen. Bis dahin bleibt das bisher vereinbarte Paket unverändert.`:`${n} vereinbarte Sticker fehlen. Prüfe, was du nicht mehr bekommst und nicht mehr abgeben musst.`;
        if (!a.proposal.continuable) $('amend-notice').textContent='Es bleibt kein beidseitiger Tausch übrig. Diese Änderung kann nicht als neuer Deal angenommen werden.';
        $('amend-actions').hidden=proposer;
        $('amend-accept').hidden=!a.proposal.continuable;
        $('amend-accept').textContent=`Mit ${after.give_count} ↔ ${after.receive_count} weitertauschen`;
      }
    } else if (['both_reported','unmatched_positions','invalid'].includes(blocked)) {
      $('amend-title').textContent='Weitere Klärung erforderlich';$('amend-copy').textContent='Die gemeldeten Positionen lassen sich nicht sicher in einer gemeinsamen Änderung auflösen. Der Deal bleibt unverändert.';
    } else if (own.phase==='missing_reported') {
      $('amend-title').textContent='Fehlende Sticker gemeldet.';$('amend-copy').textContent=`${own.missingReported.length} konkrete Positionen fehlen. Das vereinbarte Paket ist noch unverändert.`;
      $('amend-create').hidden=false;
    } else { $('amend-title').textContent='Noch keine Änderung vorgeschlagen';$('amend-copy').textContent='Die Packliste bleibt die Grundlage für die Prüfung deiner Sticker.';$('amend-pack').hidden=false; }
    $('capacity-count').textContent=role==='sender'?`${slots(state)}/3 ausgehend belegt`:`${incomingSlots(state,request.snapshot.partner_id)}/3 eingehend belegt`;
    $('amend-dev').textContent=`Active deal version: ${version(request)}\nOriginal size: ${original.give_count}/${original.receive_count}\nCurrent size: ${request.status==='cancelled'?'none (cancelled)':`${request.snapshot.give_count}/${request.snapshot.receive_count}`}\nAmendment state: ${a?.status || blocked || 'none'}\nMissing position IDs: ${a?.proposal.removed[a.proposer].map(i=>i.positionId).join(', ') || own.missingReported.join(', ')}\nCounter-position IDs: ${a?.proposal.removed[opposite(a.proposer)].map(i=>i.positionId).join(', ') || 'none'}\nAmendment proposer: ${a?.proposer || 'none'}\nAmendment accepted by: ${a?.acceptedBy || 'none'}\nMy packing count: ${own.packed.length}/${positions(request.snapshot,role).length}\nPartner packing count: ${partner.packed.length}/${positions(request.snapshot,other).length}\nOperational slot occupied: ${request.status==='accepted' && !(role==='sender'?request.ownShipped:request.recipientShipped)}`;
  }
  $('amend-pack').addEventListener('click',event=>{if(performance.now()<navigationReadyAt)event.preventDefault();});
  for (const [id,action] of [['amend-accept','accept'],['amend-cancel','cancel'],['amend-create','create']]) $(id).addEventListener('click',()=>{
    try {
      const next=readState(sessionStorage),r=next.requests[data.deal.id];
      const wasPending=r?.amendment?.status==='pending';
      const outcome=action==='create'?proposeAmendment(r,role):decideAmendment(next,r.id,role,action,Date.now(),request.amendment?.id);
      saveState(sessionStorage,next);state=next;request=next.requests[r.id];blocked=outcome;
      render();
      if (wasPending && outcome==='accepted') {
        // Prevent the second physical click from falling through onto the newly revealed link.
        navigationReadyAt=performance.now()+350;$('amend-pack').setAttribute('aria-disabled','true');
        setTimeout(()=>$('amend-pack').removeAttribute('aria-disabled'),350);
      }
      if (['forbidden','invalid','stale','further_change'].includes(outcome)) $('amend-notice').textContent='Diese Aktion kann nicht ausgeführt werden. Der vereinbarte Deal bleibt unverändert.';
      $('amend-title').focus();window.scrollTo(0,0);
    } catch(_){fail();}
  });
  $('demo-reset').addEventListener('click',()=>{try {saveState(sessionStorage,initialState(Number($('demo-count').value)));location.assign(base);}catch(_){fail();}});
  render();
}
