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

### One-time automation setup

Enable **Allow auto-merge** in the repository's general settings. Keep the
existing branch protections and required checks enabled.

Create a fine-grained personal access token restricted to this repository with
**Contents: read and write** and **Pull requests: read and write** permissions.
Store it as the repository Actions secret `RELEASE_TOKEN`, and renew it before
it expires. Never commit or paste the token into an issue, PR, or workflow input.
This token creates the version branch and PR and enables auto-merge; GitHub's
built-in token publishes the release.

The separate token lets the version PR trigger CI automatically. PRs created
with `GITHUB_TOKEN` require approval before their workflows can run. The global
Actions setting allowing workflows to create or approve PRs can stay disabled;
the release workflow does not use `GITHUB_TOKEN` to create PRs or approve reviews.

### Run the release workflow

1. Merge the changes you want to release and complete the runtime checks above.
2. Open **Actions → Release → Run workflow**, select **main**, and enter a new
   stable version such as `1.0.1` (without `v`). It must be greater than the
   version currently in the integration manifest. Prereleases are not supported.
3. The workflow creates `release/v1.0.1`, changes only the manifest version,
   opens a PR, and enables squash auto-merge. Required branch checks must pass
   before merging. If main advances, update the release branch and let CI rerun.
4. After the PR merges, the workflow creates `v1.0.1` at that PR's exact squash
   merge commit and publishes a GitHub release with generated release notes.
   It does not tag the current branch tip or overwrite existing tags.
5. Review the generated notes and add any compatibility or migration guidance.
   Install the release through HACS and confirm the version and entities after
   restarting Home Assistant.

The workflow serializes release runs and waits up to 45 minutes for merging.
Close the version PR to cancel before merging, or cancel the workflow to stop
publication. If checks fail or the PR has not merged in time, fix the problem
and use **Re-run failed jobs** after it merges. A retry accepts an existing tag
only if it targets the same commit and leaves an existing published release
untouched. If preparation fails after creating a branch but before opening its
PR, inspect and delete that unmerged release branch before retrying.

The workflow can also be dispatched from the CLI:

```bash
gh workflow run release.yml --ref main -f version=1.0.1
```

For a manual release, first merge a manifest version bump and confirm CI, then
create and publish a GitHub release with the matching `v`-prefixed tag targeting
that reviewed commit. A tag alone does not create a GitHub release.

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
