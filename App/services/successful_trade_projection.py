from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json


@dataclass(frozen=True)
class SuccessfulTradePositionDTO:
    album_id: str
    sticker_code: str
    quantity: int
    giver_user_id: int
    receiver_user_id: int


@dataclass(frozen=True)
class SuccessfulTradeDTO:
    canonical_trade_id: str
    source_type: str
    source_id: int
    trade_request_id: int
    user_id: int
    partner_user_id: int
    completed_at: str | None
    given_positions: tuple[SuccessfulTradePositionDTO, ...]
    received_positions: tuple[SuccessfulTradePositionDTO, ...]
    given_quantity_total: int
    received_quantity_total: int
    involved_album_ids: tuple[str, ...]

    @property
    def largest_trade_score(self):
        return max(self.given_quantity_total, self.received_quantity_total)


@dataclass(frozen=True)
class SuccessfulTradeAggregateDTO:
    successful_trade_count: int
    given_quantity_total: int
    received_quantity_total: int
    distinct_partner_count: int
    largest_trade: SuccessfulTradeDTO | None


class SuccessfulTradeProjectionService:
    """Canonical read-only projection of unambiguously successful trades."""

    def __init__(self, connection):
        self._connection = connection

    @staticmethod
    def legacy_is_successful(request_status):
        return request_status == "completed"

    @staticmethod
    def lifecycle_is_successful(
        request_status, lifecycle_state, requester_received,
        partner_received, has_open_problem_remainder,
    ):
        return (
            request_status == "completed"
            and lifecycle_state == "completed"
            and bool(requester_received)
            and bool(partner_received)
            and not has_open_problem_remainder
        )

    def trades_for_user(self, user_id, album_id=None):
        user_id = int(user_id)
        trades = self._load(user_id)
        if album_id is not None:
            trades = tuple(
                self.trade_for_album(trade, str(album_id))
                for trade in trades
                if str(album_id) in trade.involved_album_ids
            )
        return trades

    def count_for_user(self, user_id, album_id=None):
        return len(self.trades_for_user(user_id, album_id))

    def aggregates_for_user(self, user_id, album_id=None):
        trades = self.trades_for_user(user_id, album_id)
        return SuccessfulTradeAggregateDTO(
            successful_trade_count=len(trades),
            given_quantity_total=sum(
                trade.given_quantity_total for trade in trades
            ),
            received_quantity_total=sum(
                trade.received_quantity_total for trade in trades
            ),
            distinct_partner_count=len({
                trade.partner_user_id for trade in trades
            }),
            largest_trade=self._largest_trade(trades),
        )

    @classmethod
    def _largest_trade(cls, trades):
        if not trades:
            return None
        ranked = sorted(trades, key=lambda trade: trade.canonical_trade_id)
        ranked.sort(
            key=lambda trade: cls._completion_rank(trade.completed_at),
            reverse=True,
        )
        ranked.sort(
            key=lambda trade: trade.largest_trade_score,
            reverse=True,
        )
        return ranked[0]

    @staticmethod
    def _completion_rank(value):
        if not value:
            return (0, 0.0)
        try:
            parsed = datetime.fromisoformat(
                str(value).strip().replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return (0, 0.0)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (1, parsed.astimezone(timezone.utc).timestamp())

    def _load(self, user_id):
        lifecycle_available = self._table_exists("trades")
        receipt_available = self._table_exists("trade_receipt_status")
        lifecycle_columns = (
            "lifecycle.id AS lifecycle_id, "
            "lifecycle.requester_user_id, lifecycle.partner_user_id, "
            "lifecycle.lifecycle_state, lifecycle.completed_at"
            if lifecycle_available else
            "NULL AS lifecycle_id, NULL AS requester_user_id, "
            "NULL AS partner_user_id, NULL AS lifecycle_state, "
            "NULL AS completed_at"
        )
        receipt_columns = (
            "receipt.requester_received, receipt.partner_received"
            if receipt_available else
            "NULL AS requester_received, NULL AS partner_received"
        )
        lifecycle_join = (
            "LEFT JOIN trades lifecycle "
            "ON lifecycle.legacy_trade_request_id=request.id"
            if lifecycle_available else ""
        )
        receipt_join = (
            "LEFT JOIN trade_receipt_status receipt "
            "ON receipt.trade_id=lifecycle.id"
            if lifecycle_available and receipt_available else ""
        )
        rows = self._connection.execute(
            f"""
            SELECT request.id AS request_id, request.album_id,
                   request.from_user_id, request.to_user_id,
                   request.give_codes, request.get_codes, request.status,
                   {lifecycle_columns}, {receipt_columns}
            FROM trade_requests request
            {lifecycle_join}
            {receipt_join}
            WHERE request.from_user_id=? OR request.to_user_id=?
            ORDER BY request.id
            """,
            (user_id, user_id),
        ).fetchall()

        lifecycle_ids = tuple(
            int(row["lifecycle_id"])
            for row in rows if row["lifecycle_id"] is not None
        )
        positions = self._lifecycle_positions(lifecycle_ids)
        unresolved = self._unresolved_lifecycle_ids(lifecycle_ids)
        projected = []
        for row in rows:
            if not self.legacy_is_successful(row["status"]):
                continue
            if row["from_user_id"] == row["to_user_id"]:
                continue
            if row["lifecycle_id"] is None:
                trade = self._legacy_trade(row, user_id)
            else:
                trade = self._lifecycle_trade(
                    row, user_id, positions, unresolved
                )
            if trade is not None:
                projected.append(trade)

        # Stable canonical ID is the secondary key. A known, later completion
        # sorts before an earlier one; unknown Legacy timestamps remain NULL
        # and sort last instead of being reconstructed from request creation.
        projected.sort(key=lambda trade: trade.canonical_trade_id)
        projected.sort(
            key=lambda trade: self._completion_rank(trade.completed_at),
            reverse=True,
        )
        return tuple(projected)

    def _legacy_trade(self, row, user_id):
        give_codes = self._legacy_codes(row["give_codes"])
        get_codes = self._legacy_codes(row["get_codes"])
        if give_codes is None or get_codes is None:
            return None
        positions = self._legacy_positions(
            row["album_id"], row["from_user_id"], row["to_user_id"],
            give_codes, get_codes,
        )
        return self._perspective(
            canonical_trade_id=f"legacy:{int(row['request_id']):020d}",
            source_type="legacy",
            source_id=int(row["request_id"]),
            trade_request_id=int(row["request_id"]),
            user_id=user_id,
            from_user_id=int(row["from_user_id"]),
            to_user_id=int(row["to_user_id"]),
            completed_at=None,
            positions=positions,
        )

    def _lifecycle_trade(self, row, user_id, positions, unresolved):
        lifecycle_id = int(row["lifecycle_id"])
        if not self.lifecycle_is_successful(
            row["status"], row["lifecycle_state"],
            row["requester_received"], row["partner_received"],
            lifecycle_id in unresolved,
        ):
            return None
        # Request and lifecycle identities must describe exactly the same two
        # parties. Ambiguous or foreign position ownership fails closed.
        if (
            row["requester_user_id"] != row["from_user_id"]
            or row["partner_user_id"] != row["to_user_id"]
        ):
            return None
        trade_positions = positions.get(lifecycle_id, ())
        parties = {int(row["from_user_id"]), int(row["to_user_id"])}
        if any(
            {position.giver_user_id, position.receiver_user_id} != parties
            or position.giver_user_id == position.receiver_user_id
            for position in trade_positions
        ):
            return None
        return self._perspective(
            canonical_trade_id=f"lifecycle:{lifecycle_id:020d}",
            source_type="lifecycle",
            source_id=lifecycle_id,
            trade_request_id=int(row["request_id"]),
            user_id=user_id,
            from_user_id=int(row["from_user_id"]),
            to_user_id=int(row["to_user_id"]),
            completed_at=row["completed_at"],
            positions=trade_positions,
        )

    @staticmethod
    def _perspective(
        *, canonical_trade_id, source_type, source_id, trade_request_id, user_id,
        from_user_id, to_user_id, completed_at, positions,
    ):
        if user_id == from_user_id:
            partner_user_id = to_user_id
        elif user_id == to_user_id:
            partner_user_id = from_user_id
        else:
            return None
        given = tuple(
            position for position in positions
            if position.giver_user_id == user_id
        )
        received = tuple(
            position for position in positions
            if position.receiver_user_id == user_id
        )
        albums = tuple(sorted({
            position.album_id for position in (*given, *received)
        }))
        return SuccessfulTradeDTO(
            canonical_trade_id=canonical_trade_id,
            source_type=source_type,
            source_id=source_id,
            trade_request_id=trade_request_id,
            user_id=user_id,
            partner_user_id=partner_user_id,
            completed_at=completed_at,
            given_positions=given,
            received_positions=received,
            given_quantity_total=sum(position.quantity for position in given),
            received_quantity_total=sum(
                position.quantity for position in received
            ),
            involved_album_ids=albums,
        )

    @staticmethod
    def _legacy_codes(value):
        try:
            decoded = json.loads(value or "[]")
        except (TypeError, ValueError):
            return None
        if not isinstance(decoded, list) or any(
            not isinstance(code, (str, int)) or not str(code).strip()
            for code in decoded
        ):
            return None
        return tuple(str(code) for code in decoded)

    @staticmethod
    def _legacy_positions(
        album_id, from_user_id, to_user_id, give_codes, get_codes
    ):
        grouped = {}
        for code, giver, receiver in (
            *((code, from_user_id, to_user_id) for code in give_codes),
            *((code, to_user_id, from_user_id) for code in get_codes),
        ):
            key = (str(album_id), code, int(giver), int(receiver))
            grouped[key] = grouped.get(key, 0) + 1
        return tuple(
            SuccessfulTradePositionDTO(
                album_id=key[0], sticker_code=key[1], quantity=quantity,
                giver_user_id=key[2], receiver_user_id=key[3],
            )
            for key, quantity in sorted(grouped.items())
        )

    def _lifecycle_positions(self, lifecycle_ids):
        if not lifecycle_ids or not self._table_exists("trade_positions"):
            return {}
        placeholders = ",".join("?" for _ in lifecycle_ids)
        rows = self._connection.execute(
            f"""
            SELECT trade_id, album_id, sticker_code, quantity,
                   from_user_id, to_user_id
            FROM trade_positions
            WHERE trade_id IN ({placeholders})
            ORDER BY trade_id, id
            """,
            lifecycle_ids,
        ).fetchall()
        result = {}
        for row in rows:
            result.setdefault(int(row["trade_id"]), []).append(
                SuccessfulTradePositionDTO(
                    album_id=str(row["album_id"]),
                    sticker_code=str(row["sticker_code"]),
                    quantity=int(row["quantity"]),
                    giver_user_id=int(row["from_user_id"]),
                    receiver_user_id=int(row["to_user_id"]),
                )
            )
        return {key: tuple(value) for key, value in result.items()}

    def _unresolved_lifecycle_ids(self, lifecycle_ids):
        if not lifecycle_ids or not self._table_exists("trade_receipt_reports"):
            return set()
        placeholders = ",".join("?" for _ in lifecycle_ids)
        position_join = ""
        position_gate = "0"
        if self._table_exists("trade_receipt_report_positions"):
            position_join = (
                "LEFT JOIN trade_receipt_report_positions rp "
                "ON rp.report_id=report.id"
            )
            position_gate = (
                "COALESCE(rp.expected_quantity, 0) > "
                "COALESCE(rp.initial_received_quantity, 0) + "
                "COALESCE(rp.resolution_received_quantity, 0)"
            )
        rows = self._connection.execute(
            f"""
            SELECT DISTINCT report.trade_id
            FROM trade_receipt_reports report
            {position_join}
            WHERE report.trade_id IN ({placeholders})
              AND (report.state='open' OR {position_gate})
            """,
            lifecycle_ids,
        ).fetchall()
        return {int(row[0]) for row in rows}

    @staticmethod
    def trade_for_album(trade, album_id):
        given = tuple(
            position for position in trade.given_positions
            if position.album_id == album_id
        )
        received = tuple(
            position for position in trade.received_positions
            if position.album_id == album_id
        )
        return replace(
            trade,
            given_positions=given,
            received_positions=received,
            given_quantity_total=sum(position.quantity for position in given),
            received_quantity_total=sum(
                position.quantity for position in received
            ),
            involved_album_ids=(album_id,),
        )

    def _table_exists(self, table_name):
        return self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone() is not None
