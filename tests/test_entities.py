"""Entity values, metadata, unit conversion, and timer lifecycle."""
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.fpl_rates import binary_sensor, button, sensor


async def test_platform_setup(hass, entry, coordinator):
    for energy in (None, 'sensor.monthly_energy'):
        entry.options = {'monthly_energy_entity': energy}
        add = MagicMock()
        await sensor.async_setup_entry(hass, entry, add)
        entities = add.call_args.args[0]
        assert len(entities) == len(sensor.RATE_SENSORS) + 3 + bool(energy)
        assert sum(isinstance(e, sensor.FPLEstimatedBillSensor) for e in entities) == bool(energy)
    add = MagicMock()
    await binary_sensor.async_setup_entry(hass, entry, add)
    assert isinstance(add.call_args.args[0][0], binary_sensor.FPLPeakBinarySensor)
    await button.async_setup_entry(hass, entry, add)
    refresh = add.call_args.args[0][0]
    assert refresh.device_info['identifiers'] == {('fpl_rates', entry.entry_id)}
    with patch.object(coordinator, 'async_request_refresh', new_callable=AsyncMock) as request:
        await refresh.async_press()
    request.assert_awaited_once()


def test_published_rate_entities(coordinator, entry):
    for description in sensor.RATE_SENSORS:
        entity = sensor.FPLRateSensor(coordinator, entry, description)
        assert entity.native_value == coordinator.data[description.data_key]
        assert entity.unique_id == f'fpl_rates_{description.key}'
        if description.key == 'effective':
            assert entity.extra_state_attributes == {
                'source_url': 'https://example.com/rates.pdf',
                'source_sha256': '', 'auto_discovered': False}
        else:
            assert entity.extra_state_attributes is None


@pytest.mark.parametrize(('instant', 'period', 'price', 'next_change'), [
    ('2026-07-06T16:00:00+00:00', 'Peak', 13.5, '2026-07-06T21:00:00-04:00'),
    ('2026-07-06T15:59:00+00:00', 'Off-peak', 6, '2026-07-06T12:00:00-04:00'),
])
def test_time_entities_use_tariff_zone(entry, coordinator, instant, period, price, next_change):
    with patch.object(sensor.dt_util, 'now', return_value=datetime.fromisoformat(instant)):
        current = sensor.FPLPeriodSensor(entry)
        assert current.native_value == period
        attrs = current.extra_state_attributes
        assert attrs['timezone'] == 'America/New_York'
        assert attrs['next_change'] == next_change
        assert attrs['next_period'] == ('Off-peak' if period == 'Peak' else 'Peak')
        assert attrs['season'] == 'Summer'
        assert attrs['holiday'] is None
        assert attrs['weekend'] is False
        assert binary_sensor.FPLPeakBinarySensor(entry).is_on == (period == 'Peak')
        dollars = sensor.FPLCurrentRateSensor(coordinator, entry)
        cents = sensor.FPLCurrentRateCentsSensor(coordinator, entry)
        assert dollars.native_value == Decimal(str(price / 100))
        assert cents.native_value == price
        assert dollars.extra_state_attributes['period'] == period
        assert cents.extra_state_attributes['usage_tier'] == 'First 1,000 kWh'


@pytest.mark.parametrize('kind', ['period', 'binary'])
async def test_minute_timer_is_registered_and_removed(hass, entry, coordinator, kind):
    module, entity = ((sensor, sensor.FPLPeriodSensor(entry)) if kind == 'period'
                      else (binary_sensor, binary_sensor.FPLPeakBinarySensor(entry)))
    entity.hass = hass
    entity.entity_id = 'sensor.test'
    remove = MagicMock()
    with patch.object(module, 'async_track_time_interval', return_value=remove) as track:
        await entity.async_added_to_hass()
    assert track.call_args.args[2].total_seconds() == 60
    with patch.object(entity, 'async_write_ha_state') as write:
        track.call_args.args[1](datetime.now())
    write.assert_called_once()
    await entity.async_remove(force_remove=True)
    remove.assert_called_once()


@pytest.mark.parametrize(('value', 'unit', 'expected_kwh', 'bill'), [
    ('0', 'kWh', 0, 25),
    ('-10', 'kWh', 0, 25),
    ('500', 'kWh', 500, 52.5),
    ('1000', 'kWh', 1000, 95),
    ('1500', 'kWh', 1500, 147.5),
    ('500000', 'Wh', 500, 52.5),
    ('0.5', 'MWh', 500, 52.5),
    ('500', 'unknown', 500, 52.5),
    ('unavailable', 'kWh', None, None),
])
def test_bill_estimates(hass, entry, coordinator, value, unit, expected_kwh, bill):
    hass.states.async_set('sensor.energy', value, {'unit_of_measurement': unit})
    entity = sensor.FPLEstimatedBillSensor(coordinator, entry, 'sensor.energy')
    entity.hass = hass
    assert entity.available is True
    assert entity.native_value == bill
    assert entity.extra_state_attributes['monthly_kwh'] == expected_kwh
    assert entity.extra_state_attributes['source_energy_entity'] == 'sensor.energy'


def test_missing_energy_and_unavailable_coordinator(hass, entry, coordinator):
    entity = sensor.FPLEstimatedBillSensor(coordinator, entry, 'sensor.missing')
    entity.hass = hass
    assert entity.available is False
    assert entity.native_value is None
    hass.states.async_set('sensor.missing', '500')
    coordinator.last_update_success = False
    assert entity.available is False
    coordinator.data['minimum_base_bill'] = None
    assert entity.native_value == 52.5
