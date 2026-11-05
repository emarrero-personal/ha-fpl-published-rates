"""Shared deterministic fixtures using real Home Assistant APIs."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.fpl_rates import FPLRuntimeData
from custom_components.fpl_rates.coordinator import FPLRatesCoordinator
from custom_components.fpl_rates.parser import parse_tariff_text


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    yield instance
    await instance.async_stop(force=True)


@pytest.fixture
def entry():
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = 'test-entry'
    entry.title = 'FPL test'
    entry.version = 1
    entry.source = 'user'
    entry.data = {}
    entry.options = {}
    return entry


@pytest.fixture
def tariff_text():
    return (Path(__file__).parent / 'fixtures/residential.txt').read_text()


@pytest.fixture
def tariff(tariff_text):
    return parse_tariff_text(tariff_text, 'https://example.com/rates.pdf')


@pytest.fixture
def coordinator(hass, entry, tariff):
    coordinator = FPLRatesCoordinator(hass, entry)
    coordinator.async_set_updated_data(tariff.to_dict())
    entry.runtime_data = FPLRuntimeData(coordinator)
    return coordinator
