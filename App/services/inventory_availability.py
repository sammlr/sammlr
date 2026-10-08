from dataclasses import dataclass


@dataclass(frozen=True)
class AvailabilityDTO:
    physical: int
    assigned: int
    reserved: int
    available: int
    incoming_transit: int
    reason_code: str
    explanation: str

    physical_missing: int = 0

    @property
    def is_available(self):
        return self.available > 0

    @property
    def reservable(self):
        # S11 only names the amount that could be reserved later. It does not
        # create or enforce a reservation.
        return self.available

    @property
    def balance_is_valid(self):
        return (
            self.physical >= 0
            and self.assigned >= 0
            and self.reserved >= 0
            and self.available >= 0
            and self.incoming_transit >= 0
            and self.physical
            == self.assigned + self.reserved + self.physical_missing + self.available
        )


class LegacyAvailabilityCalculator:
    """S08 compatibility projection for today's quantity-only model."""

    @staticmethod
    def from_quantity(quantity, reserved=0, incoming_transit=0, physical_missing=0):
        physical = max(quantity, 0)
        assigned = min(physical, 1)
        reserved = max(reserved, 0)
        incoming_transit = max(incoming_transit, 0)
        physical_missing = max(physical_missing, 0)
        available = max(physical - assigned - reserved - physical_missing, 0)

        if physical == 0 and incoming_transit > 0:
            reason_code = "incoming_transit"
            explanation = (
                f"Unterwegs: {incoming_transit} erwartete Kopie(n) sind noch "
                "nicht im physischen Bestand."
            )
        elif physical == 0:
            reason_code = "not_physical"
            explanation = (
                "Nicht verfügbar: Es ist keine physische Kopie vorhanden."
            )
        elif reserved > 0 and available == 0:
            reason_code = "fully_reserved"
            explanation = (
                "Nicht verfügbar: Alle physischen Überschusskopien sind "
                "verbindlich reserviert."
            )
        elif reserved > 0:
            reason_code = "partially_reserved"
            explanation = (
                f"Verfügbar: {available} Überschusskopie(n) bleiben nach "
                f"{reserved} Reservierung(en) frei."
            )
        elif available == 0:
            reason_code = "assigned_only"
            explanation = (
                "Nicht verfügbar: Die einzige physische Kopie ist dem "
                "heutigen Einzelalbum zugeordnet."
            )
        else:
            reason_code = "legacy_surplus_available"
            explanation = (
                f"Verfügbar: {available} physische Überschusskopie(n) sind "
                "im heutigen Modell weder zugeordnet noch reserviert."
            )

        if physical_missing:
            reason_code = "physical_missing_hold"
            explanation = f"{physical_missing} physisch fehlende Kopie(n) sind für neue Tausche gesperrt."
        return AvailabilityDTO(
            physical=physical,
            physical_missing=physical_missing,
            assigned=assigned,
            reserved=reserved,
            available=available,
            incoming_transit=incoming_transit,
            reason_code=reason_code,
            explanation=explanation,
        )
