from dataclasses import dataclass
from enum import Enum


class InventoryGuardCode(str, Enum):
    OK = "OK"
    BELOW_BOUND_STOCK = "BELOW_BOUND_STOCK"
    INVALID_OPERATION = "INVALID_OPERATION"


@dataclass(frozen=True)
class InventoryGuardDecisionDTO:
    code: InventoryGuardCode
    current_quantity: int
    requested_quantity: int
    bound_quantity: int
    explanation: str

    @property
    def allowed(self):
        return self.code is InventoryGuardCode.OK


class NoInventoryBindings:
    """Default S12 source: the current application has no bound stock."""

    def minimum_quantity(self, user_id, album_id, sticker_code):
        return 0


class InventoryGuard:
    """Decides whether a normalized inventory quantity may be stored."""

    def __init__(self, binding_source=None):
        self._binding_source = binding_source or NoInventoryBindings()

    def evaluate(
        self,
        user_id,
        album_id,
        sticker_code,
        current_quantity,
        requested_quantity,
    ):
        if not self._is_quantity(current_quantity) or not self._is_quantity(
            requested_quantity
        ):
            return InventoryGuardDecisionDTO(
                code=InventoryGuardCode.INVALID_OPERATION,
                current_quantity=current_quantity,
                requested_quantity=requested_quantity,
                bound_quantity=0,
                explanation=(
                    "Ungültige Mengenänderung: Aktuelle und angeforderte "
                    "Menge müssen nichtnegative ganze Zahlen sein."
                ),
            )

        bound_quantity = self._binding_source.minimum_quantity(
            user_id, album_id, sticker_code
        )
        if not self._is_quantity(bound_quantity):
            return InventoryGuardDecisionDTO(
                code=InventoryGuardCode.INVALID_OPERATION,
                current_quantity=current_quantity,
                requested_quantity=requested_quantity,
                bound_quantity=bound_quantity,
                explanation=(
                    "Ungültige Bindungsquelle: Die gebundene Mindestmenge "
                    "muss eine nichtnegative ganze Zahl sein."
                ),
            )

        if requested_quantity >= current_quantity:
            return self._ok(
                current_quantity,
                requested_quantity,
                bound_quantity,
                "Zulässig: Die Änderung unterschreitet keinen vorhandenen Bestand.",
            )

        if requested_quantity < bound_quantity:
            return InventoryGuardDecisionDTO(
                code=InventoryGuardCode.BELOW_BOUND_STOCK,
                current_quantity=current_quantity,
                requested_quantity=requested_quantity,
                bound_quantity=bound_quantity,
                explanation=(
                    f"Nicht zulässig: Mindestens {bound_quantity} Kopie(n) "
                    "sind gebunden."
                ),
            )

        return self._ok(
            current_quantity,
            requested_quantity,
            bound_quantity,
            "Zulässig: Die gebundene Mindestmenge bleibt erhalten.",
        )

    @staticmethod
    def _is_quantity(value):
        return type(value) is int and value >= 0

    @staticmethod
    def _ok(current_quantity, requested_quantity, bound_quantity, explanation):
        return InventoryGuardDecisionDTO(
            code=InventoryGuardCode.OK,
            current_quantity=current_quantity,
            requested_quantity=requested_quantity,
            bound_quantity=bound_quantity,
            explanation=explanation,
        )
