# Contributing

## Prepare a development environment

Use a separate Home Assistant development or test instance for integration
changes. The repository contains the custom component source and a GitHub Actions
workflow for unit tests, coverage, dependency vulnerability auditing, HACS, and
hassfest validation. The minimum declared Home Assistant version is `2026.3.0`.
Tests use Home Assistant `2026.11.0` on Python 3.14 with dependencies in
`requirements-test.txt`.

1. Clone the repository and create a branch for your change.
2. Make the checkout's `custom_components/fpl_rates` directory available as
   `<test-config>/custom_components/fpl_rates`, by copying it or using a symlink
   where your development environment supports one.
3. Restart the test instance and add **FPL Published Rates** through the UI.
   Home Assistant installs the PDF dependency from `manifest.json`.
4. After editing Python files, copy changes again if needed and restart the
   test instance so it imports the new code.

For unit tests, create an isolated Python 3.14 environment:

```bash
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest
```

The test suite uses real Home Assistant classes and a local synthetic tariff
fixture, with HTTP, PDF retrieval, notifications, and platform forwarding mocked
at their boundaries. A generated in-memory PDF exercises actual text extraction
with `pypdf`. Tests make no external network requests. Keep local environments,
bytecode, downloaded publications, and instance configuration out of commits.

## Make changes in the right place

Use [the source map](architecture.md) to locate the relevant modules.

- For publication layout changes, update discovery or parsing in `parser.py`.
  Keep explicit failures for unsupported layouts and verify the positional
  columns against a representative publication.
- For rate calculations, update `models.py` and check both usage tiers and
  signed adjustments. Keep dollars and cents distinct.
- For schedule changes, update `schedule.py` and exercise boundary times,
  seasons, weekends, and holidays in Eastern Time.
- For configuration changes, keep `const.py`, `config_flow.py`, `strings.json`,
  and `translations/en.json` aligned. Check setup and options separately.
- For entity changes, preserve existing unique IDs when the entity's identity
  is unchanged, and keep entities attached to the existing device identifier.
- For dependency changes, update the pin in `manifest.json` and validate the
  integration with that dependency in the test instance.

Follow the existing async Home Assistant lifecycle and type annotations. Use
the shared HTTP session and coordinator for publication retrieval. Keep pure
parsing, calculations, and schedule logic separate from Home Assistant entity
behavior. Update these docs when user-visible behavior changes.

## Validate your contribution

From the repository root, run these basic checks with your development Python:

```bash
python3 -m compileall -q custom_components/fpl_rates
python3 -m json.tool custom_components/fpl_rates/manifest.json > /dev/null
python3 -m json.tool custom_components/fpl_rates/strings.json > /dev/null
python3 -m json.tool custom_components/fpl_rates/translations/en.json > /dev/null
git diff --check
git status --short
```

Compilation creates local `__pycache__` directories. These checks validate
syntax, JSON formatting, and diff whitespace; they do not verify Home Assistant
compatibility or runtime behavior.

Run `python -m pytest` for unit tests. `pyproject.toml` measures all Python modules
under `custom_components/fpl_rates`, including unimported modules, with branch
coverage enabled. Both local runs and CI require **combined statement and branch coverage above
85%**, enforced as a minimum of **85.01%** with two decimal places. The threshold
is defined once in `pyproject.toml` and used by pytest and coverage reports. The terminal report lists missing lines; `coverage.xml` is
also generated and uploaded by CI. For an interactive report, run
`python -m coverage html` and open `htmlcov/index.html`.

The suite covers discovery, parsing and validation, both tariff tiers, Eastern
Time schedule boundaries and daylight saving transitions, HTTP/update errors,
rate-change notifications, config and options flows, entry lifecycle, entities,
energy unit conversion, bill estimation, refresh buttons, and diagnostics.
Unit tests do not replace a complete installation test in a running Home
Assistant instance.

CI audits the full dependency chains from the integration manifest,
`requirements-test.txt`, and `requirements-security.txt` on pushes, pull requests,
the weekly schedule, and manual runs. Known vulnerabilities or dependency
collection errors fail the audit job. The audit tool is pinned separately so
Dependabot can update it without adding it to the integration's runtime.

To audit the test and tooling dependencies locally with Python 3.14:

```bash
python -m pip install -r requirements-security.txt
python -m pip_audit --strict -r requirements-test.txt -r requirements-security.txt
```

The PDF dependency in `requirements-test.txt` should match the manifest pin.
CI also reads the manifest directly so runtime requirements remain covered when
the manifest changes. Review advisories and upgrade the owning dependency rather
than overriding Home Assistant's transitive dependency pins.

Choose runtime checks that exercise the behavior you changed:

| Area | Useful validation |
| --- | --- |
| Setup and lifecycle | Add the entry, confirm duplicate setup is blocked, save options, reload, and unload without errors. |
| Retrieval | Discover a matching PDF, use a direct PDF with discovery disabled, and verify failures for invalid HTTP/PDF responses. |
| Parser | Cover representative normalized text or PDF fixtures, missing rows/date, signed values, base-charge disagreement, and implausible components. |
| Calculations | Check both tiers, positive and negative RTR adjustments, and cents-to-dollars conversion against independently calculated values. |
| Schedule | Check exact start/end boundaries, both seasons, weekends, each holiday, and the next transition with timezone-aware datetimes. |
| Estimate | Check consumption below, at, and above 1,000 kWh; Wh/MWh conversion; minimum bill; and missing or nonnumeric energy states. |
| Refresh and entities | Press Refresh rates, inspect values and attributes, and verify the intended behavior after a refresh failure or rate change. |

For repeatable parser checks, prefer a small synthetic text fixture or a
publication fixture whose source and effective date are recorded. Keep tests
independent of live publication changes where possible. The validation ranges
and fallback limitations are documented in [the architecture guide](architecture.md)
and [the installation guide](installation.md).

## Submit a contribution or report a problem

Before submitting a pull request, review the diff for unrelated changes and
generated files. Describe the concrete problem, resulting behavior, and checks
you performed, including Home Assistant and Python versions for runtime checks.
For parser changes, include the publication source and effective date. For
schedule changes, include the relevant rule and boundary examples. State any
checks you could not run.

For a bug report, include reproduction steps, expected and actual behavior,
relevant log errors, and diagnostics when useful. Review diagnostic options and
URLs for private information before posting them.

Use [GitHub issues](https://github.com/emarrero-personal/ha-fpl-published-rates/issues)
for bug reports and feature requests. See [Releases and HACS publishing](releasing.md)
for versioning and distribution steps.
