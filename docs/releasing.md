# Releases and HACS publishing

The repository uses HACS's standard `custom_components/fpl_rates` layout. HACS
downloads the integration directly from the selected branch or release tag;
there is no release ZIP to build or upload.

## Validate before publishing

1. Review the integration version in
   [`manifest.json`](../custom_components/fpl_rates/manifest.json). The initial
   version is `1.0.0`; increment it for subsequent releases.
2. Keep the minimum Home Assistant version in [`hacs.json`](../hacs.json) and the
   README aligned. The declared baseline is `2026.3.0`, which supports bundled
   brand images. Verify runtime behavior on that baseline before releasing;
   repository validation does not establish runtime compatibility.
3. Run the local checks in [Contributing](contributing.md), then require all
   jobs in the **Validate** GitHub Actions workflow to pass on the release
   commit. The workflow runs unit tests with a coverage gate requiring >85%, HACS validation,
   and Home Assistant hassfest on pushes, pull requests, a weekly schedule, and
   manual dispatch. The HACS job runs once the repository is public. After
   changing visibility, manually run **Validate** and confirm HACS passes before
   tagging or publishing the release.
4. Test installation, setup, options, refresh, reload, and removal in a separate
   Home Assistant instance. Verify rates against the source publication and
   exercise the peak schedule boundaries.

The `brand/` directory contains the project's original icon in 256 × 256 and
512 × 512 PNG sizes. When replacing the artwork, export both sizes from the same
image and preserve transparency outside the rounded tile.

Home Assistant 2026.3 and newer supports
[local brand images](https://contributors.home-assistant.io/core/integrations/brands/).
Current HACS validation accepts a bundled `brand/icon.png`; an upstream brands
submission is therefore unnecessary for this layout.

## Publish a release

1. Push the reviewed changes to the public GitHub repository and confirm CI.
2. Create a GitHub release targeting that commit with a tag matching the
   manifest version, for example `v1.0.0` for `1.0.0`.
3. Include user-visible changes, compatibility requirements, and any migration
   instructions in the release notes. Publish the release; a tag alone does
   not create a GitHub release.
4. Install the release through HACS as a custom repository and check that the
   integration version and entities are correct after restarting.

No GitHub release or remote repository change is performed by these local
preparation steps. Until a release exists, HACS can install the default branch.

## Optional default catalog submission

Custom repository installation does not add the project to HACS's default
catalog. Before requesting inclusion:

- Make the GitHub repository public, enable issues, add a description, and set
  topics such as `home-assistant`, `hacs`, `custom-component`, and `fpl`.
- Publish at least one release containing the HACS manifest and MIT license.
- Ensure the HACS and hassfest validations pass without ignored checks.
- Follow the [current HACS inclusion requirements](https://www.hacs.dev/docs/publish/include/)
  to submit the repository to `hacs/default`.

See also the official [HACS integration requirements](https://www.hacs.dev/docs/publish/integration/)
and [repository manifest reference](https://www.hacs.dev/docs/publish/start/#hacsjson).
