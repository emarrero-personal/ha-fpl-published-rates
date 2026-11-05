"""Binary sensor for FPL RTR-1 peak state."""

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from . import FPLConfigEntry
from .schedule import period_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FPLConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([FPLPeakBinarySensor(entry)])


class FPLPeakBinarySensor(BinarySensorEntity):
    """True during FPL RTR-1 on-peak hours."""

    _attr_has_entity_name = True
    _attr_name = "RTR-1 peak"
    _attr_unique_id = "fpl_rates_rtr1_peak"
    _attr_icon = "mdi:transmission-tower"
    _attr_should_poll = False

    def __init__(self, entry: FPLConfigEntry) -> None:
        self._attr_device_info = {
            "identifiers": {("fpl_rates", entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Florida Power & Light",
            "model": "Published residential rates",
        }

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

    @property
    def is_on(self) -> bool:
        return period_info(dt_util.now()).is_peak
