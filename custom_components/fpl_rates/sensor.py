"""Sensors for FPL Published Rates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from . import FPLConfigEntry
from .const import (
    CENTS_PER_KWH,
    CONF_MONTHLY_ENERGY_ENTITY,
    CURRENCY_PER_KWH,
)
from .entity import FPLEntity
from .schedule import TARIFF_TIME_ZONE, period_info


@dataclass(frozen=True, kw_only=True)
class FPLSensorDescription(SensorEntityDescription):
    """Describe a coordinator-backed sensor."""

    data_key: str


RATE_SENSORS = (
    FPLSensorDescription(
        key="effective",
        data_key="effective",
        name="Publication effective",
        icon="mdi:calendar-check",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FPLSensorDescription(
        key="base_charge",
        data_key="base_charge",
        name="RS-1 monthly base charge",
        native_unit_of_measurement="$",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
    ),
    FPLSensorDescription(
        key="minimum_base_bill",
        data_key="minimum_base_bill",
        name="Minimum base bill",
        native_unit_of_measurement="$",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
    ),
    *(
        FPLSensorDescription(
            key=key,
            data_key=key,
            name=name,
            native_unit_of_measurement=CENTS_PER_KWH,
            suggested_display_precision=3,
        )
        for key, name in (
            ("rs1_total_first_1000_cents", "RS-1 rate first 1000 kWh"),
            ("rs1_total_over_1000_cents", "RS-1 rate over 1000 kWh"),
            (
                "rtr_total_on_peak_first_1000_cents",
                "RTR-1 on-peak rate first 1000 kWh",
            ),
            (
                "rtr_total_off_peak_first_1000_cents",
                "RTR-1 off-peak rate first 1000 kWh",
            ),
            (
                "rtr_total_on_peak_over_1000_cents",
                "RTR-1 on-peak rate over 1000 kWh",
            ),
            (
                "rtr_total_off_peak_over_1000_cents",
                "RTR-1 off-peak rate over 1000 kWh",
            ),
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FPLConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        FPLRateSensor(coordinator, entry, desc) for desc in RATE_SENSORS
    ]
    entities.extend(
        [
            FPLPeriodSensor(entry),
            FPLCurrentRateSensor(coordinator, entry),
            FPLCurrentRateCentsSensor(coordinator, entry),
        ]
    )

    energy_entity = entry.options.get(
        CONF_MONTHLY_ENERGY_ENTITY,
        entry.data.get(CONF_MONTHLY_ENERGY_ENTITY),
    )
    if energy_entity:
        entities.append(
            FPLEstimatedBillSensor(coordinator, entry, energy_entity)
        )
    async_add_entities(entities)


class FPLRateSensor(FPLEntity, SensorEntity):
    entity_description: FPLSensorDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"fpl_rates_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get(self.entity_description.data_key)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key != "effective":
            return None
        return {
            "source_url": self.coordinator.data.get("source_url"),
            "source_sha256": self.coordinator.data.get("source_sha256"),
            "auto_discovered": self.coordinator.data.get("discovered_url"),
        }


class _MinuteSensor(SensorEntity):
    """A tariff schedule sensor updated once per minute."""

    _attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._tick, timedelta(minutes=1)
            )
        )

    @callback
    def _tick(self, now: datetime) -> None:
        self.async_write_ha_state()


class FPLPeriodSensor(_MinuteSensor):
    _attr_has_entity_name = True
    _attr_name = "RTR-1 current period"
    _attr_unique_id = "fpl_rates_rtr1_current_period"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["Peak", "Off-peak"]

    def __init__(self, entry: FPLConfigEntry) -> None:
        self._attr_device_info = entry.runtime_data.coordinator and {
            "identifiers": {("fpl_rates", entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Florida Power & Light",
            "model": "Published residential rates",
        }

    @property
    def native_value(self) -> str:
        return period_info(dt_util.now()).period

    @property
    def extra_state_attributes(self):
        info = period_info(dt_util.now())
        return {
            "is_peak": info.is_peak,
            "season": info.season,
            "holiday": info.holiday,
            "weekend": info.weekend,
            "schedule": info.schedule,
            "next_period": info.next_period,
            "next_change": info.next_change.isoformat(),
            "timezone": str(TARIFF_TIME_ZONE),
        }


class _CurrentRateBase(FPLEntity, _MinuteSensor):
    """Current RTR-1 price based on period and first tier."""

    @property
    def _cents(self) -> float:
        key = (
            "rtr_total_on_peak_first_1000_cents"
            if period_info(dt_util.now()).is_peak
            else "rtr_total_off_peak_first_1000_cents"
        )
        return float(self.coordinator.data[key])

    @property
    def extra_state_attributes(self):
        info = period_info(dt_util.now())
        return {
            "period": info.period,
            "usage_tier": "First 1,000 kWh",
            "note": (
                "Taxes, franchise fees, gross-receipts tax, and "
                "account-specific charges are excluded."
            ),
        }


class FPLCurrentRateSensor(_CurrentRateBase):
    _attr_name = "RTR-1 current energy price"
    _attr_unique_id = "fpl_rates_rtr1_current_energy_price"
    _attr_native_unit_of_measurement = CURRENCY_PER_KWH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 5

    @property
    def native_value(self) -> Decimal:
        return Decimal(str(round(self._cents / 100, 6)))


class FPLCurrentRateCentsSensor(_CurrentRateBase):
    _attr_name = "RTR-1 current rate"
    _attr_unique_id = "fpl_rates_rtr1_current_rate_cents"
    _attr_native_unit_of_measurement = CENTS_PER_KWH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    @property
    def native_value(self) -> float:
        return round(self._cents, 6)


class FPLEstimatedBillSensor(FPLEntity, SensorEntity):
    """Estimate RS-1 energy charges from a monthly-energy entity."""

    _attr_name = "Estimated RS-1 monthly bill"
    _attr_unique_id = "fpl_rates_estimated_rs1_monthly_bill"
    _attr_native_unit_of_measurement = "$"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry, energy_entity: str) -> None:
        super().__init__(coordinator, entry)
        self._energy_entity = energy_entity

    @property
    def available(self) -> bool:
        state = self.hass.states.get(self._energy_entity)
        return super().available and state is not None

    def _monthly_kwh(self) -> float | None:
        state = self.hass.states.get(self._energy_entity)
        if state is None:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        unit = state.attributes.get("unit_of_measurement")
        if unit == "Wh":
            value /= 1000
        elif unit == "MWh":
            value *= 1000
        return max(value, 0)

    @property
    def native_value(self) -> float | None:
        kwh = self._monthly_kwh()
        if kwh is None:
            return None
        low = self.coordinator.data["rs1_total_first_1000_cents"]
        high = self.coordinator.data["rs1_total_over_1000_cents"]
        energy_cents = min(kwh, 1000) * low + max(kwh - 1000, 0) * high
        subtotal = self.coordinator.data["base_charge"] + energy_cents / 100
        minimum = self.coordinator.data.get("minimum_base_bill")
        if minimum is not None:
            subtotal = max(subtotal, minimum)
        return round(subtotal, 2)

    @property
    def extra_state_attributes(self):
        return {
            "source_energy_entity": self._energy_entity,
            "monthly_kwh": self._monthly_kwh(),
            "tariff": "RS-1",
            "excludes": (
                "taxes, franchise fees, gross-receipts tax, deposits, "
                "late fees, and other account-specific charges"
            ),
        }
