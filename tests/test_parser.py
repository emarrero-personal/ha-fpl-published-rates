"""Publication discovery, extraction, validation, and price arithmetic."""
from hashlib import sha256
from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from custom_components.fpl_rates import parser


@pytest.mark.parametrize(('html', 'expected'), [
    ('<div href="res-eff-jan-2026.pdf">ignored</div>', 'https://example.com/res-eff-jan-2026.pdf'),
    ('<a>missing</a><a href="">empty</a><a href="other.pdf">other</a>', None),
    ('<a href="/jan-2026-res-eff-rates-rules-and-regulations.pdf">combined</a>'
     '<a href="/res-eff-feb-2026.pdf?download=1">compact</a>',
     'https://example.com/res-eff-feb-2026.pdf?download=1'),
    ('<a href="/res-eff-jan-2026.pdf">first</a><a href="/res-eff-feb-2026.pdf">second</a>',
     'https://example.com/res-eff-jan-2026.pdf'),
    ('<a href="/JAN-2026-RES-EFF-RATES-RULES-AND-REGULATIONS.PDF">combined</a>',
     'https://example.com/JAN-2026-RES-EFF-RATES-RULES-AND-REGULATIONS.PDF'),
])
def test_discovery(html, expected):
    assert parser.discover_residential_pdf(html, 'https://example.com/rates.html') == expected


def make_pdf(text):
    """Build a real text PDF without network or a separate rendering dependency."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    content = DecodedStreamObject()
    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    content.set_data(f'BT /F1 10 Tf 40 700 Td ({escaped}) Tj ET'.encode())
    page[NameObject('/Contents')] = writer._add_object(content)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_real_pdf_end_to_end(tariff_text):
    pdf = make_pdf(tariff_text.replace('\n', '  '))
    result = parser.parse_tariff_pdf(pdf, 'https://example.com/rates.pdf', True)
    assert result.effective == 'January 2026'
    assert result.source_sha256 == sha256(pdf).hexdigest()
    assert result.discovered_url is True
    assert result.base_charge == 10
    assert result.minimum_base_bill == 25
    values = result.to_dict()
    for key, expected in {
        'rs1_total_first_1000_cents': 8.5,
        'rs1_total_over_1000_cents': 10.5,
        'rtr_on_peak_adjustment_cents': 5,
        'rtr_off_peak_adjustment_cents': -2.5,
        'rtr_total_on_peak_first_1000_cents': 13.5,
        'rtr_total_on_peak_over_1000_cents': 15.5,
        'rtr_total_off_peak_first_1000_cents': 6,
        'rtr_total_off_peak_over_1000_cents': 8,
    }.items():
        assert values[key] == expected


@pytest.mark.parametrize('body', [b'<html>error</html>', make_pdf('')])
def test_empty_or_non_pdf_is_rejected(body):
    with pytest.raises(parser.TariffParseError):
        parser.extract_pdf_text(body)


def test_missing_optional_minimum_and_footnotes(tariff_text):
    result = parser.parse_tariff_text(tariff_text.split('minimum')[0].replace('6.00', '6.00**'), 'url')
    assert result.minimum_base_bill is None
    assert result.source_sha256 == ''
    assert result.rs1_energy_first_1000 == 6


@pytest.mark.parametrize(('old', 'new', 'error'), [
    ('Effective January 2026', '', 'effective date'),
    ('Residential Service (RS-1)', 'Other table', 'Required row'),
    ('Residential TOU Rider (RTR-1)', 'Other rider', 'Required row'),
    ('$10.00', '$100.00', 'base charge'),
    ('6.00', '50.00', 'component'),
    ('6.00', '-20.00', 'component'),
    ('(RTR-1) $10.00', '(RTR-1) $11.00', 'do not agree'),
])
def test_invalid_publications(tariff_text, old, new, error):
    with pytest.raises(parser.TariffParseError, match=error):
        parser.parse_tariff_text(tariff_text.replace(old, new), 'url')
