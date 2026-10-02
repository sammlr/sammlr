from dataclasses import dataclass

from services.inventory_guard import InventoryGuard, InventoryGuardDecisionDTO
from services.trade_reservations import ActiveReservationBindings


@dataclass(frozen=True)
class InventoryMutationDTO:
    user_id: int
    album_id: str
    sticker_code: str
    previous_quantity: int
    quantity: int
    duplicates: int
    created: bool
    deleted: bool
    guard_decision: InventoryGuardDecisionDTO

    @property
    def changed(self):
        return self.previous_quantity != self.quantity

    @property
    def allowed(self):
        return self.guard_decision.allowed

    @property
    def error_code(self):
        return self.guard_decision.code.value


class InventoryWriteService:
    """Adapter for the existing quantity/duplicates write behavior."""

    def __init__(self, connection, guard=None):
        self._connection = connection
        self._guard = guard or InventoryGuard(
            ActiveReservationBindings(connection)
        )

    def _row(self, user_id, album_id, sticker_code):
        return self._connection.execute(
            """
            SELECT * FROM stickers
            WHERE user_id=? AND album_id=? AND sticker_code=?
            """,
            (user_id, album_id, sticker_code),
        ).fetchone()

    def _store(
        self,
        user_id,
        album_id,
        sticker_code,
        row,
        quantity,
        insert_duplicates=None,
    ):
        previous_quantity = row["quantity"] if row else 0
        quantity = max(quantity, 0)
        guard_decision = self._guard.evaluate(
            user_id,
            album_id,
            sticker_code,
            previous_quantity,
            quantity,
        )

        if not guard_decision.allowed:
            return InventoryMutationDTO(
                user_id=user_id,
                album_id=album_id,
                sticker_code=sticker_code,
                previous_quantity=previous_quantity,
                quantity=previous_quantity,
                duplicates=row["duplicates"] if row else 0,
                created=False,
                deleted=False,
                guard_decision=guard_decision,
            )

        duplicates = max(quantity - 1, 0)
        created = row is None and quantity > 0
        deleted = row is not None and quantity == 0

        if deleted:
            self._connection.execute(
                "DELETE FROM stickers WHERE id=?",
                (row["id"],),
            )
        elif row is not None:
            self._connection.execute(
                "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                (quantity, duplicates, row["id"]),
            )
        elif created:
            if insert_duplicates is not None:
                duplicates = insert_duplicates
            self._connection.execute(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, "owned", ?, ?)
                """,
                (user_id, album_id, sticker_code, duplicates, quantity),
            )

        if previous_quantity != quantity:
            from services.community import UserActivityService
            UserActivityService(self._connection).touch(user_id)

        return InventoryMutationDTO(
            user_id=user_id,
            album_id=album_id,
            sticker_code=sticker_code,
            previous_quantity=previous_quantity,
            quantity=quantity,
            duplicates=duplicates,
            created=created,
            deleted=deleted,
            guard_decision=guard_decision,
        )

    def set_quantity(self, user_id, album_id, sticker_code, quantity):
        row = self._row(user_id, album_id, sticker_code)
        return self._store(
            user_id, album_id, sticker_code, row, max(quantity, 0)
        )

    def change_quantity(self, user_id, album_id, sticker_code, delta):
        row = self._row(user_id, album_id, sticker_code)
        previous_quantity = row["quantity"] if row else 0
        return self._store(
            user_id,
            album_id,
            sticker_code,
            row,
            max(previous_quantity + delta, 0),
            insert_duplicates=0,
        )

    def add(self, user_id, album_id, sticker_code, amount=1):
        return self.change_quantity(
            user_id, album_id, sticker_code, max(amount, 0)
        )

    def remove(self, user_id, album_id, sticker_code, amount=1):
        return self.change_quantity(
            user_id, album_id, sticker_code, -max(amount, 0)
        )
