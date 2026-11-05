![FPL Published Rates icon](./custom_components/fpl_rates/brand/icon.png)

# FPL Published Rates

Bring Florida Power & Light’s published residential electricity rates into Home
Assistant. See what FPL charges per kWh, track when the time-of-use schedule
switches between peak and off-peak, and use those signals in dashboards and
automations. The integration reads public FPL rate publications and requires no
FPL account.

## What you get in Home Assistant

The integration groups its entities on one device page.

| What you want to see | Entities to use |
| --- | --- |
| Standard residential rates (RS-1) | Prices for the first 1,000 kWh and for usage above 1,000 kWh, plus the monthly base charge and minimum base bill. |
| Time-of-use rates (RTR-1) | Peak and off-peak prices for both usage tiers, plus the current first-tier price in ¢/kWh and $/kWh. |
| Peak or off-peak now | The **RTR-1 current period** sensor shows the active period and its next scheduled change. The **RTR-1 peak** binary sensor can trigger automations, such as deferring EV charging until off-peak. |
| Estimated monthly bill | Optionally connect a monthly energy sensor to estimate your RS-1 bill. |
| Source and refresh | **Publication effective** shows the effective month and year. **Refresh rates** checks the publication on demand. |

## Install with HACS

Requires Home Assistant **2026.3.0 or newer**.

1. Open [FPL Published Rates in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=emarrero-personal&repository=ha-fpl-published-rates&category=integration). You can also open **HACS → Custom repositories** and add `https://github.com/emarrero-personal/ha-fpl-published-rates` as an **Integration**.
2. Download **FPL Published Rates** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and select **FPL Published Rates**.

For manual setup, follow the [manual installation instructions](docs/installation.md#manual-installation).

## Configure

- **Rate source.** By default, the integration looks for a residential PDF on the [FPL rates page](https://www.fpl.com/rates.html) and checks it every 24 hours. Check **Publication effective** after setup. To use a specific PDF, disable automatic discovery and enter its URL.
- **Peak schedule.** RTR-1 uses Eastern Time (`America/New_York`), including daylight saving time.
- **Bill estimate.** Select an energy sensor that tracks usage for your current month or billing cycle. The estimate covers RS-1 and excludes taxes, franchise fees, and account-specific charges.

## Documentation and support

- [Installation, configuration, and full entity list](docs/installation.md)
- [Rate calculations and peak schedule](docs/architecture.md)
- [Contributing and tests](docs/contributing.md)
- [Release guide](docs/releasing.md)
- [Report an issue](https://github.com/emarrero-personal/ha-fpl-published-rates/issues)

## Sources and credits

- **Rate data.** Florida Power & Light publishes the residential RS-1 and RTR-1 rates used by this integration. The test fixture uses synthetic values. [FPL published rates](https://www.fpl.com/rates.html)
- **Icon.** Original artwork created collaboratively by Ely Marrero and ChatGPT.
- **PDF parsing.** The integration uses pypdf, distributed separately under the BSD 3-Clause license. [pypdf license](https://github.com/py-pdf/pypdf/blob/6.21.4/LICENSE)

FPL Published Rates is an independent community project with no affiliation
with Florida Power & Light. Distributed under the [MIT license](LICENSE).
