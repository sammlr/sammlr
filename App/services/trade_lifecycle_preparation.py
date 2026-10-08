"""Accepted-contract preparation. All transitions share the foundation write lock."""
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import secrets

from services.trade_lifecycle_acceptance import LifecycleAcceptance
from services.trade_lifecycle_requests import instant
from services.trade_lifecycle_foundation import RuleSnapshot, _json
from services.physical_missing import overlap

REASONS = ('MISSING_STICKER','WRONG_STICKER','CONDITION_PROBLEM','NOT_RECOGNIZABLE')


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_preparation_cycles'").fetchone())


class LifecyclePreparation(LifecycleAcceptance):
    def _binding(self, trade, actor, revision=None):
        self._actor(actor)
        if not ready(self.db):
            raise ValueError('Preparation schema unavailable')
        row=self.db.execute('''SELECT c.*,t.requester_user_id,t.partner_user_id,a.accepted_at
            FROM lifecycle_contracts c JOIN trades t ON t.id=c.trade_id
            JOIN lifecycle_acceptances a ON a.trade_id=c.trade_id
            WHERE c.trade_id=? AND c.contract_type='trade_lifecycle_v1' AND c.state='accepted' ''',(trade,)).fetchone()
        if row is None or actor not in (row['requester_user_id'],row['partner_user_id']):
            raise ValueError('Accepted participant required')
        if revision is not None and (type(revision) is not int or revision!=row['accepted_revision_id']):
            raise ValueError('Stale contractual revision')
        return row

    def _unmoved(self,trade):
        if self.db.execute('''SELECT 1 FROM lifecycle_directions WHERE trade_id=?
            AND (shipping_state<>'not_sent' OR receipt_state<>'expected')''',(trade,)).fetchone() or self.db.execute(
                'SELECT 1 FROM lifecycle_movements WHERE trade_id=?',(trade,)).fetchone():
            raise ValueError('Physical movement forbids preparation changes')

    def _cycles(self,row,now):
        for user in (row['requester_user_id'],row['partner_user_id']):
            if not self.db.execute('SELECT 1 FROM lifecycle_preparation_cycles WHERE trade_id=? AND owner_id=? AND is_current=1',(row['trade_id'],user)).fetchone():
                self.db.execute('''INSERT INTO lifecycle_preparation_cycles(trade_id,revision_id,owner_id,created_at)
                    VALUES (?,?,?,?)''',(row['trade_id'],row['accepted_revision_id'],user,now.isoformat()))
        return self.db.execute('SELECT * FROM lifecycle_preparation_cycles WHERE trade_id=? AND is_current=1 ORDER BY owner_id',(row['trade_id'],)).fetchall()

    def _pending(self,trade):
        return self.db.execute("SELECT * FROM lifecycle_reductions WHERE trade_id=? AND state='proposed'",(trade,)).fetchone()

    def _event_data(self,row,event,actor,now,**data):
        self.db.execute('INSERT INTO trade_events(trade_id,event_type,actor_user_id,payload_json,occurred_at) VALUES (?,?,?,?,?)',
            (row['trade_id'],event,actor,_json(dict(revision_id=row['accepted_revision_id'],**data)),now.isoformat()))

    def _overdue(self,row,cycles,now):
        due=instant(row['accepted_at'])+timedelta(hours=72)
        for cycle in cycles:
            if now>=due and (not cycle['completed_at'] or instant(cycle['completed_at'])>due):
                eventkey=f"packing-overdue:{cycle['id']}"
                if not self.db.execute("SELECT 1 FROM trade_events WHERE trade_id=? AND event_type='PackingOverdue' AND json_extract(payload_json,'$.cycle')=?",(row['trade_id'],cycle['id'])).fetchone():
                    self._event_data(row,'PackingOverdue',None,now,cycle=cycle['id'],owner=cycle['owner_id'],event_key=eventkey)

    def _state(self,row,cycles):
        if self._pending(row['trade_id']):return 'reduction_pending'
        if self.db.execute('''SELECT 1 FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id
            WHERE h.trade_id=? AND m.resolved_at IS NULL AND m.overlap_quantity>0''',(row['trade_id'],)).fetchone():return 'physical_missing'
        if self.db.execute("SELECT 1 FROM lifecycle_reductions WHERE trade_id=? AND base_revision_id=? AND state='rejected'",(row['trade_id'],row['accepted_revision_id'])).fetchone():return 'reduction_rejected'
        if any(c['review_state']=='problem' for c in cycles):return 'photo_problem'
        if not all(c['completed_at'] and c['revealed_at'] for c in cycles):return 'preparation'
        if all(c['review_state']=='approved' for c in cycles):return 'ready_for_address_release'
        return 'photo_review'

    def view(self,trade,actor):
        with self.store.transaction():
            row=self._binding(trade,actor);now=instant(self.clock());cycles=self._cycles(row,now)
            self._overdue(row,cycles,now)
            pending=self._pending(trade)
            result=dict(trade=trade,revision=row['accepted_revision_id'],actor=actor,
                deadline=(instant(row['accepted_at'])+timedelta(hours=72)).isoformat(),state=self._state(row,cycles),
                basis=[c['id'] for c in cycles],positions=[dict(p) for p in self._positions(row['accepted_revision_id'])],cycles=[],
                pending=dict(pending) if pending else None)
            result['deadline_label']=instant(result['deadline']).astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y, %H:%M %Z')
            albums={a[0]:a[1] for a in self.db.execute('SELECT id,name FROM albums')}
            for position in result['positions']:position['album_name']=albums.get(position['album_id'],position['album_id'])
            if pending:
                result['proposal']=[dict(p) for p in self._positions(pending['revision_id'])]
            for c in cycles:
                item=dict(c)
                item['photos']=[dict(p) for p in self.db.execute('SELECT id,mime FROM lifecycle_control_photos WHERE cycle_id=? AND removed_at IS NULL',(c['id'],))] if c['owner_id']==actor or c['revealed_at'] else []
                item['problems']=[dict(p) for p in self.db.execute('SELECT reason,position_id,quantity FROM lifecycle_photo_problems WHERE cycle_id=? AND resolved_at IS NULL',(c['id'],))]
                item['overdue']=now>=instant(result['deadline']) and (not c['completed_at'] or instant(c['completed_at'])>instant(result['deadline']))
                result['cycles'].append(item)
            return result

    def _context(self,trade,actor,revision,basis):
        row=self._binding(trade,actor,revision);self._unmoved(trade)
        now=instant(self.clock());cycles=self._cycles(row,now)
        if basis != [c['id'] for c in cycles]:raise ValueError('Photo/preparation basis changed; reload')
        self._overdue(row,cycles,now)
        own=next(c for c in cycles if c['owner_id']==actor)
        other=next(c for c in cycles if c['owner_id']!=actor)
        return row,now,cycles,own,other

    def command(self,trade,actor,revision,basis,key,action,data=None):
        data=data or {};payload=dict(revision=revision,basis=basis,data=data)
        with self.store.transaction():
            old=self._command(trade,actor,key,'preparation:'+action,payload)
            if old is not None:return old
            row,now,cycles,own,other=self._context(trade,actor,revision,basis)
            if action not in ('reduction_approve','reduction_reject','missing','resolve_missing') and self._pending(trade):
                raise ValueError('Resolve proposed reduction first')
            event=None
            if action=='complete':
                if own['completed_at']:raise ValueError('Preparation already complete')
                if not self.db.execute('SELECT 1 FROM lifecycle_control_photos WHERE cycle_id=? AND removed_at IS NULL',(own['id'],)).fetchone():raise ValueError('Kontrollfoto erforderlich')
                if self.db.execute('''SELECT 1 FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id
                    WHERE h.trade_id=? AND m.user_id=? AND m.resolved_at IS NULL AND m.overlap_quantity>0''',(trade,actor)).fetchone():raise ValueError('Physisch fehlende Give-Menge zuerst klären')
                self.db.execute('UPDATE lifecycle_preparation_cycles SET completed_at=? WHERE id=?',(now.isoformat(),own['id']))
                self.db.execute("UPDATE lifecycle_directions SET preparation_state='prepared' WHERE trade_id=? AND from_user_id=?",(trade,actor))
                event='PreparationConfirmed'
                if other['completed_at']:
                    self.db.execute('UPDATE lifecycle_preparation_cycles SET revealed_at=COALESCE(revealed_at,?) WHERE trade_id=? AND is_current=1',(now.isoformat(),trade))
                    self._event_data(row,'BothPackagesVisible',actor,now,cycles=basis)
            elif action in ('approve','problem'):
                if not all(c['completed_at'] and c['revealed_at'] for c in cycles):raise ValueError('Mutual reveal required')
                if other['review_state']!='pending':raise ValueError('Review already decided; correction required')
                if action=='approve':
                    self.db.execute("UPDATE lifecycle_preparation_cycles SET review_state='approved' WHERE id=?",(other['id'],));event='PhotoConfirmed'
                else:
                    reason=data.get('reason');position=data.get('position');quantity=data.get('quantity')
                    if reason not in REASONS:raise ValueError('Structured reason required')
                    if position is not None:
                        p=next((p for p in self._positions(revision) if p['id']==position and p['from_user_id']==other['owner_id']),None)
                        if p is None or type(quantity) is not int or not 1<=quantity<=p['quantity']:raise ValueError('Invalid affected quantity')
                    elif quantity is not None:raise ValueError('Position required')
                    self.db.execute('INSERT INTO lifecycle_photo_problems(cycle_id,reporter_id,reason,position_id,quantity,created_at) VALUES (?,?,?,?,?,?)',(other['id'],actor,reason,position,quantity,now.isoformat()))
                    self.db.execute("UPDATE lifecycle_preparation_cycles SET review_state='problem' WHERE id=?",(other['id'],));event='PhotoProblemReported'
            elif action=='correct':
                if not own['completed_at']:raise ValueError('No completed package to correct')
                self.db.execute('UPDATE lifecycle_preparation_cycles SET is_current=0 WHERE id=?',(own['id'],))
                self.db.execute('UPDATE lifecycle_photo_problems SET resolved_at=? WHERE cycle_id=? AND resolved_at IS NULL',(now.isoformat(),own['id']))
                self.db.execute('INSERT INTO lifecycle_preparation_cycles(trade_id,revision_id,owner_id,created_at) VALUES (?,?,?,?)',(trade,revision,actor,now.isoformat()))
                self.db.execute("UPDATE lifecycle_directions SET preparation_state='preparing' WHERE trade_id=? AND from_user_id=?",(trade,actor));event='ControlPackageRevised'
            elif action=='remove_photo':
                if own['completed_at']:raise ValueError('Completed photos are frozen')
                updated=self.db.execute('UPDATE lifecycle_control_photos SET removed_at=? WHERE id=? AND cycle_id=? AND removed_at IS NULL',(now.isoformat(),data.get('photo'),own['id']))
                if updated.rowcount!=1:raise ValueError('Own draft photo required')
                event='PhotoDraftRemoved'
            elif action=='missing':
                self._missing(row,actor,data,now)
                if own['completed_at']:
                    self.db.execute('UPDATE lifecycle_preparation_cycles SET is_current=0 WHERE id=?',(own['id'],))
                    self.db.execute('INSERT INTO lifecycle_preparation_cycles(trade_id,revision_id,owner_id,created_at) VALUES (?,?,?,?)',(trade,revision,actor,now.isoformat()))
                    self.db.execute("UPDATE lifecycle_directions SET preparation_state='preparing' WHERE trade_id=? AND from_user_id=?",(trade,actor))
                event='PhysicalMissingDeclared'
            elif action=='resolve_missing':
                self._resolve_missing(row,actor,data,now);event='PhysicalMissingResolved'
            elif action=='reduction_propose':
                positions=self._reduced(row,data.get('positions'))
                new=self.store.append_revision(trade,actor,positions,'reduction')
                self.db.execute('INSERT INTO lifecycle_consents VALUES (?,?,?)',(new,actor,now.isoformat()))
                self.db.execute('INSERT INTO lifecycle_reductions(revision_id,trade_id,base_revision_id,proposer_id,created_at) VALUES (?,?,?,?,?)',(new,trade,revision,actor,now.isoformat()))
                event='AmendmentProposed'
            elif action in ('reduction_approve','reduction_reject'):
                proposal=self._pending(trade)
                if proposal is None or proposal['proposer_id']==actor or proposal['revision_id']!=data.get('proposal'):raise ValueError('Current partner proposal required')
                if proposal['base_revision_id']!=revision:raise ValueError('Stale reduction')
                if action=='reduction_approve':self._activate(row,proposal,actor,now)
                self.db.execute('UPDATE lifecycle_reductions SET state=?,decided_at=? WHERE revision_id=?',('approved' if action=='reduction_approve' else 'rejected',now.isoformat(),proposal['revision_id']))
                event='AmendmentAccepted' if action=='reduction_approve' else 'AmendmentRejected'
            else:raise ValueError('Unknown preparation command')
            self._event_data(row,event,actor,now,basis=basis,details=data)
            return self.store.record_command(trade,actor,key,'preparation:'+action,payload,dict(status='ok'))

    def _missing(self,row,actor,data,now):
        p=next((p for p in self._positions(row['accepted_revision_id']) if p['id']==data.get('position') and p['from_user_id']==actor),None)
        quantity=data.get('quantity')
        if p is None or type(quantity) is not int or not 1<=quantity<=p['quantity']:raise ValueError('Own reserved quantity required')
        h=self.db.execute('''SELECT h.* FROM lifecycle_supply_bindings b JOIN trade_reservations h ON h.id=b.reservation_id
            WHERE b.revision_position_id=? AND b.is_current=1 AND h.state='active' ''',(p['id'],)).fetchone()
        if h is None:raise ValueError('Active reservation required')
        existing=self.db.execute('SELECT quantity FROM physical_missing_holds WHERE position_id=? AND resolved_at IS NULL',(p['id'],)).fetchone()
        if existing:
            if quantity<existing[0]:raise ValueError('Resolve missing hold explicitly to reduce it')
            delta=quantity-existing[0]
            if overlap(self.db,h['id'])+delta>h['quantity']:raise ValueError('Missing quantity exceeds reserved quantity')
            self.db.execute('UPDATE physical_missing_holds SET quantity=?,overlap_quantity=overlap_quantity+? WHERE position_id=? AND resolved_at IS NULL',(quantity,delta,p['id']))
            return
        if overlap(self.db,h['id'])+quantity>h['quantity']:raise ValueError('Missing quantity exceeds reserved quantity')
        self.db.execute('''INSERT INTO physical_missing_holds(reservation_id,position_id,user_id,album_id,sticker_code,quantity,overlap_quantity,created_at)
            VALUES (?,?,?,?,?,?,?,?)''',(h['id'],p['id'],actor,p['album_id'],p['sticker_code'],quantity,quantity,now.isoformat()))

    def _resolve_missing(self,row,actor,data,now):
        h=self.db.execute('''SELECT m.* FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id
            WHERE m.id=? AND m.user_id=? AND h.trade_id=? AND m.resolved_at IS NULL''',(data.get('hold'),actor,row['trade_id'])).fetchone()
        if h is None or data.get('resolution') not in ('found','corrected'):raise ValueError('Own active missing hold required')
        self.db.execute('UPDATE physical_missing_holds SET resolved_at=?,resolution=? WHERE id=?',(now.isoformat(),data['resolution'],h['id']))
        if data['resolution']=='corrected':
            from services.inventory_write import InventoryWriteService
            stock=self.db.execute('SELECT quantity FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?',(actor,h['album_id'],h['sticker_code'])).fetchone()
            if stock is None or stock[0]<h['quantity']:raise ValueError('Stored stock inconsistent')
            result=InventoryWriteService(self.db).set_quantity(actor,h['album_id'],h['sticker_code'],stock[0]-h['quantity'])
            if not result.allowed:raise ValueError('Amend remaining reservation before correcting bound stock')

    def resolve_missing(self,trade,actor,key,hold,resolution):
        payload=dict(hold=hold,resolution=resolution)
        with self.store.transaction():
            old=self._command(trade,actor,key,'missing_resolution',payload)
            if old is not None:return old
            self._actor(actor)
            row=self.db.execute('SELECT * FROM lifecycle_contracts WHERE trade_id=?',(trade,)).fetchone()
            if row is None:raise ValueError('V1 contract required')
            now=instant(self.clock())
            self._resolve_missing(row,actor,payload,now)
            self._event_data(row,'PhysicalMissingResolved',actor,now,**payload)
            return self.store.record_command(trade,actor,key,'missing_resolution',payload,dict(status='ok'))

    def _reduced(self,row,positions):
        if not isinstance(positions,list) or not positions:raise ValueError('Exact reduced package required')
        original={tuple(p[k] for k in ('from_user_id','to_user_id','album_id','sticker_code')):p['quantity'] for p in self._positions(row['accepted_revision_id'])}
        seen=set();total=0
        for p in positions:
            if not isinstance(p,(list,tuple)) or len(p)!=5:raise ValueError('Invalid position')
            key=tuple(p[:4]);n=p[4]
            if key in seen or key not in original or type(n) is not int or not 1<=n<=original[key]:raise ValueError('Reduction cannot add or expand quantities')
            seen.add(key);total+=n
        if total>=sum(original.values()):raise ValueError('Strict reduction required')
        snapshot=RuleSnapshot.loads(self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots WHERE revision_id=?',(row['accepted_revision_id'],)).fetchone()[0])
        snapshot.validate(positions)
        return positions

    def _activate(self,row,proposal,actor,now):
        new=proposal['revision_id'];old=row['accepted_revision_id']
        newpositions=self._positions(new)
        self._reduced(row,[list(p)[1:] for p in newpositions])
        bykey={(p['from_user_id'],p['album_id'],p['sticker_code']):p for p in newpositions}
        # Validate the full remaining contract before moving either ledger.
        for p in self._positions(old):
            h=self.db.execute('''SELECT h.* FROM lifecycle_supply_bindings b JOIN trade_reservations h ON h.id=b.reservation_id
                WHERE b.revision_position_id=? AND b.is_current=1 AND h.state='active' ''',(p['id'],)).fetchone()
            claim=self.db.execute("SELECT * FROM lifecycle_need_claims WHERE revision_position_id=? AND state='committed'",(p['id'],)).fetchone()
            n=bykey.get((p['from_user_id'],p['album_id'],p['sticker_code']))
            if h is None or claim is None or h['quantity']!=p['quantity'] or claim['received_quantity']:raise ValueError('Binding mismatch')
            from services.inventory import InventoryReadService
            availability=InventoryReadService(self.db).snapshot(p['from_user_id'],p['album_id'],(p['sticker_code'],)).sticker(p['sticker_code'])
            if not availability.balance_is_valid:raise ValueError('Physical reservation balance inconsistent')
            if n and n['quantity']>h['quantity']-overlap(self.db,h['id']):raise ValueError('Reduced package still contains physically missing quantity')
        snapshot=RuleSnapshot.loads(self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots WHERE revision_id=?',(old,)).fetchone()[0])
        self.store.store_rule_snapshot(new,snapshot,row['accepted_at'])
        self.db.execute('INSERT INTO lifecycle_consents VALUES (?,?,?)',(new,actor,now.isoformat()))
        for p in self._positions(old):
            h=self.db.execute('''SELECT h.* FROM lifecycle_supply_bindings b JOIN trade_reservations h ON h.id=b.reservation_id
                WHERE b.revision_position_id=? AND b.is_current=1''',(p['id'],)).fetchone()
            n=bykey.get((p['from_user_id'],p['album_id'],p['sticker_code']))
            self.db.execute('UPDATE lifecycle_supply_bindings SET is_current=0 WHERE revision_position_id=?',(p['id'],))
            if n and n['quantity']==p['quantity']:
                self.db.execute('INSERT INTO lifecycle_supply_bindings(reservation_id,revision_position_id) VALUES (?,?)',(h['id'],n['id']))
            else:
                self.db.execute("UPDATE trade_reservations SET state='released',released_at=?,release_reason='reduction' WHERE id=?",(now.isoformat(),h['id']))
                if n:self.store.bind_supply_position(n['id'])
            self.db.execute("UPDATE lifecycle_need_claims SET state='released',released_at=? WHERE revision_position_id=?",(now.isoformat(),p['id']))
            if n:self.db.execute("INSERT INTO lifecycle_need_claims(revision_position_id,state,quantity,created_at) VALUES (?,'committed',?,?)",(n['id'],n['quantity'],now.isoformat()))
        self.db.execute('UPDATE lifecycle_contracts SET accepted_revision_id=?,current_revision_id=? WHERE trade_id=?',(new,new,row['trade_id']))
        self.db.execute('UPDATE lifecycle_preparation_cycles SET is_current=0 WHERE trade_id=? AND is_current=1',(row['trade_id'],))
        self.db.execute("UPDATE lifecycle_directions SET preparation_state='preparing' WHERE trade_id=?",(row['trade_id'],))

    def upload(self,trade,actor,revision,basis,key,data,storage):
        from services.lifecycle_photos import sanitise
        safe,mime,extension=sanitise(data)
        digest=hashlib.sha256(safe).hexdigest();payload=dict(revision=revision,basis=basis,digest=digest)
        destination=None
        try:
            with self.store.transaction():
                old=self._command(trade,actor,key,'photo_upload',payload)
                if old is not None:return old
                row,now,cycles,own,other=self._context(trade,actor,revision,basis)
                if own['completed_at'] or self._pending(trade):raise ValueError('Photo basis frozen')
                storage=Path(storage);storage.mkdir(parents=True,exist_ok=True)
                name=secrets.token_hex(24)+'.'+extension;destination=storage/name
                with destination.open('xb') as f:f.write(safe)
                photo=self.db.execute('INSERT INTO lifecycle_control_photos(cycle_id,storage_name,mime,digest,created_at) VALUES (?,?,?,?,?)',(own['id'],name,mime,digest,now.isoformat())).lastrowid
                self._event_data(row,'ControlPhotoUploaded',actor,now,cycle=own['id'],photo=photo)
                return self.store.record_command(trade,actor,key,'photo_upload',payload,dict(photo=photo))
        except BaseException:
            if destination is not None:destination.unlink(missing_ok=True)
            raise

    def photo(self,trade,actor,photo):
        self._binding(trade,actor)
        p=self.db.execute('''SELECT p.* ,c.owner_id,c.revealed_at FROM lifecycle_control_photos p
            JOIN lifecycle_preparation_cycles c ON c.id=p.cycle_id
            JOIN lifecycle_contracts t ON t.trade_id=c.trade_id
            WHERE p.id=? AND c.trade_id=? AND c.is_current=1 AND c.revision_id=t.accepted_revision_id AND p.removed_at IS NULL''',(photo,trade)).fetchone()
        if p is None or (p['owner_id']!=actor and not p['revealed_at']):raise ValueError('Photo is private')
        return dict(p)
