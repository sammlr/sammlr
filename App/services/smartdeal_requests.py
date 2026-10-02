"""Internal V1 request creation, serialized with existing SQLite writers.

No route, accept, release, inventory booking, notification or worker. V21's
normalized positions and reservations are the sole package/binding truth.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import sqlite3

from services.smartdeal_expiry import expires_at
from services.albums import all_codes
from services.inventory import InventoryReadService
from services.smartdeal_identity import SmartDealOpportunityIdentity
from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_suggestions import SmartDealSuggestionValidator, SuggestionStatus, _payload_identity
from services.trade_contracts import SMARTDEAL_V1_CONTRACT


class SmartDealRequestCode(str, Enum):
    CREATED = 'CREATED'
    ALREADY_CREATED = 'ALREADY_CREATED'
    EXISTING_COUNTERPART_REQUEST = 'EXISTING_COUNTERPART_REQUEST'
    INVALID_PAYLOAD = 'INVALID_PAYLOAD'
    STALE = 'STALE'
    LIMIT_REACHED = 'LIMIT_REACHED'
    BUSY = 'BUSY'


@dataclass(frozen=True)
class SmartDealRequestResult:
    code: SmartDealRequestCode
    request_id: int | None = None
    trade_id: int | None = None


def _instant(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return (result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result).astimezone(timezone.utc)


class SmartDealRequestService:
    def __init__(self, connection, catalog_provider=all_codes, now_provider=None):
        self._db = connection
        self._catalog = catalog_provider
        self._now = now_provider or (lambda: datetime.now(timezone.utc))

    def identity_for_request(self, request_id):
        """Internal read adapter; exact identity derived, never a digest-only match.

        No request/view authorization is implied. Caller owns read isolation when
        this adapter is used independently. Legacy requests are explicitly rejected.
        """
        request = self._db.execute('SELECT * FROM trade_requests WHERE id=?', (request_id,)).fetchone()
        if request is None or request['contract_type'] != SMARTDEAL_V1_CONTRACT:
            raise ValueError('Not a SmartDeal V1 request')
        rows = self._db.execute('''SELECT p.* FROM trade_positions p JOIN trades t ON t.id=p.trade_id
            WHERE t.legacy_trade_request_id=? ORDER BY p.from_user_id,p.album_id,p.sticker_code''', (request_id,)).fetchall()
        low, high = sorted((request['from_user_id'], request['to_user_id']))
        a, b = [], []
        for row in rows:
            pair = (row['from_user_id'], row['to_user_id'])
            if pair not in ((low,high),(high,low)):
                raise ValueError('Stored position has foreign participants')
            (a if pair == (low,high) else b).append((row['album_id'],row['sticker_code'],row['quantity']))
        identity = SmartDealOpportunityIdentity(low,high,tuple(a),tuple(b))
        if len(a) < 5 or len(a) != len(b):
            raise ValueError('Stored V1 package is not balanced/minimum sized')
        return identity

    def _assert_complete(self, request_id, identity, instant):
        if self.identity_for_request(request_id) != identity:
            raise ValueError('Persisted package differs from validated package')
        row = self._db.execute('''SELECT q.*,t.id AS trade_id,t.lifecycle_state,
                t.requester_user_id,t.partner_user_id FROM trade_requests q
            JOIN trades t ON t.legacy_trade_request_id=q.id WHERE q.id=?''', (request_id,)).fetchone()
        if (row is None or row['status'] != 'open' or row['lifecycle_state'] != 'open'
                or row['accepted_at'] is not None or row['binding_created_at'] is None
                or row['requester_user_id'] != row['from_user_id'] or row['partner_user_id'] != row['to_user_id']
                or not _instant(row['binding_created_at']) <= instant < expires_at(row['binding_created_at'])):
            raise ValueError('Incomplete or expired open V1 binding')
        held = self._db.execute('''SELECT p.*,r.quantity AS held,r.state,r.user_id AS holder,
                r.album_id AS held_album,r.sticker_code AS held_code,r.created_at AS held_at,
                r.trade_id AS reservation_trade FROM trade_positions p
            LEFT JOIN trade_reservations r ON r.trade_position_id=p.id WHERE p.trade_id=?''', (row['trade_id'],)).fetchall()
        if len(held) != 2*len(identity.low_to_high) or any(
                p['state'] != 'active' or p['held'] != p['quantity'] or p['holder'] != p['from_user_id']
                or p['held_album'] != p['album_id'] or p['held_code'] != p['sticker_code']
                or p['reservation_trade'] != row['trade_id'] or p['held_at'] != row['binding_created_at']
                for p in held):
            raise ValueError('Incomplete bilateral reservation')
        return row['trade_id']

    def _assert_projected(self, actor, partner_id, identity, instant):
        inputs = SmartDealPlanningService(self._db,self._catalog,lambda:instant).build_pairwise_inputs(actor)
        other = next(p for p in inputs.partners if p.user_id == partner_id)
        by_user = {actor:inputs.subject,partner_id:other}
        for receiver, positions in ((identity.high_user_id,identity.low_to_high), (identity.low_user_id,identity.high_to_low)):
            needs = {(p.album_id,p.sticker_code) for p in by_user[receiver].needs}
            if any((a,c) in needs for a,c,_ in positions):
                raise ValueError('New incoming promise did not bind canonical need')

    def create_from_suggestion(self, suggestion, actor_user_id):
        """Own one BEGIN IMMEDIATE through COMMIT; reject caller transactions.

        Same-actor retry returns its existing open binding; a counterpart attempt
        returns the existing request without accepting it. Neither creates writes.
        Fresh creates always revalidate inside the acquired write transaction.
        """
        if self._db.in_transaction:
            raise ValueError('Creation requires an idle connection; caller transaction preserved')
        identity = _payload_identity(suggestion)
        if identity is None or type(actor_user_id) is not int or actor_user_id not in (identity.low_user_id,identity.high_user_id):
            return SmartDealRequestResult(SmartDealRequestCode.INVALID_PAYLOAD)
        started = False
        try:
            self._db.execute('BEGIN IMMEDIATE')
            started = True
            instant = _instant(self._now())
            result = self._create_locked(suggestion, actor_user_id, identity, instant)
            self._db.commit()
            return result
        except BaseException as error:
            if started:
                self._db.rollback()
            if isinstance(error,sqlite3.OperationalError) and getattr(error,'sqlite_errorcode',0)&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):
                return SmartDealRequestResult(SmartDealRequestCode.BUSY)
            raise

    def _create_locked(self, suggestion, actor_user_id, identity, instant):
        """Internal composition for T6b; caller owns BEGIN IMMEDIATE and payload validation.

        No nested transaction or commit. Public T5a behavior remains unchanged.
        """
        if not self._db.in_transaction:
            raise ValueError('Creation requires the caller write transaction')
        stamp = instant.isoformat(timespec='microseconds')
        partner = identity.high_user_id if actor_user_id == identity.low_user_id else identity.low_user_id
        candidates = self._db.execute('''SELECT id,from_user_id,binding_created_at FROM trade_requests
            WHERE contract_type=? AND status='open' AND
            ((from_user_id=? AND to_user_id=?) OR (from_user_id=? AND to_user_id=?)) ORDER BY id''',
            (SMARTDEAL_V1_CONTRACT,actor_user_id,partner,partner,actor_user_id)).fetchall()
        matches = [r for r in candidates if self.identity_for_request(r['id']) == identity]
        if len(matches) > 1:
            raise ValueError('Multiple existing open bindings of the same package')
        if matches:
            row = matches[0]
            if instant >= expires_at(row['binding_created_at']):
                return SmartDealRequestResult(SmartDealRequestCode.STALE)
            trade_id = self._assert_complete(row['id'],identity,instant)
            code = SmartDealRequestCode.ALREADY_CREATED if row['from_user_id'] == actor_user_id else SmartDealRequestCode.EXISTING_COUNTERPART_REQUEST
            return SmartDealRequestResult(code,row['id'],trade_id)
        validator = SmartDealSuggestionValidator(self._db,self._catalog,lambda:instant)
        validation = validator.validate(suggestion,actor_user_id)
        if validation.status != SuggestionStatus.VALID:
            return SmartDealRequestResult(SmartDealRequestCode(validation.status.value))
        rows = self._db.execute("SELECT binding_created_at FROM trade_requests WHERE contract_type=? AND status='open' AND from_user_id=?",
                                (SMARTDEAL_V1_CONTRACT,actor_user_id)).fetchall()
        if sum(instant < expires_at(r['binding_created_at']) for r in rows) >= 3:
            return SmartDealRequestResult(SmartDealRequestCode.LIMIT_REACHED)
        # T2a read projection ignores expired V1 holds. Until T5b releases
        # them physically, never overdraw the shared stored-reservation view.
        inventory = InventoryReadService(self._db)
        for album in suggestion.involved_albums:
            states = inventory.matching_states((identity.low_user_id,identity.high_user_id),album,
                tuple(c for a,c,_ in identity.low_to_high+identity.high_to_low if a == album))
            for giver,positions in ((identity.low_user_id,identity.low_to_high),(identity.high_user_id,identity.high_to_low)):
                if any(c not in states[giver].available_codes for a,c,_ in positions if a == album):
                    return SmartDealRequestResult(SmartDealRequestCode.STALE)
        # Required legacy album column is context only. Empty legacy code
        # arrays cannot misrepresent a multi-album V1 package to old accept.
        request_id = self._db.execute('''INSERT INTO trade_requests
            (album_id,from_user_id,to_user_id,give_codes,get_codes,status,created_at,
             from_confirmed,to_confirmed,contract_type)
            VALUES (?,?,?,'[]','[]','open',?,0,0,?)''',
            (suggestion.involved_albums[0],actor_user_id,partner,stamp,SMARTDEAL_V1_CONTRACT)).lastrowid
        trade_id = self._db.execute('''INSERT INTO trades
            (legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state,created_at,updated_at)
            VALUES (?,?,?,'open',?,?)''', (request_id,actor_user_id,partner,stamp,stamp)).lastrowid
        positions = [(giver,receiver,a,c,q) for giver,receiver,items in
            ((identity.low_user_id,identity.high_user_id,identity.low_to_high),
             (identity.high_user_id,identity.low_user_id,identity.high_to_low)) for a,c,q in items]
        self._db.execute('''INSERT INTO trade_positions
            (trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity,created_at)
            SELECT ?,json_extract(value,'$[0]'),json_extract(value,'$[1]'),json_extract(value,'$[2]'),
                json_extract(value,'$[3]'),json_extract(value,'$[4]'),? FROM json_each(?)''',
            (trade_id,stamp,json.dumps(positions,ensure_ascii=False)))
        self._db.execute('''INSERT INTO trade_reservations
            (trade_id,trade_position_id,user_id,album_id,sticker_code,quantity,state,created_at)
            SELECT trade_id,id,from_user_id,album_id,sticker_code,quantity,'active',?
            FROM trade_positions WHERE trade_id=? ORDER BY id''', (stamp,trade_id))
        self._db.execute('UPDATE trade_requests SET binding_created_at=? WHERE id=?', (stamp,request_id))
        self._assert_complete(request_id,identity,instant)
        self._assert_projected(actor_user_id,partner,identity,instant)
        return SmartDealRequestResult(SmartDealRequestCode.CREATED,request_id,trade_id)
