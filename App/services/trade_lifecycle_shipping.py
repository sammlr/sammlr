"""V1 shipping. One serialized debit path; no receipt or inventory credits."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from services.trade_lifecycle_addresses import LifecycleAddresses
from services.trade_lifecycle_requests import instant
from services.inventory import InventoryReadService
from services.history_cutover import HistoricalInventoryWriteService
from services.physical_missing import overlap
from services.typed_notifications import TypedNotificationService


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_shipping'").fetchone())


class LifecycleShipping(LifecycleAddresses):
    def _shipping_schema(self):
        if not ready(self.db):raise ValueError('Shipping schema unavailable')

    def _sent(self,trade,sender):
        return self.db.execute('SELECT * FROM lifecycle_shipping WHERE trade_id=? AND from_user_id=?',(trade,sender)).fetchone()

    def _shipping_overdue(self,row,now):
        release=self._released(row['trade_id'])
        if not release:return
        due=instant(release['released_at'])+timedelta(hours=72)
        if now<due:return
        for sender in (row['requester_user_id'],row['partner_user_id']):
            sent=self._sent(row['trade_id'],sender)
            if sent and instant(sent['sent_at'])<due:continue
            if not self.db.execute("SELECT 1 FROM trade_events WHERE trade_id=? AND event_type='ShippingOverdue' AND json_extract(payload_json,'$.sender')=?",(row['trade_id'],sender)).fetchone():
                self._event_data(row,'ShippingOverdue',None,now,sender=sender,due_at=due.isoformat())

    def shipping_view(self,trade,actor):
        self._shipping_schema()
        # Address rendering retains L05's server-side privacy boundary.
        model=self.view_address(trade,actor)
        with self.store.transaction():
            row=self._binding(trade,actor);release=self._released(trade)
            if not release:raise ValueError('Mutual address release required')
            now=instant(self.clock());self._shipping_overdue(row,now)
            due=instant(release['released_at'])+timedelta(hours=72)
            directions=[]
            for sender in (row['requester_user_id'],row['partner_user_id']):
                sent=self._sent(trade,sender)
                directions.append(dict(sender=sender,state='sent' if sent else 'overdue' if now>=due else 'ready_to_ship',
                    sent_at=sent['sent_at'] if sent else None,source=sent['source'] if sent else None))
            model.update(actor=actor,directions=directions,shipping_state='in_transit' if all(d['state']=='sent' for d in directions) else 'partially_sent' if any(d['state']=='sent' for d in directions) else 'ready_to_ship',
                due_at=due.isoformat(),due_label=due.astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y, %H:%M %Z'),
                remaining_seconds=max(0,int((due-now).total_seconds())),
                positions=[dict(p) for p in self._positions(row['accepted_revision_id']) if p['from_user_id']==actor])
            return model

    def finalize_direction_sent(self,trade,sender,revision,*,actor,source='SENDER_CONFIRMATION'):
        """Trusted domain primitive inside this service's IMMEDIATE unit of work.

        RECEIPT_EVIDENCE is an internal future full-package evidence caller, never
        a public HTTP option. sent_at records observation, not an invented past
        dispatch. A future partial receipt must debit only evidenced positions
        through the same movement ledger; no receipt is implemented here.
        A savepoint rolls back this entire primitive even if its caller catches.
        """
        self.store._write(trade);self._shipping_schema()
        self.db.execute('SAVEPOINT direction_shipping')
        try:
            result=self._finalize(trade,sender,revision,actor,source)
            self.db.execute('RELEASE direction_shipping')
            return result
        except BaseException:
            self.db.execute('ROLLBACK TO direction_shipping');self.db.execute('RELEASE direction_shipping');raise

    def _finalize(self,trade,sender,revision,actor,source):
        row=self._binding(trade,actor,revision)
        direction=self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? AND from_user_id=?',(trade,sender)).fetchone()
        if direction is None or source not in ('SENDER_CONFIRMATION','RECEIPT_EVIDENCE'):raise ValueError('Invalid shipping source')
        if actor!=(sender if source=='SENDER_CONFIRMATION' else direction['to_user_id']):raise ValueError('Invalid shipping actor')
        old=self._sent(trade,sender)
        if old:return dict(old)
        now=instant(self.clock())
        if direction['shipping_state']!='not_sent':raise ValueError('Inconsistent shipping state')
        if source=='SENDER_CONFIRMATION':
            release=self._released(trade)
            if not release or release['revision_id']!=revision or direction['preparation_state']!='ready_to_ship':raise ValueError('Current address release required')
        if self._pending(trade):raise ValueError('Reduction unresolved')
        positions=[p for p in self._positions(revision) if p['from_user_id']==sender]
        if not positions:raise ValueError('Give package missing')
        pending=[]
        for p in positions:
            hold=self.db.execute('''SELECT h.* FROM lifecycle_supply_bindings b JOIN trade_reservations h ON h.id=b.reservation_id
                WHERE b.revision_position_id=? AND b.is_current=1''',(p['id'],)).fetchone()
            if hold is None or hold['state']!='active' or hold['quantity']!=p['quantity'] or overlap(self.db,hold['id']):raise ValueError('Exact physically present reservation required')
            inv=InventoryReadService(self.db).snapshot(sender,p['album_id'],(p['sticker_code'],)).sticker(p['sticker_code'])
            if not inv.balance_is_valid or inv.physical<p['quantity']:raise ValueError('Inventory requires reconciliation')
            if self.db.execute("SELECT 1 FROM lifecycle_movements WHERE trade_id=? AND from_user_id=? AND album_id=? AND sticker_code=? AND movement_kind='debit'",(trade,sender,p['album_id'],p['sticker_code'])).fetchone():raise ValueError('Existing partial debit requires reconciliation')
            pending.append((p,hold,inv.physical))
        self._shipping_overdue(row,now)
        for p,hold,quantity in pending:
            self.db.execute("UPDATE trade_reservations SET state='released',released_at=?,release_reason='lifecycle_sent' WHERE id=?",(now.isoformat(),hold['id']))
            movement=f"lifecycle-sent:{trade}:{sender}:{p['id']}"
            result=HistoricalInventoryWriteService(self.db).remove(sender,p['album_id'],p['sticker_code'],p['quantity'],event_key=movement,source_type='trade_shipping')
            if not result.allowed or result.previous_quantity!=quantity or result.quantity!=quantity-p['quantity']:raise ValueError('Shipping debit failed')
            self.db.execute("INSERT INTO lifecycle_movements VALUES (?,?,?,?,'debit',?,?,?)",(trade,sender,p['album_id'],p['sticker_code'],'full-package',p['quantity'],movement))
        self.db.execute('INSERT INTO lifecycle_shipping VALUES (?,?,?,?,?,?,?)',(trade,sender,revision,now.isoformat(),now.isoformat() if source=='SENDER_CONFIRMATION' else None,source,actor))
        self.db.execute("UPDATE lifecycle_directions SET shipping_state='sent' WHERE trade_id=? AND from_user_id=?",(trade,sender))
        self._event_data(row,'DirectionSent',actor,now,sender=sender,source=source,sent_at=now.isoformat())
        event=self.db.execute('SELECT last_insert_rowid()').fetchone()[0]
        TypedNotificationService(self.db).create(direction['to_user_id'],'lifecycle_direction_sent','Sendung versendet',
            'Dein Tauschpartner hat seine Sendung als versendet bestätigt.' if source=='SENDER_CONFIRMATION' else 'Der physische Abgang wurde durch einen Empfangsnachweis festgestellt.',
            'trade',trade,event)
        return dict(self._sent(trade,sender))

    def send_direction(self,trade,actor,revision,key):
        self._shipping_schema();payload=dict(revision=revision)
        with self.store.transaction():
            old=self._command(trade,actor,key,'direction_sent',payload)
            if old is not None:return old
            result=self.finalize_direction_sent(trade,actor,revision,actor=actor)
            return self.store.record_command(trade,actor,key,'direction_sent',payload,result)
