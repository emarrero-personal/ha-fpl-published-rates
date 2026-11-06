"""Prepare a protected version PR, then release its exact merged commit."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

MANIFEST = "custom_components/fpl_rates/manifest.json"


def version_tuple(value: str) -> tuple[int, ...]:
    """Accept stable SemVer without leading zeroes or a v prefix."""
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise ValueError("Version must be MAJOR.MINOR.PATCH, for example 1.0.1")
    return tuple(map(int, value.split(".")))


def gh(*args: str, payload: dict | None = None) -> str:
    command = ["gh", *args]
    if payload is not None:
        command += ["--input", "-"]
    return subprocess.check_output(
        command,
        input=json.dumps(payload) if payload is not None else None,
        text=True,
    )


def api(path: str, payload: dict | None = None, method: str | None = None) -> dict | list:
    endpoint = f"repos/{os.environ['GITHUB_REPOSITORY']}"
    if path:
        endpoint += f"/{path}"
    options = ("--method", method) if method else ()
    return json.loads(gh("api", endpoint, *options, payload=payload))


def manifest(ref: str) -> tuple[dict, str]:
    result = api(f"contents/{MANIFEST}?ref={ref}")
    return json.loads(base64.b64decode(result["content"])), result["sha"]


def check_pr(pr: dict, version: str) -> None:
    """Only automate an open, version-only PR in this repository."""
    repository = os.environ["GITHUB_REPOSITORY"]
    if (
        pr["base"]["ref"] != "main"
        or pr["head"]["ref"] != f"release/v{version}"
        or pr["head"]["repo"]["full_name"] != repository
        or pr["base"]["repo"]["full_name"] != repository
    ):
        raise ValueError("Unexpected release PR source or target")
    files = api(f"pulls/{pr['number']}/files?per_page=100")
    if len(files) != 1 or files[0]["filename"] != MANIFEST or files[0]["status"] != "modified":
        raise ValueError("Release PR must change only the integration manifest")
    before, _ = manifest(pr["base"]["sha"])
    after, _ = manifest(pr["head"]["sha"])
    if version_tuple(version) <= version_tuple(before["version"]):
        raise ValueError("Release version must increase")
    before["version"] = version
    if after != before:
        raise ValueError("Release PR must change only the manifest version")


def prepare(version: str) -> None:
    if not os.environ.get("GH_TOKEN"):
        raise ValueError("Configure the RELEASE_TOKEN repository Actions secret first")
    repository = api("")
    if not repository["allow_auto_merge"]:
        raise ValueError("Enable repository auto-merge before running Release")
    branch = f"release/v{version}"
    prs = api(f"pulls?state=all&head={repository['owner']['login']}:{branch}&base=main")
    if prs:
        pr = api(f"pulls/{prs[0]['number']}")
        if pr["state"] != "open":
            raise ValueError("Release PR is already closed; rerun a failed publish job instead")
    else:
        base = api("git/ref/heads/main")["object"]["sha"]
        current, blob = manifest(base)
        if version_tuple(version) <= version_tuple(current["version"]):
            raise ValueError("Release version must be newer than main's manifest version")
        # Create the branch before modifying it; an existing branch fails safely.
        api("git/refs", {"ref": f"refs/heads/{branch}", "sha": base})
        current["version"] = version
        api(f"contents/{MANIFEST}", {
            "message": f"Bump integration version to {version}",
            "content": base64.b64encode((json.dumps(current, indent=2) + "\n").encode()).decode(),
            "sha": blob,
            "branch": branch,
        }, method="PUT")
        pr = api("pulls", {
            "title": f"Release v{version}",
            "head": branch,
            "base": "main",
            "body": (
                f"Bump the integration manifest to {version}. Auto-merge waits for "
                "the protected branch's required checks. After merging, the Release "
                f"workflow publishes v{version} at the exact merged commit with "
                "generated release notes. Close this PR to cancel the release."
            ),
        })
    check_pr(pr, version)
    # Pin the merge request to the inspected head; never bypass branch protection.
    gh("pr", "merge", str(pr["number"]), "--repo", os.environ["GITHUB_REPOSITORY"],
       "--auto", "--squash", "--match-head-commit", pr["head"]["sha"])
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"pr={pr['number']}\n")
    print(pr["html_url"])


def build_release_zip(commit: str, destination: Path) -> None:
    """Archive only tracked integration files from the exact released commit."""
    subprocess.check_call(["git", "fetch", "--no-tags", "--depth=1", "origin", commit])
    subprocess.check_call([
        "git", "archive", "--format=zip", f"--output={destination}",
        f"{commit}:custom_components/fpl_rates",
    ])


def publish_asset(tag: str, commit: str, existing: dict | None) -> None:
    """Upload the integration ZIP before publishing; recover partial attempts."""
    repository = os.environ["GITHUB_REPOSITORY"]
    asset_name = f"fpl_rates-{tag}.zip"
    if existing and existing["prerelease"]:
        raise ValueError("Existing release is a prerelease; inspect it manually")
    asset = next((asset for asset in existing["assets"] if asset["name"] == asset_name), None) if existing else None
    if asset:
        if asset["state"] != "uploaded" or asset["size"] == 0:
            raise ValueError("Existing ZIP upload is incomplete; delete the failed asset and rerun this job")
        if existing["draft"]:
            print(gh("release", "edit", tag, "--repo", repository, "--draft=false"))
        print(existing["html_url"])
        return
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / asset_name
        build_release_zip(commit, archive)
        if not existing:
            gh("release", "create", tag, "--repo", repository, "--draft",
               "--verify-tag", "--target", commit, "--title", tag, "--generate-notes")
        gh("release", "upload", tag, str(archive), "--repo", repository)
        if not existing or existing["draft"]:
            print(gh("release", "edit", tag, "--repo", repository, "--draft=false"))
        else:
            print(existing["html_url"])


def publish(version: str, number: int) -> None:
    deadline = time.monotonic() + 45 * 60
    while True:
        pr = api(f"pulls/{number}")
        if pr["merged"]:
            break
        if pr["state"] == "closed":
            raise ValueError("Release canceled: PR closed without merging")
        if time.monotonic() >= deadline:
            raise TimeoutError("PR did not merge within 45 minutes; rerun this job after it merges")
        print("Waiting for required checks and auto-merge...", flush=True)
        time.sleep(30)
    check_pr(pr, version)
    commit = pr["merge_commit_sha"]
    released, _ = manifest(commit)
    if released["version"] != version:
        raise ValueError("Merged commit does not contain the requested version")
    tag = f"v{version}"
    # Check the tag at the commit level, including annotated tags. Never move a tag.
    refs = api(f"git/matching-refs/tags/{tag}")
    exists = any(ref["ref"] == f"refs/tags/{tag}" for ref in refs)
    if exists:
        if api(f"commits/{tag}")["sha"] != commit:
            raise ValueError("Release tag already targets a different commit")
    else:
        api("git/refs", {"ref": f"refs/tags/{tag}", "sha": commit})
    releases = json.loads(gh("api", "--paginate", "--slurp",
        f"repos/{os.environ['GITHUB_REPOSITORY']}/releases?per_page=100"))
    existing = next((r for page in releases for r in page if r["tag_name"] == tag), None)
    publish_asset(tag, commit, existing)


if __name__ == "__main__":
    try:
        requested = os.environ["RELEASE_VERSION"]
        version_tuple(requested)
        if sys.argv[1] == "prepare":
            prepare(requested)
        elif sys.argv[1] == "publish":
            publish(requested, int(os.environ["RELEASE_PR"]))
        else:
            raise ValueError("Expected prepare or publish")
    except (ValueError, TimeoutError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
