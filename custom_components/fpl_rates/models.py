"""Models for FPL Published Rates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TariffData:
    """Parsed residential tariff data."""

    effective: str
    source_url: str
    source_sha256: str
    discovered_url: bool
    base_charge: float
    minimum_base_bill: float | None
    rs1_energy_first_1000: float
    rs1_energy_over_1000: float
    conservation: float
    capacity: float
    environmental: float
    storm_protection: float
    fuel_first_1000: float
    fuel_over_1000: float
    transition_credit: float
    rtr_on_peak_energy_adjustment: float
    rtr_off_peak_energy_adjustment: float
    rtr_on_peak_fuel_adjustment: float
    rtr_off_peak_fuel_adjustment: float

    def to_dict(self) -> dict[str, Any]:
        """Return raw and calculated values."""
        data = asdict(self)
        rs1_first = (
            self.rs1_energy_first_1000
            + self.conservation
            + self.capacity
            + self.environmental
            + self.storm_protection
            + self.fuel_first_1000
            + self.transition_credit
        )
        rs1_over = (
            self.rs1_energy_over_1000
            + self.conservation
            + self.capacity
            + self.environmental
            + self.storm_protection
            + self.fuel_over_1000
            + self.transition_credit
        )
        on_adjustment = (
            self.rtr_on_peak_energy_adjustment
            + self.rtr_on_peak_fuel_adjustment
        )
        off_adjustment = (
            self.rtr_off_peak_energy_adjustment
            + self.rtr_off_peak_fuel_adjustment
        )

        data.update(
            {
                "rs1_total_first_1000_cents": round(rs1_first, 6),
                "rs1_total_over_1000_cents": round(rs1_over, 6),
                "rtr_on_peak_adjustment_cents": round(on_adjustment, 6),
                "rtr_off_peak_adjustment_cents": round(off_adjustment, 6),
                "rtr_total_on_peak_first_1000_cents": round(
                    rs1_first + on_adjustment, 6
                ),
                "rtr_total_off_peak_first_1000_cents": round(
                    rs1_first + off_adjustment, 6
                ),
                "rtr_total_on_peak_over_1000_cents": round(
                    rs1_over + on_adjustment, 6
                ),
                "rtr_total_off_peak_over_1000_cents": round(
                    rs1_over + off_adjustment, 6
                ),
            }
        )
        return data
