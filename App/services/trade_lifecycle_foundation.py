"""Internal persistence primitives; no requests, transitions or UI activation.

All mutations require the explicit IMMEDIATE unit of work. This is not a Send
or Accept service: later commands must add authorization, deadlines and policy.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json

from services.inventory import InventoryReadService
from services.smartdeal_planning import SmartDealPlanningService
from services.trade_planning_compat import LegacyPlanningReadAdapter
from services.trade_contracts import require_trade_operation
from services.trade_v2_rules import balance_groups, valid_balance, mode


def _stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _quantity(value, *, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError('Integer quantity required')
    return value


@dataclass(frozen=True)
class RuleSnapshot:
    """Explicit rule inputs, no profile, address or mutable inventory payload.

    albums: (album_id, proposer_pool, partner_pool, proposer_mode, partner_mode).
    Balance is always evaluated from the frozen original proposer perspective.
    """
    proposer: int
    partner: int
    origin: str
    equal: bool
    albums: tuple
    version: int = 1

    def __post_init__(self):
        if (type(self.version) is not int or self.version != 1 or type(self.proposer) is not int or type(self.partner) is not int
                or min(self.proposer, self.partner) <= 0 or self.proposer == self.partner
                or self.origin not in ('MANUAL', 'SMARTDEAL') or type(self.equal) is not bool
                or (self.origin == 'SMARTDEAL' and not self.equal)):
            raise ValueError('Invalid rule snapshot')
        normalized = tuple(sorted(tuple(a) for a in self.albums))
        if not normalized or len({a[0] for a in normalized}) != len(normalized):
            raise ValueError('Unique album rules required')
        for a in normalized:
            if len(a) != 5 or not isinstance(a[0], str) or not a[0] or a[1:3] != (True, True):
                raise ValueError('Bilateral pool consent required')
            if any(type(v) is not bool for v in a[1:3]):
                raise ValueError('Boolean pool consent required')
            if mode(a[3]) != a[3] or mode(a[4]) != a[4]:
                raise ValueError('Explicit normalized modes required')
        object.__setattr__(self, 'albums', normalized)

    @property
    def groups(self):
        return balance_groups([a[0] for a in self.albums],
                              {a[0]: a[3] for a in self.albums},
                              {a[0]: a[4] for a in self.albums})

    def dumps(self):
        return _json(dict(version=self.version, proposer=self.proposer, partner=self.partner,
                          origin=self.origin, equal=self.equal, albums=self.albums))

    @classmethod
    def loads(cls, payload):
        return cls(**json.loads(payload))

    def validate(self, positions):
        give, receive = [], []
        for giver, receiver, album, code, quantity in positions:
            _quantity(quantity)
            if {giver, receiver} != {self.proposer, self.partner} or not code:
                raise ValueError('Invalid snapshot position')
            (give if giver == self.proposer else receive).extend([album] * quantity)
        if not give or not receive or not valid_balance(give, receive, self.groups, equal=self.equal):
            raise ValueError('Invalid frozen rule balance')


@dataclass(frozen=True)
class LifecycleAvailability:
    supply: int
    physical: int
    target: int
    committed: int
    pending: int
    free_need: int


def lifecycle_availability(db, user_id, album_id, code, *, exclude_revision=None, now=None):
    """Canonical physical supply plus quantity-based new-contract Need view.

    Read-only; callers needing atomic admission must use the write unit of work.
    Trade-v2 consumes this projection; legacy planners retain their own policy.
    """
    now = now or datetime.now(timezone.utc)
    inventory = InventoryReadService(db).snapshot(user_id, album_id, (code,)).sticker(code)
    if not inventory.balance_is_valid:
        raise ValueError('Inconsistent physical reservation balance')
    row = db.execute('SELECT quantity FROM lifecycle_need_targets WHERE user_id=? AND album_id=? AND sticker_code=?',
                     (user_id, album_id, code)).fetchone()
    target = row[0] if row else 1
    reader = SmartDealPlanningService(LegacyPlanningReadAdapter(db))
    rows = reader._binding_rows((user_id,))
    bindings = reader._project_bindings(user_id, now, rows)
    by_id = {r['position_id']: r for r in rows}
    committed = sum(max(b.quantity - by_id[b.position_id]['received_quantity'], 0)
                    for b in bindings if b.album_id == album_id and b.sticker_code == code
                    and b.direction == 'incoming' and b.incoming_committed_quantity)
    quantities = {'pending': 0, 'committed': committed}
    for state, quantity in db.execute('''SELECT c.state,SUM(c.quantity-c.received_quantity)
            FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id
            WHERE p.to_user_id=? AND p.album_id=? AND p.sticker_code=? AND c.state<>'released'
              AND (? IS NULL OR p.revision_id<>?) GROUP BY c.state''',
            (user_id, album_id, code, exclude_revision, exclude_revision)):
        quantities[state] += quantity
    supply = inventory.available
    # Read-only deadline projection. Commands physically release through _expire.
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_requests'").fetchone():
        from services.trade_lifecycle_requests import instant
        for revision, deadline in db.execute("SELECT revision_id,expires_at FROM lifecycle_requests WHERE status='open'"):
            if now < instant(deadline):
                continue
            pending = db.execute("""SELECT COALESCE(SUM(c.quantity),0) FROM lifecycle_need_claims c
                JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id
                WHERE p.revision_id=? AND p.to_user_id=? AND p.album_id=? AND p.sticker_code=?
                  AND c.state='pending' AND (? IS NULL OR p.revision_id<>?)""",
                (revision,user_id,album_id,code,exclude_revision,exclude_revision)).fetchone()[0]
            quantities['pending'] -= pending
            supply += db.execute("""SELECT COALESCE(SUM(h.quantity),0) FROM trade_reservations h
                JOIN lifecycle_supply_bindings b ON b.reservation_id=h.id AND b.is_current=1
                JOIN lifecycle_revision_positions p ON p.id=b.revision_position_id
                WHERE p.revision_id=? AND h.user_id=? AND h.album_id=? AND h.sticker_code=? AND h.state='active'""",
                (revision,user_id,album_id,code)).fetchone()[0]
    free = max(target - inventory.physical - quantities['committed'] - quantities['pending'], 0)
    return LifecycleAvailability(supply, inventory.physical, target,
                                 quantities['committed'], quantities['pending'], free)


class LifecycleFoundation:
    """Storage composition only. No public Send/Accept/Ship command is provided."""
    def __init__(self, connection):
        self.db = connection
        self._writing = False

    @contextmanager
    def transaction(self):
        if self.db.in_transaction or self._writing:
            raise ValueError('Foundation requires its own explicit IMMEDIATE transaction')
        if not self.db.execute('PRAGMA foreign_keys').fetchone()[0]:
            raise ValueError('Foreign keys must be enabled')
        self.db.execute('BEGIN IMMEDIATE')
        self._writing = True
        try:
            yield self
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        finally:
            self._writing = False

    def _write(self, trade_id=None):
        if not self._writing or not self.db.in_transaction:
            raise ValueError('Explicit foundation unit of work required')
        if trade_id is not None:
            require_trade_operation(self.db, trade_id, 'foundation')

    def create_identity(self, proposer, partner, origin='MANUAL'):
        self._write()
        stamp = _stamp()
        trade_id = self.db.execute('''INSERT INTO trades
            (requester_user_id,partner_user_id,lifecycle_state,created_at,updated_at)
            VALUES (?,?,'foundation',?,?)''', (proposer, partner, stamp, stamp)).lastrowid
        self.db.execute('INSERT INTO lifecycle_contracts(trade_id,origin,created_at) VALUES (?,?,?)',
                        (trade_id, origin, stamp))
        for a, b in ((proposer, partner), (partner, proposer)):
            self.db.execute('INSERT INTO lifecycle_directions(trade_id,from_user_id,to_user_id) VALUES (?,?,?)',
                            (trade_id, a, b))
        return trade_id

    def append_revision(self, trade_id, author, positions, kind='original'):
        self._write(trade_id)
        number = self.db.execute('SELECT COALESCE(MAX(number),0)+1 FROM lifecycle_revisions WHERE trade_id=?',
                                 (trade_id,)).fetchone()[0]
        revision = self.db.execute('''INSERT INTO lifecycle_revisions
            (trade_id,number,author_user_id,kind,created_at) VALUES (?,?,?,?,?)''',
            (trade_id, number, author, kind, _stamp())).lastrowid
        for giver, receiver, album, code, quantity in positions:
            _quantity(quantity)
            self.db.execute('''INSERT INTO lifecycle_revision_positions
                (revision_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (?,?,?,?,?,?)''',
                (revision, giver, receiver, album, code, quantity))
        self.db.execute('UPDATE lifecycle_revisions SET sealed=1 WHERE id=?', (revision,))
        return revision

    def store_rule_snapshot(self, revision, snapshot, accepted_at):
        revision_row = self.db.execute('SELECT trade_id,author_user_id,kind FROM lifecycle_revisions WHERE id=?', (revision,)).fetchone()
        if revision_row is None:
            raise ValueError('Unknown revision')
        trade_id, author, kind = revision_row
        self._write(trade_id)
        trade = self.db.execute('SELECT requester_user_id,partner_user_id FROM trades WHERE id=?', (trade_id,)).fetchone()
        origin = self.db.execute('SELECT origin FROM lifecycle_contracts WHERE trade_id=?', (trade_id,)).fetchone()[0]
        if set(trade) != {snapshot.proposer, snapshot.partner} or origin != snapshot.origin:
            raise ValueError('Snapshot contract ownership mismatch')
        if kind in ('original', 'counter') and snapshot.proposer != author:
            raise ValueError('Snapshot must retain the accepted offers proposer perspective')
        if kind == 'reduction':
            previous = self.db.execute('''SELECT s.payload_json FROM lifecycle_contracts c
                JOIN lifecycle_rule_snapshots s ON s.revision_id=c.accepted_revision_id
                WHERE c.trade_id=?''', (trade_id,)).fetchone()
            if previous is None or RuleSnapshot.loads(previous[0]) != snapshot:
                raise ValueError('Reduction must retain the accepted rule frame')
        positions = self.db.execute('''SELECT from_user_id,to_user_id,album_id,sticker_code,quantity
                                      FROM lifecycle_revision_positions WHERE revision_id=?''', (revision,)).fetchall()
        snapshot.validate(positions)
        self.db.execute('INSERT INTO lifecycle_rule_snapshots VALUES (?,1,?,?)',
                        (revision, snapshot.dumps(), accepted_at))

    def bind_pending_quantities(self, revision):
        """Internal binding primitive; not a request (no deadline/quota/UI).

        One unit of work binds own Give in the shared reservation table and own
        Receive claims. Future Send must add current TradeV2Domain validation.
        """
        row = self.db.execute('SELECT trade_id,author_user_id,sealed FROM lifecycle_revisions WHERE id=?',
                              (revision,)).fetchone()
        if row is None or not row[2]:
            raise ValueError('Sealed revision required')
        trade_id, sender, _ = row
        self._write(trade_id)
        rows = self.db.execute('''SELECT id,from_user_id,to_user_id,album_id,sticker_code,quantity
                                 FROM lifecycle_revision_positions WHERE revision_id=?''', (revision,)).fetchall()
        # Validate all quantities before materializing either kind of binding.
        for _, giver, receiver, album, code, quantity in rows:
            available = lifecycle_availability(self.db, sender, album, code)
            if quantity > (available.supply if giver == sender else available.free_need):
                raise ValueError('Insufficient free supply or need')
        for position, giver, receiver, album, code, quantity in rows:
            if giver == sender:
                self.bind_supply_position(position)
            else:
                self.db.execute('''INSERT INTO lifecycle_need_claims
                    (revision_position_id,state,quantity,created_at) VALUES (?,'pending',?,?)''',
                    (position,quantity,_stamp()))

    def bind_supply_position(self, position):
        """Materialize one exact revision position in the shared hold source."""
        row = self.db.execute("""SELECT p.revision_id,r.trade_id,p.from_user_id,p.to_user_id,
            p.album_id,p.sticker_code,p.quantity FROM lifecycle_revision_positions p
            JOIN lifecycle_revisions r ON r.id=p.revision_id WHERE p.id=?""", (position,)).fetchone()
        if row is None:
            raise ValueError('Unknown revision position')
        revision,trade_id,giver,receiver,album,code,quantity = row
        self._write(trade_id)
        existing = self.db.execute("""SELECT p.id,h.id,h.state FROM trade_positions p
            LEFT JOIN trade_reservations h ON h.trade_position_id=p.id
            WHERE p.trade_id=? AND p.from_user_id=? AND p.to_user_id=? AND p.album_id=? AND p.sticker_code=?""",
            (trade_id,giver,receiver,album,code)).fetchone()
        if existing is None:
            stored = self.db.execute("""INSERT INTO trade_positions
                (trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (?,?,?,?,?,?)""",
                (trade_id,giver,receiver,album,code,quantity)).lastrowid
            reservation = self.db.execute("""INSERT INTO trade_reservations
                (trade_id,trade_position_id,user_id,album_id,sticker_code,quantity) VALUES (?,?,?,?,?,?)""",
                (trade_id,stored,giver,album,code,quantity)).lastrowid
        else:
            stored,reservation,state = existing
            if reservation is None or state != 'released':
                raise ValueError('Physical projection must be released before rebind')
            self.db.execute('UPDATE lifecycle_supply_bindings SET is_current=0 WHERE reservation_id=? AND is_current=1', (reservation,))
            self.db.execute('UPDATE trade_positions SET quantity=? WHERE id=?', (quantity,stored))
            self.db.execute("""UPDATE trade_reservations SET quantity=?,state='active',released_at=NULL,release_reason=NULL
                WHERE id=?""", (quantity,reservation))
        self.db.execute('INSERT INTO lifecycle_supply_bindings(reservation_id,revision_position_id) VALUES (?,?)',
                        (reservation,position))

    def release_pending_quantities(self, revision):
        row = self.db.execute('SELECT trade_id FROM lifecycle_revisions WHERE id=?', (revision,)).fetchone()
        if row is None:
            raise ValueError('Unknown revision')
        self._write(row[0])
        if self.db.execute("SELECT 1 FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id WHERE p.revision_id=? AND c.state='committed'", (revision,)).fetchone():
            raise ValueError('Not a pending binding')
        self.db.execute('''UPDATE lifecycle_need_claims SET state='released',released_at=?
            WHERE state='pending' AND revision_position_id IN
              (SELECT id FROM lifecycle_revision_positions WHERE revision_id=?)''', (_stamp(),revision))
        self.db.execute("UPDATE trade_reservations SET state='released',released_at=?,release_reason='foundation_release' WHERE id IN (SELECT b.reservation_id FROM lifecycle_supply_bindings b JOIN lifecycle_revision_positions p ON p.id=b.revision_position_id WHERE p.revision_id=? AND b.is_current=1) AND state='active'",
                        (_stamp(),revision))

    def record_command(self, trade_id, actor, key, operation, payload, result):
        self._write(trade_id)
        digest = hashlib.sha256(_json(payload).encode()).hexdigest()
        old = self.db.execute('''SELECT operation,payload_digest,result_json FROM lifecycle_commands
            WHERE trade_id=? AND actor_user_id=? AND command_key=?''', (trade_id,actor,key)).fetchone()
        if old:
            if (old[0],old[1]) != (operation,digest):
                raise ValueError('Idempotency key reused with different command')
            return json.loads(old[2])
        self.db.execute('INSERT INTO lifecycle_commands VALUES (?,?,?,?,?,?,?)',
                        (trade_id,actor,key,operation,digest,_json(result),_stamp()))
        return result
