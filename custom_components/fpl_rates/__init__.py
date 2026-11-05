"""FPL Published Rates integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import FPLRatesCoordinator


@dataclass
class FPLRuntimeData:
    """Runtime data for one config entry."""

    coordinator: FPLRatesCoordinator


FPLConfigEntry = ConfigEntry[FPLRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: FPLConfigEntry
) -> bool:
    """Set up FPL Published Rates."""
    coordinator = FPLRatesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = FPLRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FPLConfigEntry
) -> bool:
    """Unload the integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _reload_entry(
    hass: HomeAssistant, entry: FPLConfigEntry
) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
