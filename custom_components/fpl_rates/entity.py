"""Shared FPL entity."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FPLConfigEntry
from .const import DOMAIN
from .coordinator import FPLRatesCoordinator


class FPLEntity(CoordinatorEntity[FPLRatesCoordinator]):
    """Base entity."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: FPLRatesCoordinator, entry: FPLConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Florida Power & Light",
            model="Published residential rates",
            configuration_url=coordinator.data.get("source_url"),
        )
