"""HTTP and update behavior with deterministic I/O boundaries."""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.fpl_rates import coordinator as module
from custom_components.fpl_rates.const import DEFAULT_PDF_URL
from custom_components.fpl_rates.parser import TariffParseError


@pytest.mark.parametrize('method,body', [('_get_text', 'page'), ('_get_bytes', b'%PDF data')])
async def test_http_requests(coordinator, method, body):
    response = MagicMock()
    response.text = AsyncMock(return_value=body)
    response.read = AsyncMock(return_value=body)
    session = MagicMock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    with patch.object(module, 'async_get_clientsession', return_value=session):
        assert await getattr(coordinator, method)('https://example.com') == body
    response.raise_for_status.assert_called_once()
    assert session.get.call_args.kwargs['timeout'] == 30
    assert 'User-Agent' in session.get.call_args.kwargs['headers']


async def test_reject_non_pdf_response(coordinator):
    response = MagicMock(read=AsyncMock(return_value=b'error'))
    session = MagicMock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    with patch.object(module, 'async_get_clientsession', return_value=session):
        with pytest.raises(TariffParseError, match='did not return a PDF'):
            await coordinator._get_bytes('url')


@pytest.mark.parametrize(('discovery', 'html', 'expected', 'discovered'), [
    (False, '', DEFAULT_PDF_URL, False),
    (True, '<html>No PDF</html>', DEFAULT_PDF_URL, False),
    (True, '<a href="/res-eff-feb-2026.pdf">new</a>', 'https://www.fpl.com/res-eff-feb-2026.pdf', True),
])
async def test_update_sources(coordinator, entry, tariff, discovery, html, expected, discovered):
    entry.options = {'auto_discover': discovery}
    coordinator.data = None
    with (patch.object(coordinator, '_get_text', AsyncMock(return_value=html)) as get_text,
          patch.object(coordinator, '_get_bytes', AsyncMock(return_value=b'%PDF')) as get_bytes,
          patch.object(module, 'parse_tariff_pdf', return_value=tariff) as parse):
        assert await coordinator._async_update_data() == tariff.to_dict()
    assert get_text.await_count == int(discovery)
    get_bytes.assert_awaited_once_with(expected)
    parse.assert_called_once_with(b'%PDF', expected, discovered)


async def test_options_precedence(hass, entry):
    entry.data = {'update_hours': 12, 'pdf_url': 'data'}
    entry.options = {'update_hours': 6, 'pdf_url': 'options'}
    coordinator = module.FPLRatesCoordinator(hass, entry)
    assert coordinator.update_interval == timedelta(hours=6)
    assert coordinator._option('pdf_url', 'default') == 'options'
    assert coordinator._option('missing', 'default') == 'default'


@pytest.mark.parametrize('stage', ['page', 'download', 'parse'])
async def test_refresh_errors_preserve_cause(coordinator, stage):
    error = ValueError('broken source')
    with (patch.object(coordinator, '_get_text', AsyncMock(side_effect=error if stage == 'page' else None, return_value='')),
          patch.object(coordinator, '_get_bytes', AsyncMock(side_effect=error if stage == 'download' else None, return_value=b'%PDF')),
          patch.object(module, 'parse_tariff_pdf', side_effect=error if stage == 'parse' else None)):
        with pytest.raises(UpdateFailed, match='broken source') as caught:
            await coordinator._async_update_data()
    assert caught.value.__cause__ is error


@pytest.mark.parametrize('changed', [False, True])
async def test_notify_only_for_changed_rates(coordinator, tariff, changed):
    if changed:
        coordinator.data['base_charge'] = 99
    notification = MagicMock()
    with (patch.object(coordinator, '_get_text', AsyncMock(return_value='')),
          patch.object(coordinator, '_get_bytes', AsyncMock(return_value=b'%PDF')),
          patch.object(module, 'parse_tariff_pdf', return_value=tariff),
          patch.object(type(coordinator.hass), 'components', create=True, new=MagicMock(persistent_notification=notification))):
        await coordinator._async_update_data()
    assert notification.async_create.call_count == int(changed)
