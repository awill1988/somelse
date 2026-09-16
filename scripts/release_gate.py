#!/usr/bin/env python3
"""Gate a crates.io release on a manifest version increase."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
BOOTSTRAP_BASELINE = "0.0.0"


def parse_version(value):
    match = SEMVER.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid semver version: {value}")
    core = tuple(int(part) for part in match.group(1, 2, 3))
    prerelease = match.group(4)
    identifiers = []
    if prerelease is not None:
        for part in prerelease.split("."):
            if part.isdecimal():
                if len(part) > 1 and part.startswith("0"):
                    raise ValueError(f"invalid numeric prerelease identifier: {value}")
                identifiers.append((0, int(part)))
            else:
                identifiers.append((1, part))
    return core, tuple(identifiers) if prerelease is not None else None


def compare_versions(left, right):
    left_core, left_pre = parse_version(left)
    right_core, right_pre = parse_version(right)
    if left_core != right_core:
        return (left_core > right_core) - (left_core < right_core)
    if left_pre is None or right_pre is None:
        return (left_pre is None) - (right_pre is None)
    return (left_pre > right_pre) - (left_pre < right_pre)


def sparse_index_path(crate_name):
    name = crate_name.lower()
    if len(name) == 1:
        return f"1/{name}"
    if len(name) == 2:
        return f"2/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def published_versions(crate_name):
    url = f"https://index.crates.io/{sparse_index_path(crate_name)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            lines = response.read().decode("utf-8").splitlines()
    except HTTPError as error:
        if error.code == 404:
            return []
        raise RuntimeError(f"registry lookup failed with status {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"registry lookup failed: {error}") from error
    if not lines:
        raise RuntimeError("registry lookup returned an empty index")
    return [json.loads(line)["vers"] for line in lines]


def package_metadata():
    result = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"],
        check=True,
        capture_output=True,
        text=True,
    )
    root_manifest = Path("Cargo.toml").resolve()
    packages = json.loads(result.stdout)["packages"]
    package = next(
        (item for item in packages if Path(item["manifest_path"]) == root_manifest),
        None,
    )
    if package is None:
        raise RuntimeError("root package missing from cargo metadata")
    return package["name"], package["version"]


def previous_version(before_sha):
    if not before_sha or before_sha.strip("0") == "":
        return BOOTSTRAP_BASELINE
    result = subprocess.run(
        ["git", "show", f"{before_sha}:Cargo.toml"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return BOOTSTRAP_BASELINE
    return tomllib.loads(result.stdout)["package"]["version"]


def initial_version():
    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return BOOTSTRAP_BASELINE
    roots = result.stdout.splitlines()
    if not roots:
        return BOOTSTRAP_BASELINE
    return previous_version(roots[0])


def tag_target(version):
    result = subprocess.run(
        ["git", "rev-parse", f"refs/tags/v{version}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def release_decision(
    current,
    previous,
    initial,
    versions,
    recovery_tag_matches=False,
):
    if current == previous:
        return False, False
    if current == BOOTSTRAP_BASELINE:
        if previous == initial and not versions:
            return False, False
        raise ValueError("the bootstrap baseline cannot replace a later version")
    if compare_versions(current, previous) <= 0:
        raise ValueError(f"{current} must exceed previous main version {previous}")
    if previous != BOOTSTRAP_BASELINE and previous not in versions:
        raise ValueError(f"previous main version {previous} is not published")
    current_is_published = False
    for published in versions:
        comparison = compare_versions(current, published)
        if comparison == 0:
            current_is_published = True
        elif comparison < 0:
            raise ValueError(f"{current} must exceed published version {published}")
    if current_is_published:
        if recovery_tag_matches:
            return True, False
        raise ValueError(f"{current} is already published without a matching recovery tag")
    return True, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-sha", required=True)
    parser.add_argument("--recovery-sha")
    args = parser.parse_args()
    crate_name, current = package_metadata()
    previous = previous_version(args.before_sha)
    # An unchanged manifest does not consult the registry.
    versions = published_versions(crate_name) if current != previous else []
    recovery_tag_matches = (
        args.recovery_sha is not None
        and current in versions
        and tag_target(current) == args.recovery_sha
    )
    release, publish = release_decision(
        current,
        previous,
        initial_version(),
        versions,
        recovery_tag_matches,
    )
    output = (
        f"release={'true' if release else 'false'}\n"
        f"publish={'true' if publish else 'false'}\n"
        f"name={crate_name}\n"
        f"version={current}\n"
        f"prerelease={'true' if parse_version(current)[1] is not None else 'false'}\n"
    )
    print(output, end="")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"release gate failed: {error}", file=sys.stderr)
        sys.exit(1)
