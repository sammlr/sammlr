"""Read-only global planning inputs. No matching, allocation or lifecycle writes."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from services.smartdeal_expiry import expires_at
from services.albums import all_codes
from services.album_privacy import AlbumPrivacyService
from services.community import CommunityService
from services.inventory_availability import LegacyAvailabilityCalculator
from services.trade_contracts import SMARTDEAL_V1_CONTRACT, request_contract_type


@dataclass(frozen=True, order=True)
class PlanningPiece:
    album_id: str
    sticker_code: str
    user_album_id: int
    quantity: int


@dataclass(frozen=True)
class PlanningAlbum:
    album_id: str
    user_album_id: int
    catalog_codes: tuple[str, ...]


@dataclass(frozen=True)
class PlanningPartner:
    user_id: int
    album_ids: tuple[str, ...]


@dataclass(frozen=True)
class PlanningBinding:
    request_id: int
    trade_id: int
    position_id: int
    album_id: str
    sticker_code: str
    direction: str
    quantity: int
    contract_type: str
    valid: bool
    stored_reserved_quantity: int
    reserved_quantity: int
    incoming_committed_quantity: int
    reason: str


@dataclass(frozen=True)
class PlanningState:
    user_id: int
    missing: tuple[PlanningPiece, ...]
    needs: tuple[PlanningPiece, ...]
    outgoing_supply: tuple[PlanningPiece, ...]
    incoming_committed_needs: tuple[PlanningPiece, ...]
    eligible_partners: tuple[PlanningPartner, ...]
    album_context: tuple[PlanningAlbum, ...]
    reservation_context: tuple[PlanningBinding, ...]


@dataclass(frozen=True)
class PartnerPlanningInventory:
    """Canonical partner pieces restricted to the subject's permitted albums."""
    user_id: int
    needs: tuple[PlanningPiece, ...]
    outgoing_supply: tuple[PlanningPiece, ...]


@dataclass(frozen=True)
class PairwisePlanningInputs:
    subject: PlanningState
    partners: tuple[PartnerPlanningInventory, ...]


def _instant(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SmartDealPlanningService:
    """V21 reader with a single SQLite snapshot and bounded batch queries.

    catalog_provider is the canonical all_codes adapter, injectable for fixtures.
    General profile/album visibility is not a trade-pool permission: the existing
    AlbumPrivacyService pool gate deliberately permits private collectors in pool.
    No foreign inventory/profile data is exposed, only eligible IDs/common albums.
    """

    def __init__(self, connection, catalog_provider=all_codes, now_provider=None):
        self._connection = connection
        self._catalog = catalog_provider
        self._now = now_provider or (lambda: datetime.now(timezone.utc))

    def build(self, user_id):
        user_id = int(user_id)
        owns_transaction = not self._connection.in_transaction
        if owns_transaction:
            self._connection.execute("BEGIN")
        try:
            return self._build(user_id, _instant(self._now()))
        finally:
            # End only our read transaction, never commit/rollback caller writes.
            if owns_transaction:
                self._connection.rollback()

    def _build(self, user_id, now):
        db = self._connection
        owner = db.execute("SELECT account_state FROM users WHERE id=?", (user_id,)).fetchone()
        if owner is None or owner[0] != "active":
            raise ValueError("Planning requires an active existing user")
        memberships = db.execute(
            "SELECT ua.id,ua.album_id FROM user_albums ua "
            "JOIN albums a ON a.id=ua.album_id WHERE ua.user_id=? ORDER BY ua.album_id",
            (user_id,),
        ).fetchall()
        privacy = AlbumPrivacyService(db)
        pool = privacy.trade_pool_user_ids_by_album([r["album_id"] for r in memberships])
        albums = tuple(
            PlanningAlbum(r["album_id"], r["id"], tuple(sorted(set(self._catalog(r["album_id"])))))
            for r in memberships if user_id in pool[r["album_id"]]
        )
        album_ids = {a.album_id for a in albums}
        candidates = {p for a in albums for p in pool[a.album_id]}
        allowed = CommunityService(db).interactable_user_ids(user_id, candidates)
        partners = tuple(PlanningPartner(p, tuple(a.album_id for a in albums if p in pool[a.album_id]))
                         for p in sorted(allowed))
        quantities = {(r["album_id"], r["sticker_code"]): r["quantity"] for r in db.execute(
            "SELECT album_id,sticker_code,quantity FROM stickers WHERE user_id=?", (user_id,)
        )}
        bindings = self._bindings(user_id, now)
        reserved = defaultdict(int, {
            (r["album_id"], r["sticker_code"]): r["quantity"]
            for r in db.execute(
                "SELECT album_id,sticker_code,SUM(quantity) AS quantity "
                "FROM trade_reservations WHERE user_id=? AND state='active' "
                "GROUP BY album_id,sticker_code", (user_id,)
            )
        })
        missing, needs, supply, incoming = self._pieces(albums, quantities, bindings, reserved)
        return PlanningState(user_id, missing, needs, supply, incoming,
                             partners, albums, tuple(b for b in bindings if b.album_id in album_ids))

    @staticmethod
    def _pieces(albums, quantities, bindings, reserved):
        committed = set()
        for binding in bindings:
            key = (binding.album_id, binding.sticker_code)
            if binding.direction == "outgoing":
                reserved[key] -= binding.stored_reserved_quantity - binding.reserved_quantity
            elif binding.incoming_committed_quantity:
                committed.add(key)
        missing, needs, supply, incoming = [], [], [], []
        for album in albums:
            for code in album.catalog_codes:
                key = (album.album_id, code)
                availability = LegacyAvailabilityCalculator.from_quantity(
                    quantities.get(key, 0), reserved=reserved[key]
                )
                if availability.physical == 0:
                    piece = PlanningPiece(album.album_id, code, album.user_album_id, 1)
                    missing.append(piece)
                    (incoming if key in committed else needs).append(piece)
                if availability.available:
                    supply.append(PlanningPiece(album.album_id, code, album.user_album_id,
                                                availability.available))
        return tuple(missing), tuple(needs), tuple(supply), tuple(incoming)

    def _bindings(self, user_id, now):
        return self._project_bindings(user_id, now, self._binding_rows((user_id,)))

    def _binding_rows(self, user_ids, *, request_id=None):
        placeholders = ','.join('?' for _ in user_ids)
        request_filter = ' AND q.id=?' if request_id is not None else ''
        parameters = (*user_ids, *user_ids) + ((request_id,) if request_id is not None else ())
        return self._connection.execute(f"""
            SELECT p.id AS position_id,p.trade_id,p.album_id,p.sticker_code,
                   p.from_user_id,p.to_user_id,p.quantity,
                   t.requester_user_id,t.partner_user_id,t.lifecycle_state,
                   q.id AS request_id,q.status,q.created_at,q.contract_type,
                   q.binding_created_at,q.accepted_at,
                   r.quantity AS reserved_quantity,r.state AS reservation_state,
                   COALESCE(s.requester_shipped,0) AS requester_shipped,
                   COALESCE(s.partner_shipped,0) AS partner_shipped,
                   COALESCE(receipt.requester_received,0) AS requester_received,
                   COALESCE(receipt.partner_received,0) AS partner_received,
                   COALESCE(problem.initial_received_quantity,0)
                     + COALESCE(problem.resolution_received_quantity,0) AS received_quantity
            FROM trades t
            JOIN trade_requests q ON q.id=t.legacy_trade_request_id
            JOIN trade_positions p ON p.trade_id=t.id
            LEFT JOIN trade_reservations r ON r.trade_position_id=p.id
            LEFT JOIN trade_shipping_status s ON s.trade_id=t.id
            LEFT JOIN trade_receipt_status receipt ON receipt.trade_id=t.id
            LEFT JOIN trade_receipt_report_positions problem ON problem.trade_position_id=p.id
            WHERE (t.requester_user_id IN ({placeholders}) OR t.partner_user_id IN ({placeholders})){request_filter}
            ORDER BY q.id,p.id
        """, parameters).fetchall()

    @staticmethod
    def _project_bindings(user_id, now, rows):
        groups = defaultdict(list)
        for row in rows:
            groups[row["request_id"]].append(row)
        result = []
        active_states = {"accepted", "partially_shipped", "shipped", "partially_received", "problem_open"}
        for positions in groups.values():
            head = positions[0]
            kind = request_contract_type(head)
            v1 = kind == SMARTDEAL_V1_CONTRACT
            sent = bool(head["requester_shipped"] or head["partner_shipped"])
            valid = head["status"] == "accepted" and head["lifecycle_state"] in active_states
            reason = "active" if valid else "not_binding"
            if v1 and head["status"] == "open":
                # Consume only explicit, fully materialized
                # bilateral position bindings; never infer them from old JSON.
                complete = all(r["reservation_state"] == "active"
                               and r["reserved_quantity"] == r["quantity"] for r in positions)
                directions = {(r["from_user_id"], r["to_user_id"]) for r in positions}
                pair = (head["requester_user_id"], head["partner_user_id"])
                complete = complete and directions == {pair, pair[::-1]}
                try:
                    expiry = expires_at(head["binding_created_at"])
                    bound = _instant(head["binding_created_at"])
                    timely = bound <= now < expiry
                except (ValueError, TypeError) as error:
                    raise ValueError("V1 binding requires valid persistent timestamps") from error
                if not complete or head["binding_created_at"] is None:
                    raise ValueError("Incomplete V1 position binding; no executable planning input")
                if sent or head["lifecycle_state"] != "open" or head["accepted_at"] is not None:
                    raise ValueError("Open V1 binding has an inconsistent lifecycle")
                valid = timely
                reason = "open_v1_binding" if valid else "invalid_or_expired_v1_binding"
            for row in positions:
                outgoing = row["from_user_id"] == user_id
                incoming = row["to_user_id"] == user_id
                if not outgoing and not incoming:
                    raise ValueError("Position does not belong to the trade participants")
                held = row["quantity"] if row["reservation_state"] == "active" else 0
                if held and row["reserved_quantity"] != row["quantity"]:
                    raise ValueError("Reservation quantity differs from the frozen position")
                # Preserve actual legacy active reservations exactly as Inventory
                # does. Only explicit V1 terminal/expired bindings are ineffective.
                effective_held = held if not v1 or valid or sent else 0
                giver_shipped = row["requester_shipped"] if row["from_user_id"] == row["requester_user_id"] else row["partner_shipped"]
                receiver_done = row["requester_received"] if row["to_user_id"] == row["requester_user_id"] else row["partner_received"]
                remaining = max(row["quantity"] - row["received_quantity"], 0)
                incoming_quantity = int(bool(valid and incoming and not receiver_done and remaining
                                             and (held or giver_shipped)))
                result.append(PlanningBinding(
                    row["request_id"], row["trade_id"], row["position_id"], row["album_id"],
                    row["sticker_code"], "outgoing" if outgoing else "incoming", row["quantity"],
                    kind, bool(valid), held, effective_held, incoming_quantity, reason,
                ))
        return tuple(sorted(result, key=lambda b: (b.album_id, b.sticker_code, b.request_id, b.position_id)))

    def build_pairwise_inputs(self, user_id):
        """Additive batch reader: no per-partner SQL or second eligibility policy.

        A single clock/snapshot covers the subject and every permitted partner.
        Partner inventories are internal domain inputs, not a public read endpoint.
        """
        user_id = int(user_id)
        owns_transaction = not self._connection.in_transaction
        if owns_transaction:
            self._connection.execute("BEGIN")
        try:
            now = _instant(self._now())
            subject = self._build(user_id, now)
            ids = tuple(p.user_id for p in subject.eligible_partners)
            if not ids:
                return PairwisePlanningInputs(subject, ())
            placeholders = ','.join('?' for _ in ids)
            memberships = defaultdict(dict)
            for row in self._connection.execute(
                f"SELECT id,user_id,album_id FROM user_albums WHERE user_id IN ({placeholders})", ids
            ):
                memberships[row['user_id']][row['album_id']] = row['id']
            quantities = defaultdict(dict)
            for row in self._connection.execute(
                f"SELECT user_id,album_id,sticker_code,quantity FROM stickers WHERE user_id IN ({placeholders})", ids
            ):
                quantities[row['user_id']][(row['album_id'],row['sticker_code'])] = row['quantity']
            reserved = defaultdict(lambda: defaultdict(int))
            for row in self._connection.execute(
                f"SELECT user_id,album_id,sticker_code,SUM(quantity) AS quantity "
                f"FROM trade_reservations WHERE user_id IN ({placeholders}) AND state='active' "
                "GROUP BY user_id,album_id,sticker_code", ids
            ):
                reserved[row['user_id']][(row['album_id'],row['sticker_code'])] = row['quantity']
            binding_rows = defaultdict(list)
            allowed_ids = set(ids)
            for row in self._binding_rows(ids):
                for participant in {row['requester_user_id'],row['partner_user_id']} & allowed_ids:
                    binding_rows[participant].append(row)
            catalogs = {a.album_id:a.catalog_codes for a in subject.album_context}
            participants = []
            for partner in subject.eligible_partners:
                albums = tuple(PlanningAlbum(a, memberships[partner.user_id][a], catalogs[a])
                               for a in partner.album_ids)
                bindings = self._project_bindings(partner.user_id, now, binding_rows[partner.user_id])
                _, needs, supply, _ = self._pieces(albums, quantities[partner.user_id], bindings,
                                                  reserved[partner.user_id])
                participants.append(PartnerPlanningInventory(partner.user_id, needs, supply))
            return PairwisePlanningInputs(subject, tuple(participants))
        finally:
            if owns_transaction:
                self._connection.rollback()
