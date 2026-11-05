"""Diagnostics for FPL Published Rates."""

from typing import Any

from homeassistant.core import HomeAssistant

from . import FPLConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FPLConfigEntry
) -> dict[str, Any]:
    """Return non-sensitive diagnostics."""
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "last_exception": (
            str(coordinator.last_exception)
            if coordinator.last_exception
            else None
        ),
        "parsed_tariff": dict(coordinator.data or {}),
    }
