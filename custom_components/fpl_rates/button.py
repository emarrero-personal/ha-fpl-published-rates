"""Refresh button for FPL Published Rates."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FPLConfigEntry
from .entity import FPLEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FPLConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [FPLRefreshButton(entry.runtime_data.coordinator, entry)]
    )


class FPLRefreshButton(FPLEntity, ButtonEntity):
    _attr_name = "Refresh rates"
    _attr_unique_id = "fpl_rates_refresh"
    _attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
