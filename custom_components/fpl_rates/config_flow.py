"""Config flow for FPL Published Rates."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_DISCOVER,
    CONF_MONTHLY_ENERGY_ENTITY,
    CONF_NAME,
    CONF_PDF_URL,
    CONF_RATES_PAGE,
    CONF_UPDATE_HOURS,
    DEFAULT_NAME,
    DEFAULT_PDF_URL,
    DEFAULT_RATES_PAGE,
    DEFAULT_UPDATE_HOURS,
    DOMAIN,
    MAX_UPDATE_HOURS,
    MIN_UPDATE_HOURS,
)


class FPLRatesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up FPL Published Rates."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(
                "fpl_published_residential_rates"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME], data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(
                        CONF_AUTO_DISCOVER, default=True
                    ): bool,
                    vol.Required(
                        CONF_RATES_PAGE, default=DEFAULT_RATES_PAGE
                    ): str,
                    vol.Required(
                        CONF_PDF_URL, default=DEFAULT_PDF_URL
                    ): str,
                    vol.Required(
                        CONF_UPDATE_HOURS, default=DEFAULT_UPDATE_HOURS
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_UPDATE_HOURS,
                            max=MAX_UPDATE_HOURS,
                        ),
                    ),
                    vol.Optional(CONF_MONTHLY_ENERGY_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="energy",
                        )
                    ),
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return FPLRatesOptionsFlow()


class FPLRatesOptionsFlow(config_entries.OptionsFlow):
    """Manage integration options."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        def current(key, default=None):
            return self.config_entry.options.get(
                key, self.config_entry.data.get(key, default)
            )

        schema = {
            vol.Required(
                CONF_AUTO_DISCOVER,
                default=current(CONF_AUTO_DISCOVER, True),
            ): bool,
            vol.Required(
                CONF_RATES_PAGE,
                default=current(CONF_RATES_PAGE, DEFAULT_RATES_PAGE),
            ): str,
            vol.Required(
                CONF_PDF_URL,
                default=current(CONF_PDF_URL, DEFAULT_PDF_URL),
            ): str,
            vol.Required(
                CONF_UPDATE_HOURS,
                default=current(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_UPDATE_HOURS, max=MAX_UPDATE_HOURS),
            ),
        }
        energy = current(CONF_MONTHLY_ENERGY_ENTITY)
        schema[vol.Optional(
            CONF_MONTHLY_ENERGY_ENTITY, default=energy
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor", device_class="energy"
            )
        )
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema)
        )
