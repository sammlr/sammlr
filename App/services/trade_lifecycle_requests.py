"""Authoritative pre-acceptance V1 commands. Never migrate or move inventory."""
from datetime import datetime, timedelta, timezone
import hashlib

from services.trade_lifecycle_foundation import LifecycleFoundation, _json
from services.trade_contracts import require_trade_operation
from services.trade_v2_domain import TradeV2Domain


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lifecycle_requests'").fetchone())


def instant(value):
    value = datetime.fromisoformat(str(value).replace('Z', '+00:00')) if not isinstance(value, datetime) else value
    if value.tzinfo is None:
        raise ValueError('Timezone-aware timestamp required')
    return value.astimezone(timezone.utc)


class LifecycleRequests:
    def __init__(self, db, now=None):
        self.db = db
        self.store = LifecycleFoundation(db)
        self.clock = now or (lambda: datetime.now(timezone.utc))

    def _actor(self, actor):
        if type(actor) is not int or actor <= 0:
            raise ValueError('Authenticated actor required')
        row = self.db.execute('SELECT account_state FROM users WHERE id=?', (actor,)).fetchone()
        if row is None or row[0] != 'active':
            raise ValueError('Active account required')

    def _row(self, trade_id):
        require_trade_operation(self.db, trade_id, 'request')
        row = self.db.execute('''SELECT q.*,CASE WHEN q.sender_user_id=t.requester_user_id THEN t.partner_user_id ELSE t.requester_user_id END AS partner_user_id,c.accepted_revision_id,c.origin
            FROM lifecycle_requests q JOIN trades t ON t.id=q.trade_id
            JOIN lifecycle_contracts c ON c.trade_id=q.trade_id WHERE q.trade_id=? AND q.revision_id=c.current_revision_id''', (trade_id,)).fetchone()
        if row is None:
            raise ValueError('Current request required')
        return row

    def _event(self, trade, revision, event, actor, now):
        self.db.execute('''INSERT INTO trade_events(trade_id,event_type,actor_user_id,payload_json,occurred_at)
            VALUES (?,?,?,?,?)''', (trade, event, actor, _json({'revision_id':revision}), now.isoformat()))

    def _end(self, row, status, actor, now):
        if row['status'] != 'open':
            return row['status']
        self.store.release_pending_quantities(row['revision_id'])
        self.db.execute('UPDATE lifecycle_requests SET status=?,ended_at=? WHERE revision_id=?',
                        (status,now.isoformat(),row['revision_id']))
        self.db.execute("UPDATE lifecycle_contracts SET state='ended' WHERE trade_id=?", (row['trade_id'],))
        self.db.execute('UPDATE trades SET lifecycle_state=?,updated_at=? WHERE id=?',
                        (status,now.isoformat(),row['trade_id']))
        kind=self.db.execute('SELECT kind FROM lifecycle_revisions WHERE id=?',(row['revision_id'],)).fetchone()[0]
        self._event(row['trade_id'],row['revision_id'],('Counter' if kind=='counter' else 'Offer')+status.title(),actor,now)
        return status

    def _expire(self, now):
        rows = self.db.execute("SELECT trade_id FROM lifecycle_requests WHERE status='open'").fetchall()
        count = 0
        for row in rows:
            request = self._row(row[0])
            if now >= instant(request['expires_at']):
                self._end(request,'expired',None,now)
                count += 1
        return count

    def expire(self):
        """Same idempotent command for lazy cleanup and a future scheduler."""
        with self.store.transaction():
            return self._expire(instant(self.clock()))

    def create(self, actor, partner, give, receive, key, *, origin='MANUAL'):
        if not ready(self.db):
            raise ValueError('Lifecycle request schema unavailable')
        if type(partner) is not int or partner == actor or origin not in ('MANUAL','SMARTDEAL'):
            raise ValueError('Invalid recipient or origin')
        if not isinstance(key,str) or not 1 <= len(key) <= 200:
            raise ValueError('Command key required')
        give,receive = tuple(give),tuple(receive)
        payload = dict(partner=partner,origin=origin,
                       give=sorted((p.album_id,p.sticker_code,p.quantity) for p in give),
                       receive=sorted((p.album_id,p.sticker_code,p.quantity) for p in receive))
        digest = hashlib.sha256(_json(payload).encode()).hexdigest()
        with self.store.transaction():
            self._actor(actor)
            now = instant(self.clock())  # Sample after acquiring the serialization lock.
            self._expire(now)
            old = self.db.execute('SELECT trade_id,payload_digest FROM lifecycle_requests WHERE sender_user_id=? AND command_key=?', (actor,key)).fetchone()
            if old:
                if old['payload_digest'] != digest:
                    raise ValueError('Command key reused with different deal')
                return old['trade_id']
            self._actor(partner)
            count = self.db.execute("SELECT COUNT(*) FROM lifecycle_requests WHERE sender_user_id=? AND status='open'", (actor,)).fetchone()[0]
            if count >= 3:
                raise ValueError('Maximal drei eigene offene Anfragen sind möglich.')
            market = TradeV2Domain(self.db).market(actor)
            TradeV2Domain.validate_deal(market,partner,give,receive,balanced=origin=='SMARTDEAL')
            if origin=='SMARTDEAL' and sum(p.quantity for p in receive)<5:
                raise ValueError('SmartDeal requires at least five pieces')
            trade = self.store.create_identity(actor,partner,origin)
            positions = [(actor,partner,p.album_id,p.sticker_code,p.quantity) for p in give]
            positions += [(partner,actor,p.album_id,p.sticker_code,p.quantity) for p in receive]
            revision = self.store.append_revision(trade,actor,positions)
            self.db.execute("UPDATE lifecycle_contracts SET current_revision_id=?,state='open' WHERE trade_id=?", (revision,trade))
            self.store.bind_pending_quantities(revision)
            self.db.execute('''INSERT INTO lifecycle_requests
                (trade_id,revision_id,sender_user_id,command_key,payload_digest,created_at,expires_at)
                VALUES (?,?,?,?,?,?,?)''', (trade,revision,actor,key,digest,now.isoformat(),(now+timedelta(hours=72)).isoformat()))
            self.db.execute("UPDATE trades SET lifecycle_state='open',created_at=?,updated_at=? WHERE id=?", (now.isoformat(),now.isoformat(),trade))
            self._event(trade,revision,'OfferSent',actor,now)
            return trade

    def transition(self, trade_id, actor, action):
        if action not in ('withdrawn','rejected'):
            raise ValueError('Unsupported request action')
        with self.store.transaction():
            self._actor(actor)
            row = self._row(trade_id)
            if row['accepted_revision_id'] is not None:
                raise ValueError('Accepted contracts cannot use request releases')
            owner = row['sender_user_id'] if action=='withdrawn' else row['partner_user_id']
            if actor != owner:
                raise ValueError('Request role does not authorize this action')
            now = instant(self.clock())
            if row['status']=='open' and now >= instant(row['expires_at']):
                return self._end(row,'expired',None,now)
            return self._end(row,action,actor,now)

    def view(self, actor, trade_id=None):
        """Authorized read with atomic lazy expiry; no acceptance action exists."""
        with self.store.transaction():
            self._actor(actor)
            if trade_id is not None:
                row = self._row(trade_id)
                if actor not in (row['sender_user_id'],row['partner_user_id']):
                    raise ValueError('Request is private to its participants')
            self._expire(instant(self.clock()))
            rows = self.db.execute('''SELECT q.*,CASE WHEN q.sender_user_id=t.requester_user_id THEN t.partner_user_id ELSE t.requester_user_id END AS partner_user_id,s.username AS sender,p.username AS recipient,r.kind
                FROM lifecycle_requests q JOIN trades t ON t.id=q.trade_id
                JOIN lifecycle_contracts c ON c.trade_id=q.trade_id AND c.current_revision_id=q.revision_id
                JOIN lifecycle_revisions r ON r.id=q.revision_id
                JOIN users s ON s.id=q.sender_user_id JOIN users p ON p.id=CASE WHEN q.sender_user_id=t.requester_user_id THEN t.partner_user_id ELSE t.requester_user_id END
                WHERE (t.requester_user_id=? OR t.partner_user_id=?) AND (? IS NULL OR q.trade_id=?)
                ORDER BY q.created_at DESC,q.trade_id DESC''',(actor,actor,trade_id,trade_id)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item['positions'] = [dict(p) for p in self.db.execute('''SELECT p.*,a.name AS album
                    FROM lifecycle_revision_positions p JOIN albums a ON a.id=p.album_id
                    WHERE revision_id=? ORDER BY from_user_id,album_id,sticker_code''',(row['revision_id'],))]
                result.append(item)
            return result
