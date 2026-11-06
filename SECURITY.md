# Reporting a vulnerability

Use [GitHub’s private vulnerability report form](https://github.com/emarrero-personal/ha-fpl-published-rates/security/advisories/new) to contact the maintainers about a security issue. Include the integration and Home Assistant versions, what the issue affects, and steps to reproduce it. Keep credentials, account information, and unredacted Home Assistant diagnostics out of reports.

## Dependency updates

Keep the deployed Home Assistant instance and this integration up to date.
Home Assistant manages its own dependencies; updating this repository's test
requirements does not update an installed instance. Home Assistant 2026.11.0
includes Pillow 13.0.0, which fixes the known Pillow vulnerabilities affecting
the 12.3.0 pin in Home Assistant 2026.10.4. Upgrade Home Assistant through its
supported update process rather than installing a different Pillow version into
its environment.

The validation workflow audits runtime, test, and tooling dependencies against
current vulnerability advisories on each push, pull request, and weekly run.
A passing scan covers known package advisories for the resolved dependencies;
it does not establish that every deployed instance or operating system is secure.
