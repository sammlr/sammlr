"""Internal pending V1 releases; no acceptance, booking or public route."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import sqlite3

from services.smartdeal_expiry import expires_at, utc_instant
from services.smartdeal_requests import SmartDealRequestService
from services.smartdeal_planning import SmartDealPlanningService
from services.trade_contracts import SMARTDEAL_V1_CONTRACT
from services.trade_reservations import TradeReservationService
from services.typed_notifications import TypedNotificationService


class ReleaseCode(str, Enum):
    RELEASED = 'RELEASED'
    ALREADY_RELEASED = 'ALREADY_RELEASED'
    NOT_DUE = 'NOT_DUE'
    NOT_PENDING = 'NOT_PENDING'
    NOT_V1 = 'NOT_V1'
    NOT_FOUND = 'NOT_FOUND'
    UNAUTHORIZED = 'UNAUTHORIZED'
    BUSY = 'BUSY'


@dataclass(frozen=True)
class ReleaseResult:
    code: ReleaseCode
    request_id: int
    status: str | None = None
    released_count: int = 0


class SmartDealReleaseService:
    def __init__(self, connection, now_provider=None):
        self._db = connection
        self._now = now_provider or (lambda: datetime.now(timezone.utc))

    def _transaction(self, operation):
        if self._db.in_transaction:
            raise ValueError('Release requires an idle connection; caller transaction preserved')
        started = False
        try:
            self._db.execute('BEGIN IMMEDIATE')
            started = True
            result = operation(utc_instant(self._now()))
            self._db.commit()
            return result
        except BaseException:
            if started:
                self._db.rollback()
            raise

    def _command(self, request_id, reason, actor=None):
        if type(request_id) is not int or request_id <= 0:
            raise ValueError('Canonical positive request ID required')
        try:
            return self._transaction(lambda now: self._release_locked(request_id, reason, actor, now))
        except sqlite3.OperationalError as error:
            if getattr(error, 'sqlite_errorcode', 0) & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                return ReleaseResult(ReleaseCode.BUSY, request_id)
            raise

    def decline(self, request_id, actor_user_id):
        return self._command(request_id, 'declined', actor_user_id)

    def withdraw(self, request_id, actor_user_id):
        return self._command(request_id, 'withdrawn', actor_user_id)

    def expire(self, request_id):
        """Trusted maintenance command, not a user-authorized endpoint."""
        return self._command(request_id, 'expired')

    def sweep(self):
        """Explicit maintenance pass; one clock, one atomic write transaction.

        No read-side writes, cron, global optimizer or silent error suppression.
        Malformed pending data aborts the pass; caller can diagnose/retry.
        """
        def run(now):
            rows = self._db.execute("""SELECT id,binding_created_at FROM trade_requests
                WHERE contract_type=? AND status='open' AND accepted_at IS NULL ORDER BY id""",
                (SMARTDEAL_V1_CONTRACT,)).fetchall()
            return tuple(self._release_locked(r['id'], 'expired', None, now)
                         for r in rows if now >= expires_at(r['binding_created_at']))
        return self._transaction(run)

    def _materialized(self, request):
        """Validate both sides and cross-table ownership before any release."""
        trade = self._db.execute('SELECT * FROM trades WHERE legacy_trade_request_id=?', (request['id'],)).fetchone()
        if (trade is None or trade['requester_user_id'] != request['from_user_id']
                or trade['partner_user_id'] != request['to_user_id'] or trade['completed_at'] is not None):
            raise ValueError('Inconsistent V1 request/lifecycle ownership')
        identity = SmartDealRequestService(self._db).identity_for_request(request['id'])
        rows = self._db.execute('''SELECT r.*,p.trade_id AS position_trade,p.from_user_id,p.to_user_id,
                p.album_id AS position_album,p.sticker_code AS position_code,p.quantity AS position_quantity
            FROM trade_reservations r LEFT JOIN trade_positions p ON p.id=r.trade_position_id
            WHERE r.id IN (
                SELECT id FROM trade_reservations WHERE trade_id=?
                UNION
                SELECT r2.id FROM trade_positions p2 JOIN trade_reservations r2
                    ON r2.trade_position_id=p2.id WHERE p2.trade_id=?
            ) ORDER BY r.id''', (trade['id'], trade['id'])).fetchall()
        if len(rows) != 2 * len(identity.low_to_high) or any(
                r['trade_id'] != trade['id'] or r['position_trade'] != trade['id']
                or r['user_id'] != r['from_user_id'] or r['album_id'] != r['position_album']
                or r['sticker_code'] != r['position_code'] or r['quantity'] != r['position_quantity']
                for r in rows):
            raise ValueError('Incomplete or foreign V1 reservations')
        for table, flags in (('trade_shipping_status', ('requester_shipped','partner_shipped')),
                             ('trade_receipt_status', ('requester_received','partner_received'))):
            row = self._db.execute(f'SELECT * FROM {table} WHERE trade_id=?', (trade['id'],)).fetchone()
            if row and any(row[f] for f in flags):
                raise ValueError('Pending release cannot undo physical lifecycle')
        return trade, rows

    def _verify_released(self, request_id, now):
        request = self._db.execute('SELECT * FROM trade_requests WHERE id=?', (request_id,)).fetchone()
        trade, rows = self._materialized(request)
        if (request['accepted_at'] is not None or request['status'] not in ('declined','cancelled','expired')
                or trade['lifecycle_state'] != request['status']
                or any(r['state'] != 'released' or not r['released_at'] or not r['release_reason'] for r in rows)):
            raise ValueError('Incomplete terminal V1 release')
        # Verify this request's projection, independently of current eligibility
        # or other contracts. No assertion that a still-foreign-bound need is free.
        reader = SmartDealPlanningService(self._db)
        users = (request['from_user_id'], request['to_user_id'])
        projected_rows = reader._binding_rows(users, request_id=request_id)
        for user in users:
            bindings = reader._project_bindings(user, now, projected_rows)
            if any(b.request_id == request_id and (b.valid or b.reserved_quantity or b.incoming_committed_quantity)
                   for b in bindings):
                raise ValueError('Terminal request retains planning binding')

    def _release_locked(self, request_id, reason, actor, now):
        """Internal composition point; caller MUST own BEGIN IMMEDIATE.

        Used by this service and CommunityService.block in its existing write TX.
        Does not commit/rollback the caller. No arbitrary external reason/status.
        """
        if not self._db.in_transaction or reason not in ('declined','withdrawn','expired','blocked'):
            raise ValueError('Release needs owned write transaction and known cause')
        request = self._db.execute('SELECT * FROM trade_requests WHERE id=?', (request_id,)).fetchone()
        if request is None:
            return ReleaseResult(ReleaseCode.NOT_FOUND, request_id)
        if request['contract_type'] != SMARTDEAL_V1_CONTRACT:
            return ReleaseResult(ReleaseCode.NOT_V1, request_id)
        allowed = (request['to_user_id'],) if reason == 'declined' else (request['from_user_id'],)
        if reason == 'blocked':
            allowed = (request['from_user_id'], request['to_user_id'])
        if reason != 'expired' and (type(actor) is not int or actor not in allowed):
            return ReleaseResult(ReleaseCode.UNAUTHORIZED, request_id)
        if request['accepted_at'] is not None or request['status'] == 'accepted':
            return ReleaseResult(ReleaseCode.NOT_PENDING, request_id, request['status'])
        if request['status'] in ('declined','cancelled','expired'):
            self._verify_released(request_id, now)
            return ReleaseResult(ReleaseCode.ALREADY_RELEASED, request_id, request['status'])
        if request['status'] != 'open':
            return ReleaseResult(ReleaseCode.NOT_PENDING, request_id, request['status'])
        deadline = expires_at(request['binding_created_at'])
        if now < utc_instant(request['binding_created_at']):
            raise ValueError('Release clock predates binding')
        trade, rows = self._materialized(request)
        if (trade['lifecycle_state'] != 'open' or request['from_confirmed'] != 0 or request['to_confirmed'] != 0
                or any(r['state'] != 'active' for r in rows)):
            raise ValueError('Inconsistent pending V1 binding')
        if reason == 'expired' and now < deadline:
            return ReleaseResult(ReleaseCode.NOT_DUE, request_id, 'open')
        # Once the deadline is reached, an authorized late user action observes
        # expiry, never revives or extends the unanswered request.
        if now >= deadline:
            reason = 'expired'
        status = 'cancelled' if reason in ('withdrawn','blocked') else reason
        changed = self._db.execute("""UPDATE trade_requests SET status=?
            WHERE id=? AND contract_type=? AND status='open' AND accepted_at IS NULL""",
            (status, request_id, SMARTDEAL_V1_CONTRACT))
        if changed.rowcount != 1:
            raise ValueError('Request no longer pending')
        stamp = now.isoformat(timespec='microseconds')
        result = TradeReservationService(self._db).release(request_id, reason, status, released_at=stamp)
        if result.released_count != len(rows):
            raise ValueError('Incomplete supply release')
        self._verify_released(request_id, now)
        if reason == 'declined':
            TypedNotificationService(self._db).notify_request_declined(request_id, actor)
        return ReleaseResult(ReleaseCode.RELEASED, request_id, status, result.released_count)
