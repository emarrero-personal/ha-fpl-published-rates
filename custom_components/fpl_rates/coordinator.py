"""Data coordinator for FPL Published Rates."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_AUTO_DISCOVER,
    CONF_PDF_URL,
    CONF_RATES_PAGE,
    CONF_UPDATE_HOURS,
    DEFAULT_PDF_URL,
    DEFAULT_RATES_PAGE,
    DEFAULT_UPDATE_HOURS,
)
from .parser import (
    TariffParseError,
    discover_residential_pdf,
    parse_tariff_pdf,
)

_LOGGER = logging.getLogger(__name__)


class FPLRatesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate discovery, download, parsing, and validation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        hours = entry.options.get(
            CONF_UPDATE_HOURS,
            entry.data.get(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="FPL Published Rates",
            update_interval=timedelta(hours=int(hours)),
            always_update=False,
        )

    def _option(self, key: str, default: Any) -> Any:
        return self.entry.options.get(
            key, self.entry.data.get(key, default)
        )

    async def _get_text(self, url: str) -> str:
        session = async_get_clientsession(self.hass)
        async with session.get(
            url,
            timeout=30,
            headers={"User-Agent": "HomeAssistant-FPL-Rates/1.0"},
        ) as response:
            response.raise_for_status()
            return await response.text()

    async def _get_bytes(self, url: str) -> bytes:
        session = async_get_clientsession(self.hass)
        async with session.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "HomeAssistant-FPL-Rates/1.0",
                "Accept": "application/pdf",
            },
        ) as response:
            response.raise_for_status()
            body = await response.read()
        if not body.startswith(b"%PDF"):
            raise TariffParseError("FPL source did not return a PDF")
        return body

    async def _async_update_data(self) -> dict[str, Any]:
        configured_url = self._option(CONF_PDF_URL, DEFAULT_PDF_URL)
        source_url = configured_url
        discovered = False

        try:
            if self._option(CONF_AUTO_DISCOVER, True):
                rates_page = self._option(
                    CONF_RATES_PAGE, DEFAULT_RATES_PAGE
                )
                html = await self._get_text(rates_page)
                discovered_url = discover_residential_pdf(html, rates_page)
                if discovered_url:
                    source_url = discovered_url
                    discovered = source_url != configured_url

            pdf = await self._get_bytes(source_url)
            tariff = await self.hass.async_add_executor_job(
                parse_tariff_pdf, pdf, source_url, discovered
            )
            parsed = tariff.to_dict()
        except Exception as err:
            raise UpdateFailed(
                f"Unable to retrieve or parse FPL rates: {err}"
            ) from err

        previous = self.data or {}
        important = (
            "base_charge",
            "minimum_base_bill",
            "rs1_total_first_1000_cents",
            "rs1_total_over_1000_cents",
            "rtr_total_on_peak_first_1000_cents",
            "rtr_total_off_peak_first_1000_cents",
        )
        if previous and any(
            previous.get(key) != parsed.get(key) for key in important
        ):
            persistent_notification.async_create(
                self.hass,
                (
                    "FPL's published residential rates changed. Review the "
                    "FPL Published Rates entities and diagnostics."
                ),
                title="FPL residential rates changed",
                notification_id="fpl_rates_changed",
            )
        return parsed
