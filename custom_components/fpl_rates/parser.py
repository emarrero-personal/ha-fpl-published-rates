"""FPL residential rate-summary discovery and parsing."""

from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
import re
from urllib.parse import urljoin

from pypdf import PdfReader

from .models import TariffData

NUMBER = r"[-+]?\d+(?:\.\d+)?"
PDF_PATTERN = re.compile(
    r"(?:res-eff-[a-z]{3}-\d{4}|"
    r"[a-z]{3}-\d{4}-res-eff-rates-rules-and-regulations)"
    r"\.pdf(?:\?[^\"'<>\s]*)?",
    re.IGNORECASE,
)


class TariffParseError(ValueError):
    """Raised when the publication cannot be parsed safely."""


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def discover_residential_pdf(html: str, base_url: str) -> str | None:
    """Find the most likely current FPL residential-rate PDF link."""
    parser = _LinkParser()
    parser.feed(html)

    candidates = []
    for href in parser.links:
        absolute = urljoin(base_url, href)
        if PDF_PATTERN.search(absolute):
            candidates.append(absolute)

    if not candidates:
        candidates = [
            urljoin(base_url, match.group(0))
            for match in PDF_PATTERN.finditer(html)
        ]
    if not candidates:
        return None

    # Prefer the compact "res-eff-mon-year.pdf" publication over archived
    # combined documents, while preserving document order from FPL's page.
    candidates.sort(
        key=lambda url: (
            0 if re.search(r"/res-eff-[a-z]{3}-\d{4}\.pdf", url, re.I) else 1
        )
    )
    return candidates[0]


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract normalized text from a PDF."""
    if not pdf_bytes.startswith(b"%PDF"):
        raise TariffParseError("Downloaded content is not a PDF")
    reader = PdfReader(BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = " ".join(text.split())
    if not normalized:
        raise TariffParseError("The PDF contains no extractable text")
    return normalized


def _row(text: str, label: str, count: int) -> list[float]:
    match = re.search(
        re.escape(label)
        + rf"\s+((?:\$?{NUMBER}(?:\*+)?\s+){{{count - 1}}}"
        + rf"\$?{NUMBER}(?:\*+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise TariffParseError(f"Required row not found: {label}")
    values = re.findall(NUMBER, match.group(1))
    if len(values) != count:
        raise TariffParseError(
            f"{label}: expected {count} values, found {len(values)}"
        )
    return [float(value) for value in values]


def parse_tariff_text(
    text: str,
    source_url: str,
    source_bytes: bytes = b"",
    discovered_url: bool = False,
) -> TariffData:
    """Parse and validate the RS-1 and RTR-1 rows."""
    effective_match = re.search(
        r"Effective\s+([A-Za-z]+\s+\d{4})", text, re.IGNORECASE
    )
    if not effective_match:
        raise TariffParseError("Publication effective date not found")

    rs1 = _row(text, "Residential Service (RS-1)", 10)
    rtr = _row(text, "Residential TOU Rider (RTR-1)", 10)

    minimum_match = re.search(
        rf"minimum\s+\$({NUMBER})\s+base bill", text, re.IGNORECASE
    )
    minimum_bill = (
        float(minimum_match.group(1)) if minimum_match else None
    )

    # Guard against silently accepting a different table layout.
    if not 0 < rs1[0] < 100:
        raise TariffParseError("RS-1 base charge is outside a plausible range")
    for value in rs1[1:9]:
        if not -20 < value < 50:
            raise TariffParseError("RS-1 component outside plausible range")
    if abs(rs1[0] - rtr[0]) > 0.01:
        raise TariffParseError("RS-1 and RTR-1 base charges do not agree")

    return TariffData(
        effective=effective_match.group(1),
        source_url=source_url,
        source_sha256=sha256(source_bytes).hexdigest() if source_bytes else "",
        discovered_url=discovered_url,
        base_charge=rs1[0],
        minimum_base_bill=minimum_bill,
        rs1_energy_first_1000=rs1[1],
        rs1_energy_over_1000=rs1[2],
        conservation=rs1[3],
        capacity=rs1[4],
        environmental=rs1[5],
        storm_protection=rs1[6],
        fuel_first_1000=rs1[7],
        fuel_over_1000=rs1[8],
        transition_credit=rs1[9],
        rtr_on_peak_energy_adjustment=rtr[1],
        rtr_off_peak_energy_adjustment=rtr[2],
        rtr_on_peak_fuel_adjustment=rtr[7],
        rtr_off_peak_fuel_adjustment=rtr[8],
    )


def parse_tariff_pdf(
    pdf_bytes: bytes, source_url: str, discovered_url: bool
) -> TariffData:
    """Extract and parse a residential publication PDF."""
    return parse_tariff_text(
        extract_pdf_text(pdf_bytes),
        source_url,
        source_bytes=pdf_bytes,
        discovered_url=discovered_url,
    )
