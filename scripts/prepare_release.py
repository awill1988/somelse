#!/usr/bin/env python3
"""Validate and apply a release version to the root Cargo manifest."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from release_gate import (
    BOOTSTRAP_BASELINE,
    package_metadata,
    parse_version,
    published_versions,
    release_decision,
)


PACKAGE_HEADER = re.compile(r"^\[package\]\s*$")
SECTION_HEADER = re.compile(r"^\[[^]]+\]\s*$")
VERSION_LINE = re.compile(r'^(version\s*=\s*)"([^"]+)"(\s*)$')
SUBJECT_PREFIX = "chore(release): prepare "


def validate_version_input(candidate):
    parse_version(candidate)
    if candidate == BOOTSTRAP_BASELINE:
        raise ValueError(f"cannot prepare release for bootstrap baseline {BOOTSTRAP_BASELINE}")
    if len(f"{SUBJECT_PREFIX}{candidate}") > 72:
        raise ValueError("version makes the release commit subject exceed 72 characters")


def replace_package_version(manifest, expected, candidate):
    lines = manifest.splitlines(keepends=True)
    in_package = False
    replacements = 0
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        newline = line[len(content) :]
        if PACKAGE_HEADER.fullmatch(content):
            in_package = True
            continue
        if in_package and SECTION_HEADER.fullmatch(content):
            break
        if not in_package:
            continue
        match = VERSION_LINE.fullmatch(content)
        if match is None:
            continue
        if match.group(2) != expected:
            raise ValueError(
                f"manifest version {match.group(2)} does not match cargo metadata {expected}"
            )
        lines[index] = f'{match.group(1)}"{candidate}"{match.group(3)}{newline}'
        replacements += 1
    if replacements != 1:
        raise ValueError("expected one package version in Cargo.toml")
    return "".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    candidate = args.version
    validate_version_input(candidate)

    crate_name, current = package_metadata()
    versions = published_versions(crate_name)
    release, publish = release_decision(
        candidate,
        current,
        BOOTSTRAP_BASELINE,
        versions,
    )
    if not release or not publish:
        raise ValueError(f"{candidate} does not create a new release")

    manifest_path = Path("Cargo.toml")
    manifest = manifest_path.read_text(encoding="utf-8")
    updated = replace_package_version(manifest, current, candidate)
    manifest_path.write_text(updated, encoding="utf-8")

    output = (
        f"name={crate_name}\n"
        f"previous={current}\n"
        f"version={candidate}\n"
        f"prerelease={'true' if parse_version(candidate)[1] is not None else 'false'}\n"
    )
    print(output, end="")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"prepare release failed: {error}", file=sys.stderr)
        sys.exit(1)
