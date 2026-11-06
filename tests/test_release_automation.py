"""Exercise release safety boundaries without contacting GitHub."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import release


def release_pr(**changes):
    repository = {"full_name": "owner/repo"}
    return {
        "number": 10, "state": "open", "merged": False,
        "html_url": "https://github.com/owner/repo/pull/10",
        "base": {"ref": "main", "sha": "base", "repo": repository},
        "head": {"ref": "release/v1.0.1", "sha": "head", "repo": repository},
        "merge_commit_sha": "merged-commit",
        **changes,
    }


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "GH_TOKEN": "test"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_version_validation(self):
        self.assertGreater(release.version_tuple("1.10.0"), release.version_tuple("1.9.0"))
        for value in ("v1.0.1", "01.0.1", "1.0", "1.0.1-rc.1", "1.0.1\n", "1.0.1;bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.version_tuple(value)

    def test_manifest_update_uses_put(self):
        with patch.object(release, "gh", return_value="{}") as cli:
            release.api("contents/file.json", {"sha": "blob"}, method="PUT")
        cli.assert_called_once_with("api", "repos/owner/repo/contents/file.json", "--method", "PUT", payload={"sha": "blob"})

    def test_pr_must_change_only_version(self):
        files = [{"filename": release.MANIFEST, "status": "modified"}]
        with patch.object(release, "api", return_value=files), patch.object(release, "manifest") as manifests:
            manifests.side_effect = [({"version": "1.0.0", "requirements": []}, "a"),
                                     ({"version": "1.0.1", "requirements": ["unexpected"]}, "b")]
            with self.assertRaisesRegex(ValueError, "only the manifest version"):
                release.check_pr(release_pr(), "1.0.1")

    def test_pr_rejects_other_files_and_forks(self):
        with patch.object(release, "api", return_value=[{"filename": "other", "status": "modified"}]):
            with self.assertRaisesRegex(ValueError, "only the integration manifest"):
                release.check_pr(release_pr(), "1.0.1")
        pr = release_pr()
        pr["head"]["repo"] = {"full_name": "someone/fork"}
        with self.assertRaisesRegex(ValueError, "source or target"):
            release.check_pr(pr, "1.0.1")

    def test_prepare_creates_version_pr_and_auto_merge(self):
        repository = {"allow_auto_merge": True, "owner": {"login": "owner"}}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"GITHUB_OUTPUT": str(Path(directory) / "output")}), \
             patch.object(release, "api", side_effect=[repository, [], {"object": {"sha": "base"}}, {}, {}, release_pr()]) as api, \
             patch.object(release, "manifest", return_value=({"version": "1.0.0"}, "blob")), \
             patch.object(release, "check_pr") as check, patch.object(release, "gh") as cli:
            release.prepare("1.0.1")
            self.assertEqual(Path(os.environ["GITHUB_OUTPUT"]).read_text(), "pr=10\n")
            self.assertEqual(api.call_args_list[4].kwargs["method"], "PUT")
            check.assert_called_once()
            self.assertIn("--auto", cli.call_args.args)
            self.assertEqual(cli.call_args.args[-2:], ("--match-head-commit", "head"))

    def test_prepare_rejects_equal_or_older_version(self):
        for version in ("1.0.0", "0.9.0"):
            with patch.object(release, "api", side_effect=[{"allow_auto_merge": True, "owner": {"login": "owner"}}, [], {"object": {"sha": "base"}}]) as api, \
                 patch.object(release, "manifest", return_value=({"version": "1.0.0"}, "blob")), self.assertRaises(ValueError):
                release.prepare(version)
            self.assertEqual(api.call_count, 3)

    def test_closed_pr_cancels_publication(self):
        with patch.object(release, "api", return_value=release_pr(state="closed")), patch.object(release, "gh") as cli:
            with self.assertRaisesRegex(ValueError, "canceled"):
                release.publish("1.0.1", 10)
            cli.assert_not_called()

    def test_publish_waits_and_targets_exact_merge_commit(self):
        with patch.object(release, "api", side_effect=[release_pr(), release_pr(merged=True), [], {}]) as api, \
             patch.object(release, "check_pr"), patch.object(release, "manifest", return_value=({"version": "1.0.1"}, "blob")), \
             patch.object(release.time, "sleep") as sleep, patch.object(release, "gh", return_value="[[]]"), \
             patch.object(release, "publish_asset") as publish_asset:
            release.publish("1.0.1", 10)
            sleep.assert_called_once_with(30)
            self.assertEqual(api.call_args.args, ("git/refs", {"ref": "refs/tags/v1.0.1", "sha": "merged-commit"}))
            publish_asset.assert_called_once_with("v1.0.1", "merged-commit", None)

    def test_existing_tag_cannot_be_moved(self):
        with patch.object(release, "api", side_effect=[release_pr(merged=True), [{"ref": "refs/tags/v1.0.1"}], {"sha": "wrong"}]), \
             patch.object(release, "check_pr"), patch.object(release, "manifest", return_value=({"version": "1.0.1"}, "blob")), \
             patch.object(release, "gh") as cli:
            with self.assertRaisesRegex(ValueError, "different commit"):
                release.publish("1.0.1", 10)
            cli.assert_not_called()

    def test_existing_matching_release_is_idempotent(self):
        existing = {"tag_name": "v1.0.1", "draft": False, "prerelease": False, "html_url": "release-url",
                    "assets": [{"name": "fpl_rates-v1.0.1.zip", "state": "uploaded", "size": 100}]}
        with patch.object(release, "api", side_effect=[release_pr(merged=True), [{"ref": "refs/tags/v1.0.1"}], {"sha": "merged-commit"}]), \
             patch.object(release, "check_pr"), patch.object(release, "manifest", return_value=({"version": "1.0.1"}, "blob")), \
             patch.object(release, "gh", return_value=json.dumps([[existing]])) as cli:
            release.publish("1.0.1", 10)
            self.assertEqual(cli.call_count, 1)

    def test_zip_contains_only_integration_contents_from_release_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", "-C", directory, *args], text=True).strip()
            git("init", "--quiet")
            git("config", "user.name", "Release test")
            git("config", "user.email", "test@example.com")
            component = root / "custom_components/fpl_rates"
            (component / "brand").mkdir(parents=True)
            (component / "manifest.json").write_text('{"version": "1.0.1"}')
            (component / "brand/icon.png").write_bytes(b"image")
            (root / "README.md").write_text("excluded")
            git("add", ".")
            git("commit", "--quiet", "-m", "Release snapshot")
            commit = git("rev-parse", "HEAD")
            (component / "manifest.json").write_text('{"version": "9.0.0"}')
            (component / "untracked.py").write_text("excluded")
            git("remote", "add", "origin", directory)
            archive = root / "integration.zip"
            # Use a real Git archive and local fetch without changing process cwd.
            check_call = subprocess.check_call
            with patch.object(release.subprocess, "check_call", side_effect=lambda args: check_call(args, cwd=directory)):
                release.build_release_zip(commit, archive)
            with zipfile.ZipFile(archive) as result:
                files = {name for name in result.namelist() if not name.endswith("/")}
                self.assertEqual(files, {"manifest.json", "brand/icon.png"})
                self.assertEqual(json.loads(result.read("manifest.json"))["version"], "1.0.1")
                self.assertEqual(result.read("brand/icon.png"), b"image")

    def test_new_release_is_published_only_after_zip_upload(self):
        with patch.object(release, "build_release_zip") as build, patch.object(release, "gh") as cli:
            release.publish_asset("v1.0.1", "merged-commit", None)
            self.assertEqual(build.call_args.args[0], "merged-commit")
            self.assertEqual(build.call_args.args[1].name, "fpl_rates-v1.0.1.zip")
            self.assertEqual([call.args[1] for call in cli.call_args_list], ["create", "upload", "edit"])
            self.assertIn("--draft", cli.call_args_list[0].args)
            self.assertIn("--generate-notes", cli.call_args_list[0].args)
            self.assertIn("--draft=false", cli.call_args_list[2].args)

    def test_failed_upload_leaves_draft_for_retry(self):
        with patch.object(release, "build_release_zip"), \
             patch.object(release, "gh", side_effect=["", subprocess.CalledProcessError(1, "upload")]) as cli:
            with self.assertRaises(subprocess.CalledProcessError):
                release.publish_asset("v1.0.1", "merged-commit", None)
            self.assertEqual([call.args[1] for call in cli.call_args_list], ["create", "upload"])

    def test_retry_completes_draft_with_existing_zip_without_reupload(self):
        existing = {"draft": True, "prerelease": False, "html_url": "release-url",
                    "assets": [{"name": "fpl_rates-v1.0.1.zip", "state": "uploaded", "size": 100}]}
        with patch.object(release, "build_release_zip") as build, patch.object(release, "gh") as cli:
            release.publish_asset("v1.0.1", "merged-commit", existing)
            build.assert_not_called()
            self.assertEqual(cli.call_args.args, ("release", "edit", "v1.0.1", "--repo", "owner/repo", "--draft=false"))

    def test_retry_adds_zip_to_existing_release_missing_asset(self):
        existing = {"draft": False, "prerelease": False, "html_url": "release-url", "assets": []}
        with patch.object(release, "build_release_zip"), patch.object(release, "gh") as cli:
            release.publish_asset("v1.0.1", "merged-commit", existing)
            self.assertEqual(cli.call_count, 1)
            self.assertEqual(cli.call_args.args[1], "upload")

    def test_incomplete_asset_is_not_published(self):
        existing = {"draft": True, "prerelease": False, "html_url": "release-url",
                    "assets": [{"name": "fpl_rates-v1.0.1.zip", "state": "starter", "size": 0}]}
        with patch.object(release, "gh") as cli, self.assertRaisesRegex(ValueError, "incomplete"):
            release.publish_asset("v1.0.1", "merged-commit", existing)
        cli.assert_not_called()

    def test_timeout_does_not_publish(self):
        with patch.object(release, "api", return_value=release_pr()), patch.object(release.time, "monotonic", side_effect=[0, 3000]), \
             patch.object(release, "gh") as cli, self.assertRaises(TimeoutError):
            release.publish("1.0.1", 10)
        cli.assert_not_called()
