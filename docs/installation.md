# Installation and configuration

## Install with HACS

Requires Home Assistant **2026.3.0 or newer**.

1. Open HACS and select **Custom repositories** from the menu.
2. Add `https://github.com/emarrero-personal/ha-fpl-published-rates` with type
   **Integration**.
3. Download **FPL Published Rates**, then restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and select
   **FPL Published Rates** to complete setup.

For updates, download the new version in HACS and restart Home Assistant.

## Manual installation

1. Copy the entire [`custom_components/fpl_rates`](../custom_components/fpl_rates/)
   directory into your Home Assistant configuration directory, producing
   `<config>/custom_components/fpl_rates/manifest.json` and the adjacent Python
   files and translations.
2. Restart Home Assistant. Home Assistant installs the dependency declared in
   `manifest.json`, currently `pypdf==6.21.4`.
3. Open **Settings → Devices & services → Add integration** and search for
   **FPL Published Rates**.
4. Complete the setup form. The integration retrieves and parses the publication
   during its first refresh before loading the entity platforms.

Setup uses the UI config flow; the project does not implement YAML configuration.
Only one config entry is allowed, using the unique ID
`fpl_published_residential_rates`.

## Configuration fields

| Field | Default | Behavior |
| --- | --- | --- |
| Name | `FPL Published Rates` | Entry title and device name; supplied during initial setup. |
| Automatically discover the current PDF | Enabled | Searches the configured rates page for a matching residential publication. |
| FPL rates page URL | `https://www.fpl.com/rates.html` | HTML page used for discovery. |
| Fallback residential-rate PDF URL | `https://www.fpl.com/content/dam/fplgp/us/en/rates/pdf/res-eff-jan-2026.pdf` | PDF used when discovery is disabled or the page has no matching link. This is a built-in default, not a guarantee that this publication is current. |
| Update interval in hours | `24` | Integer from `6` through `168`. |
| Optional monthly energy sensor | Unset | A sensor with the energy device class, used to estimate an RS-1 monthly bill. |

The options flow exposes all these settings except the name. Options override
the original setup values, and saving options reloads the integration.

Discovery prefers a compact `res-eff-mon-year.pdf` filename over a combined
`mon-year-res-eff-rates-rules-and-regulations.pdf` filename. Within the same
preference group, the first matching link in page order wins. It does not compare
publication dates or wait until a publication's effective month.

The fallback is used only when discovery is disabled or finds no matching link.
A failure to fetch the rates page, or to download or parse a discovered PDF,
fails the refresh rather than retrying the fallback. To use a specific PDF,
disable discovery and set the PDF URL directly.

## Time zone and monthly energy

The integration converts Home Assistant's current time to `America/New_York`
before evaluating the peak schedule, including daylight saving time. Home
Assistant can use any configured time zone. The period sensor's `timezone`
attribute reports `America/New_York`, and `next_change` includes the applicable
Eastern UTC offset.

For the optional bill estimate, select a sensor whose value represents energy
used in the current month or billing cycle. The integration does not create a
utility meter, reset the sensor, or infer billing-cycle boundaries. It converts
`Wh` to kWh and `MWh` to kWh; other units are treated as kWh. Negative consumption
is clamped to zero.

The bill sensor reads the source value when its state is evaluated, but does not
register a listener for changes to that energy sensor. Do not assume every
consumption change immediately updates the estimate in Home Assistant.

## Entities and operation

The integration groups its entities under one device. Home Assistant generates
entity IDs, so check the actual IDs in your installation before using them in
automations.

| Entities | Purpose |
| --- | --- |
| Publication effective | Effective month and year, with source URL, PDF SHA-256, and discovery attributes. |
| RS-1 monthly base charge; Minimum base bill | Fixed amounts in dollars; the minimum can be unknown if absent from the publication. |
| RS-1 rates, first 1,000 and over 1,000 kWh | Two total energy prices in cents/kWh. |
| RTR-1 on-peak and off-peak rates for both tiers | Four total energy prices in cents/kWh. |
| RTR-1 current period | `Peak` or `Off-peak`, with season, holiday, weekend, schedule, time zone, and next-change attributes. |
| RTR-1 current energy price; RTR-1 current rate | The current first-tier RTR-1 price in dollars/kWh and cents/kWh respectively. |
| RTR-1 peak | Binary sensor that is on during peak periods. |
| Estimated RS-1 monthly bill | Optional estimate in dollars, created when a monthly energy entity is configured. |
| Refresh rates | Button that requests a coordinator refresh. |

Time-sensitive entities update on a one-minute timer. Publication data is polled
at the configured hourly interval. A persistent notification appears when a
successful update changes selected base charges or calculated rates; it is not
a notification for every PDF or source change.

## Troubleshooting

- For retrieval failures, check the configured URLs and connectivity from the
  Home Assistant host. Requests have a 30-second timeout and reject HTTP errors.
- For a non-PDF response, confirm that the URL returns bytes beginning with
  `%PDF`, rather than an HTML error page.
- For parsing failures, check the effective-date text and RS-1/RTR-1 table
  layout. A scanned PDF without extractable text will fail. See the parser
  contract in [the architecture guide](architecture.md).
- For an incorrect peak period, compare the current time in `America/New_York`
  with the schedule rules in [the architecture guide](architecture.md).
- For an unknown estimate, check that the selected energy entity exists and has
  a numeric state. Confirm its units and monthly reset behavior separately.

Download integration diagnostics from Home Assistant to inspect
`last_update_success`, `last_exception`, entry options, and `parsed_tariff`.
The publication sensor also exposes source information. Diagnostics include
configured options and source URLs; review those values before attaching a
diagnostic file to a public issue.
