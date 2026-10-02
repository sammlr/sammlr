"""Internal V1 Accept / GO orchestration. No physical lifecycle or public route."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import sqlite3

from services.albums import all_codes
from services.inventory import InventoryReadService
from services.smart_trade_requests import SMART_ACCEPTED_EVENT
from services.smartdeal_expiry import expires_at, utc_instant
from services.smartdeal_identity import SmartDealOpportunityIdentity
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_release import SmartDealReleaseService
from services.smartdeal_requests import SmartDealRequestService
from services.smartdeal_suggestions import _payload_identity
from services.trade_contracts import SMARTDEAL_V1_CONTRACT


class AcceptanceCode(str, Enum):
    ACCEPTED = 'ACCEPTED'
    ALREADY_ACCEPTED = 'ALREADY_ACCEPTED'
    CREATED = 'CREATED'
    ALREADY_CREATED = 'ALREADY_CREATED'
    INVALID_PAYLOAD = 'INVALID_PAYLOAD'
    STALE = 'STALE'
    LIMIT_REACHED = 'LIMIT_REACHED'
    EXPIRED = 'EXPIRED'
    NOT_PENDING = 'NOT_PENDING'
    NOT_V1 = 'NOT_V1'
    NOT_FOUND = 'NOT_FOUND'
    UNAUTHORIZED = 'UNAUTHORIZED'
    BUSY = 'BUSY'


@dataclass(frozen=True)
class AcceptanceResult:
    code: AcceptanceCode
    request_id: int | None = None
    trade_id: int | None = None


class SmartDealAcceptanceService:
    def __init__(self, connection, catalog_provider=all_codes, now_provider=None):
        self._db = connection
        self._catalog = catalog_provider
        self._now = now_provider or (lambda:datetime.now(timezone.utc))
        self._requests = SmartDealRequestService(connection,catalog_provider,self._now)
        self._release = SmartDealReleaseService(connection,self._now)

    def _transaction(self, action):
        if self._db.in_transaction:
            raise ValueError('Accept/GO requires idle connection; caller transaction preserved')
        started = False
        try:
            self._db.execute('BEGIN IMMEDIATE')
            started = True
            result = action(utc_instant(self._now()))
            self._db.commit()
            return result
        except BaseException as error:
            if started:
                self._db.rollback()
            if isinstance(error,sqlite3.OperationalError) and getattr(error,'sqlite_errorcode',0)&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):
                return AcceptanceResult(AcceptanceCode.BUSY)
            raise

    def _lookup(self, identity):
        """Two batch reads under the writer lock; full identity, never digest only."""
        params = (SMARTDEAL_V1_CONTRACT, identity.low_user_id, identity.high_user_id,
                  identity.high_user_id, identity.low_user_id)
        where = """q.contract_type=? AND q.status IN ('open','accepted') AND
            ((q.from_user_id=? AND q.to_user_id=?) OR (q.from_user_id=? AND q.to_user_id=?))"""
        requests = self._db.execute('SELECT q.* FROM trade_requests q WHERE '+where+' ORDER BY q.id',params).fetchall()
        positions = defaultdict(list)
        for row in self._db.execute('''SELECT p.*,q.id AS request_id FROM trade_requests q
            JOIN trades t ON t.legacy_trade_request_id=q.id JOIN trade_positions p ON p.trade_id=t.id
            WHERE '''+where+' ORDER BY q.id,p.id',params):
            positions[row['request_id']].append(row)
        matches = []
        for request in requests:
            low,high=sorted((request['from_user_id'],request['to_user_id']))
            a,b=[],[]
            for p in positions[request['id']]:
                if (p['from_user_id'],p['to_user_id']) not in ((low,high),(high,low)):
                    raise ValueError('Foreign stored participant in opportunity lookup')
                (a if p['from_user_id']==low else b).append((p['album_id'],p['sticker_code'],p['quantity']))
            actual = SmartDealOpportunityIdentity(low,high,tuple(a),tuple(b))
            if len(a)<5 or len(a)!=len(b):
                raise ValueError('Incomplete stored opportunity')
            if actual == identity:
                matches.append(request)
        if len(matches)>1:
            raise ValueError('Multiple active instances of exact opportunity')
        return matches[0] if matches else None

    def go(self, suggestion, actor_user_id):
        identity = _payload_identity(suggestion)
        if identity is None or type(actor_user_id) is not int or actor_user_id not in (identity.low_user_id,identity.high_user_id):
            return AcceptanceResult(AcceptanceCode.INVALID_PAYLOAD)
        def run(now):
            request = self._lookup(identity)
            if request is not None:
                if request['status']=='accepted':
                    trade_id=self._verify_accepted(request,now)
                    return AcceptanceResult(AcceptanceCode.ALREADY_ACCEPTED,request['id'],trade_id)
                if request['to_user_id']==actor_user_id:
                    return self._accept_locked(request['id'],actor_user_id,now)
                if now >= expires_at(request['binding_created_at']):
                    self._release._release_locked(request['id'],'expired',None,now)
                    return AcceptanceResult(AcceptanceCode.EXPIRED,request['id'])
                trade_id=self._requests._assert_complete(request['id'],identity,now)
                return AcceptanceResult(AcceptanceCode.ALREADY_CREATED,request['id'],trade_id)
            created=self._requests._create_locked(suggestion,actor_user_id,identity,now)
            return AcceptanceResult(AcceptanceCode(created.code.value),created.request_id,created.trade_id)
        return self._transaction(run)

    def accept(self, request_id, actor_user_id):
        if type(request_id) is not int or request_id<=0:
            raise ValueError('Canonical positive request ID required')
        return self._transaction(lambda now:self._accept_locked(request_id,actor_user_id,now))

    def _currently_executable(self, request, identity, now):
        """Own bound pieces are not free-T4 inputs. Verify coverage and foreign needs."""
        users=(request['from_user_id'],request['to_user_id'])
        reader=SmartDealPlanningService(self._db,self._catalog,lambda:now)
        try:
            inputs=reader.build_pairwise_inputs(users[0])
        except ValueError:
            return False
        partner=next((p for p in inputs.subject.eligible_partners if p.user_id==users[1]),None)
        if partner is None:
            return False
        all_positions=identity.low_to_high+identity.high_to_low
        albums={a for a,_,_ in all_positions}
        if not albums.issubset(partner.album_ids):
            return False
        catalogs={album:frozenset(self._catalog(album)) for album in albums}
        inventory=InventoryReadService(self._db)
        snapshots={(user,album):inventory.snapshot(user,album,tuple(c for a,c,_ in all_positions if a==album))
                   for album in albums for user in users}
        bindings=reader._binding_rows(users)
        foreign={user:{(b.album_id,b.sticker_code) for b in reader._project_bindings(user,now,[r for r in bindings if user in (r['requester_user_id'],r['partner_user_id'])])
                       if b.request_id!=request['id'] and b.direction=='incoming' and b.incoming_committed_quantity}
                 for user in users}
        for giver,receiver,pieces in ((identity.low_user_id,identity.high_user_id,identity.low_to_high),
                                     (identity.high_user_id,identity.low_user_id,identity.high_to_low)):
            for album,code,quantity in pieces:
                giving=snapshots[giver,album].sticker(code)
                receiving=snapshots[receiver,album].sticker(code)
                if (code not in catalogs[album] or not giving.balance_is_valid
                        or giving.reserved<quantity or not receiving.missing or (album,code) in foreign[receiver]):
                    return False
        return True

    def _verify_accepted(self, request, now):
        trade,rows=self._release._materialized(request)
        if (request['status']!='accepted' or request['accepted_at'] is None
                or trade['lifecycle_state']!='accepted'
                or not utc_instant(request['binding_created_at']) <= utc_instant(request['accepted_at']) < expires_at(request['binding_created_at'])
                or utc_instant(request['accepted_at'])>now
                or any(r['state']!='active' for r in rows)):
            raise ValueError('Inconsistent accepted V1 contract')
        events=self._db.execute('SELECT actor_user_id,occurred_at FROM trade_events WHERE trade_id=? AND event_type=?',
                                (trade['id'],SMART_ACCEPTED_EVENT)).fetchall()
        if (len(events)!=1 or events[0]['actor_user_id']!=request['to_user_id']
                or utc_instant(events[0]['occurred_at'])!=utc_instant(request['accepted_at'])):
            raise ValueError('Inconsistent acceptance event')
        return trade['id']

    def _record_acceptance(self, request, trade_id, actor, now):
        # Reuse the existing Smart accept lifecycle event. There is no accepted
        # notification in the closed catalog; do not invent a type or callback.
        if self._db.execute('SELECT 1 FROM trade_events WHERE trade_id=? AND event_type=?',
                            (trade_id,SMART_ACCEPTED_EVENT)).fetchone():
            raise ValueError('Pending request already has acceptance event')
        self._db.execute('''INSERT INTO trade_events(trade_id,event_type,actor_user_id,payload_json,occurred_at)
            VALUES (?,?,?,?,?)''',(trade_id,SMART_ACCEPTED_EVENT,actor,json.dumps({'source':'smartdeal_v1'},sort_keys=True),now.isoformat(timespec='microseconds')))

    def _accept_locked(self, request_id, actor, now):
        request=self._db.execute('SELECT * FROM trade_requests WHERE id=?',(request_id,)).fetchone()
        if request is None:return AcceptanceResult(AcceptanceCode.NOT_FOUND,request_id)
        if request['contract_type']!=SMARTDEAL_V1_CONTRACT:return AcceptanceResult(AcceptanceCode.NOT_V1,request_id)
        if type(actor) is not int or actor!=request['to_user_id']:
            return AcceptanceResult(AcceptanceCode.UNAUTHORIZED,request_id)
        if request['status']=='accepted':
            return AcceptanceResult(AcceptanceCode.ALREADY_ACCEPTED,request_id,self._verify_accepted(request,now))
        if request['status']!='open':return AcceptanceResult(AcceptanceCode.NOT_PENDING,request_id)
        if request['accepted_at'] is not None:raise ValueError('Open request already carries acceptance time')
        if now >= expires_at(request['binding_created_at']):
            self._release._release_locked(request_id,'expired',None,now)
            return AcceptanceResult(AcceptanceCode.EXPIRED,request_id)
        identity=self._requests.identity_for_request(request_id)
        matching=self._lookup(identity)
        if matching is None or matching['id']!=request_id:
            raise ValueError('No unique active opportunity instance')
        trade_id=self._requests._assert_complete(request_id,identity,now)
        # Also reject foreign crosslinks / shipping that a position-only read
        # cannot establish. Reuse T5b materialization, without performing release.
        self._release._materialized(request)
        if request['from_confirmed']!=0 or request['to_confirmed']!=0:
            raise ValueError('Pending V1 confirmation flags are inconsistent')
        if not self._currently_executable(request,identity,now):
            return AcceptanceResult(AcceptanceCode.STALE,request_id,trade_id)
        updated=self._db.execute("""UPDATE trade_requests SET status='accepted',accepted_at=?
            WHERE id=? AND contract_type=? AND status='open' AND accepted_at IS NULL""",
            (now.isoformat(timespec='microseconds'),request_id,SMARTDEAL_V1_CONTRACT))
        if updated.rowcount!=1:raise ValueError('Concurrent request transition')
        self._db.execute("UPDATE trades SET lifecycle_state='accepted',updated_at=? WHERE id=?",
                         (now.isoformat(timespec='microseconds'),trade_id))
        self._record_acceptance(request,trade_id,actor,now)
        fresh=self._db.execute('SELECT * FROM trade_requests WHERE id=?',(request_id,)).fetchone()
        self._verify_accepted(fresh,now)
        self._requests._assert_projected(request['from_user_id'],actor,identity,now)
        return AcceptanceResult(AcceptanceCode.ACCEPTED,request_id,trade_id)
