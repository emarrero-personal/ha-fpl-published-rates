# FPL Published Rates documentation

FPL Published Rates is a custom Home Assistant integration with the domain
`fpl_rates`. It downloads FPL residential rate publications and exposes standard
residential (RS-1) and residential time-of-use rider (RTR-1) prices, a local
peak-period schedule, and an optional RS-1 monthly bill estimate.

It uses public documents and does not require an FPL account or read meter data
from FPL. Monthly consumption, if used, comes from a Home Assistant energy sensor
you select.

## Guides

- [Installation and configuration](installation.md): install the integration,
  configure its sources, and troubleshoot updates.
- [How the project works](architecture.md): follow the data flow, calculations,
  schedule logic, and entity behavior.
- [Releases and HACS publishing](releasing.md): validate and distribute releases.
- [Contributing](contributing.md): navigate the source, prepare a development
  environment, validate changes, and submit a contribution.

## Scope

The rate entities represent the components parsed from the publication. Prices
and estimates exclude taxes, franchise fees, gross-receipts tax, and
account-specific charges. The optional bill sensor estimates RS-1 charges;
it does not calculate an RTR-1 bill from time-of-use consumption.

The current RTR-1 price always uses the first 1,000 kWh tier. Selecting a monthly
energy sensor does not change that tier. The peak schedule is implemented in
Python and is not extracted from the PDF.

These guides describe the implementation in this repository. The repository
declares Home Assistant `2026.3.0` as its minimum and includes HACS and hassfest
CI validation, plus a unit test suite with a coverage gate requiring >85%. See
[Contributing](contributing.md) for the Python 3.14 test environment and commands.
