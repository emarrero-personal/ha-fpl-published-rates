"""Config entry setup, reload, unload, and diagnostics."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components import fpl_rates
from custom_components.fpl_rates.const import PLATFORMS
from custom_components.fpl_rates.diagnostics import async_get_config_entry_diagnostics


async def test_setup_reload_and_unload(hass, entry):
    coordinator = MagicMock(async_config_entry_first_refresh=AsyncMock())
    manager = MagicMock(async_forward_entry_setups=AsyncMock(),
                        async_unload_platforms=AsyncMock(return_value=True),
                        async_reload=AsyncMock())
    hass.config_entries = manager
    with patch.object(fpl_rates, 'FPLRatesCoordinator', return_value=coordinator):
        assert await fpl_rates.async_setup_entry(hass, entry) is True
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    assert entry.runtime_data.coordinator is coordinator
    manager.async_forward_entry_setups.assert_awaited_once_with(entry, PLATFORMS)
    listener = entry.add_update_listener.call_args.args[0]
    await listener(hass, entry)
    manager.async_reload.assert_awaited_once_with(entry.entry_id)
    entry.async_on_unload.assert_called_once_with(entry.add_update_listener.return_value)
    assert await fpl_rates.async_unload_entry(hass, entry) is True
    manager.async_unload_platforms.assert_awaited_once_with(entry, PLATFORMS)


async def test_setup_failure_does_not_load_platforms(hass, entry):
    coordinator = MagicMock(async_config_entry_first_refresh=AsyncMock(side_effect=RuntimeError('unavailable')))
    hass.config_entries = MagicMock(async_forward_entry_setups=AsyncMock())
    with patch.object(fpl_rates, 'FPLRatesCoordinator', return_value=coordinator):
        with pytest.raises(RuntimeError, match='unavailable'):
            await fpl_rates.async_setup_entry(hass, entry)
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()


@pytest.mark.parametrize('failed', [False, True])
async def test_diagnostics(hass, entry, coordinator, failed):
    entry.options = {'update_hours': 6}
    coordinator.last_update_success = not failed
    coordinator.last_exception = ValueError('bad PDF') if failed else None
    if failed:
        coordinator.data = None
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result['entry'] == {'title': entry.title, 'version': 1, 'options': {'update_hours': 6}}
    assert result['last_update_success'] is not failed
    assert result['last_exception'] == ('bad PDF' if failed else None)
    assert result['parsed_tariff'] == ({} if failed else coordinator.data)
    assert result['entry']['options'] is not entry.options
