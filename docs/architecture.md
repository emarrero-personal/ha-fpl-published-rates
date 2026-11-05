# How the project works

## Source map

All implementation files live in
[`custom_components/fpl_rates`](../custom_components/fpl_rates/).

| File | Responsibility |
| --- | --- |
| `manifest.json` | Integration metadata, config-flow support, and the pinned PDF dependency. |
| `const.py` | Domain, platform list, option keys, URLs, units, and interval limits. |
| `config_flow.py` | Initial setup, singleton enforcement, and options forms. |
| `__init__.py` | Entry setup, first refresh, runtime data, platform forwarding, unload, and reload. |
| `coordinator.py` | HTTP retrieval, discovery orchestration, refresh errors, and rate-change notifications. |
| `parser.py` | PDF discovery, text extraction, table parsing, and validation. |
| `models.py` | Immutable `TariffData` and calculated totals. |
| `schedule.py` | Peak periods, holidays, and the next period transition. |
| `entity.py` | Shared coordinator entity and device information. |
| `sensor.py` | Published prices, local period, current prices, and optional bill estimate. |
| `binary_sensor.py` | Local peak-state binary sensor. |
| `button.py` | Manual refresh button. |
| `diagnostics.py` | Entry options, refresh status, exception, and parsed data export. |
| `strings.json`, `translations/en.json` | Setup and options UI text. |

## Lifecycle and data flow

1. The config flow stores user input in a Home Assistant config entry.
2. Entry setup creates `FPLRatesCoordinator` and awaits its first refresh.
3. If discovery is enabled, the coordinator fetches the rates page and selects
   a matching publication URL. Otherwise, or if no match exists, it uses the
   configured PDF URL.
4. The coordinator downloads the PDF with Home Assistant's shared aiohttp
   session. Both HTML and PDF requests have a 30-second timeout.
5. `parse_tariff_pdf()` extracts normalized text with `pypdf`, parses it into
   `TariffData`, and `to_dict()` adds calculated rate totals.
6. Setup stores the coordinator in `entry.runtime_data` and loads the sensor,
   binary sensor, and button platforms.
7. Periodic polling and the refresh button reuse the coordinator. Option
   changes reload the entry; unloading delegates to Home Assistant's platforms.

The coordinator wraps retrieval and parsing exceptions in `UpdateFailed`.
Coordinator-backed entities follow Home Assistant's coordinator availability
behavior. The period sensor and peak binary sensor calculate local schedule
state independently of publication refresh success. There is no explicit
on-disk tariff cache or startup fallback in this integration.

The coordinator uses `always_update=False`, allowing Home Assistant to suppress
coordinator notifications when the resulting dictionary is unchanged. Once
prior data exists, it checks base charge, minimum bill, both RS-1 totals, and
both first-tier RTR-1 totals for changes. A difference creates a persistent
notification with ID `fpl_rates_changed`.

## Parser contract

Discovery recognizes two filename patterns, case-insensitively:
`res-eff-mon-year.pdf` and
`mon-year-res-eff-rates-rules-and-regulations.pdf`. It resolves anchor URLs
against the rates page, prefers the compact filename, and otherwise preserves
page order. If anchors yield no match, it searches the raw HTML for matching
filenames.

PDF extraction joins text from all pages and collapses whitespace. Parsing
requires an `Effective <month> <year>` phrase and ten numeric values immediately
following each of `Residential Service (RS-1)` and
`Residential TOU Rider (RTR-1)`. Numbers can have a sign, a dollar prefix, and
trailing asterisks. The column order is positional:

| Index | RS-1 meaning | RTR-1 use |
| --- | --- | --- |
| 0 | Monthly base charge | Must agree with RS-1 within $0.01. |
| 1, 2 | Energy, first tier and upper tier | On-peak and off-peak energy adjustments. |
| 3–6 | Conservation, capacity, environmental, storm protection | Parsed but not used in calculations. |
| 7, 8 | Fuel, first tier and upper tier | On-peak and off-peak fuel adjustments. |
| 9 | Transition credit | Parsed but not used in calculations. |

The optional `minimum $<number> base bill` phrase supplies the minimum bill.
The parser rejects missing required rows or dates, empty extracted text, a base
charge outside `0 < value < 100`, RS-1 columns 1–8 outside
`-20 < value < 50`, and mismatched base charges. These checks do not validate
every parsed column or independently verify the tariff's business rules.

The resulting model includes the source URL, SHA-256 of the original PDF, and
`discovered_url`. That flag is true only when discovery selected a URL different
from the configured PDF URL; it does not simply mean discovery was enabled.

## Price and estimate calculations

Variable components are in cents/kWh. Base charge and minimum bill are in dollars.
For each usage tier:

```text
RS-1 total = energy + conservation + capacity + environmental
             + storm protection + fuel + transition credit
RTR-1 on-peak total = RS-1 total + on-peak energy adjustment
                      + on-peak fuel adjustment
RTR-1 off-peak total = RS-1 total + off-peak energy adjustment
                       + off-peak fuel adjustment
```

`TariffData.to_dict()` rounds calculated totals and combined adjustments to six
decimal places. Current-rate sensors select the on-peak or off-peak **first-tier**
total from the local schedule. The dollars/kWh sensor divides that value by 100.

For monthly consumption `kwh`, after unit conversion and clamping to zero:

```text
energy_cents = min(kwh, 1000) * rs1_first_tier
               + max(kwh - 1000, 0) * rs1_upper_tier
subtotal_dollars = base_charge + energy_cents / 100
estimate = max(subtotal_dollars, minimum_base_bill)  # when a minimum exists
```

The estimate rounds to two decimals. It reads the configured sensor's state
without creating its own energy meter or subscribing to source-state changes.
The [installation guide](installation.md) describes units and excluded charges.

## Local time-of-use schedule

`schedule.py` converts each supplied timezone-aware datetime to
`America/New_York` before evaluating hours, seasons, weekends, or holidays.
Entity callers pass `homeassistant.util.dt.now()`; Home Assistant's configured
time zone does not affect the result. Naive datetimes are rejected. Next
transitions are returned in Eastern Time with the applicable daylight saving
offset, and the period sensor's `timezone` attribute is `America/New_York`.

| Season | Months | Weekday peak windows |
| --- | --- | --- |
| Summer | April–October | 12:00 inclusive to 21:00 exclusive. |
| Winter | November–March | 06:00 inclusive to 10:00 exclusive, and 18:00 inclusive to 22:00 exclusive. |

Weekends and these holidays are entirely off-peak: New Year's Day, Memorial Day
(last Monday in May), Independence Day, Labor Day (first Monday in September),
Thanksgiving Day (fourth Thursday in November), and Christmas Day. Fixed-date
holidays use the date itself, without a substitute observed weekday.

`next_change()` scans minute boundaries for the next change in peak state, with
a nine-day search bound. `period_info()` combines this with the current period,
season, holiday, weekend flag, and a human-readable schedule. Minute timers
update the period, current prices, and binary peak sensor separately from PDF
polling. Schedule rules must be changed in code when their intended behavior
changes; downloading a different PDF does not update them.
