"""Config form schemas, singleton setup, and option precedence."""
from unittest.mock import MagicMock

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.fpl_rates.config_flow import FPLRatesConfigFlow


def make_flow(hass):
    flow = FPLRatesConfigFlow()
    flow.hass = hass
    flow.context = {'source': 'user'}
    hass.config_entries = MagicMock()
    hass.config_entries.flow.async_progress_by_handler.return_value = []
    hass.config_entries.async_entry_for_domain_unique_id.return_value = None
    return flow


async def test_user_form_defaults_and_validation(hass):
    flow = make_flow(hass)
    result = await flow.async_step_user()
    assert result['type'] == FlowResultType.FORM
    schema = result['data_schema']
    defaults = schema({})
    assert defaults['name'] == 'FPL Published Rates'
    assert defaults['auto_discover'] is True
    assert defaults['update_hours'] == 24
    for hours in (6, 168):
        assert schema({'update_hours': str(hours)})['update_hours'] == hours
    for hours in (5, 169, 'invalid'):
        with pytest.raises(vol.Invalid):
            schema({'update_hours': hours})


async def test_setup_and_duplicate_prevention(hass, entry):
    flow = make_flow(hass)
    result = await flow.async_step_user({'name': 'My rates', 'update_hours': 6})
    assert result['type'] == FlowResultType.CREATE_ENTRY
    assert result['title'] == 'My rates'
    assert result['data'] == {'name': 'My rates', 'update_hours': 6}
    assert flow.context['unique_id'] == 'fpl_published_residential_rates'
    hass.config_entries.async_entry_for_domain_unique_id.return_value = entry
    with pytest.raises(AbortFlow, match='already_configured'):
        await flow.async_step_user({'name': 'Duplicate'})


async def test_options_factory_defaults_and_save(hass, entry):
    flow = FPLRatesConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_known_entry.return_value = entry
    entry.data = {'update_hours': 12, 'auto_discover': False}
    entry.options = {'update_hours': 6, 'monthly_energy_entity': 'sensor.energy'}
    result = await flow.async_step_init()
    assert result['type'] == FlowResultType.FORM
    defaults = result['data_schema']({})
    assert defaults['update_hours'] == 6
    assert defaults['auto_discover'] is False
    assert defaults['monthly_energy_entity'] == 'sensor.energy'
    submitted = {'auto_discover': True, 'update_hours': 48}
    result = await flow.async_step_init(submitted)
    assert result['type'] == FlowResultType.CREATE_ENTRY
    assert result['data'] == submitted
