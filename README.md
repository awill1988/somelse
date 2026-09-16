# Rust Crate Template

A modern, production-grade GitHub template repository for publishing Rust libraries and crates to [crates.io](https://crates.io) with automated CI/CD.

[![CI](https://github.com/awill1988/rust-crate-template/actions/workflows/ci.yml/badge.svg)](https://github.com/awill1988/rust-crate-template/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-blue.svg)](LICENSE-MIT)

## Features

- **Automated Publishing & Release Gate**:
  - Crates.io publishing gated behind verified manifest version increments.
  - Git tags and GitHub releases synchronized automatically on merge to `main`.
  - **Unpublishable Baseline (`0.0.0`)**: Package version starts strictly at `0.0.0` and can never be published to crates.io. The first publishable release starts at `0.1.0` (or `0.1.0-alpha.1`).
- **Native GitHub Coverage Reporting**:
  - Complete elimination of external third-party coverage services and tokens.
  - Coverage summaries rendered directly in GitHub Actions Step Summaries (`$GITHUB_STEP_SUMMARY`).
  - Interactive HTML coverage reports uploaded as downloadable workflow artifacts.
- **Commit Linting & Attribution Policy**:
  - Zero-dependency commit linter enforcing Conventional Commits and lowercase subjects.
  - Strict 72-character line wrapping.
  - Zero AI attribution policy enforcement.
- **Quality & Security**:
  - `cargo test`, `cargo fmt`, `cargo clippy`, and `cargo publish --dry-run`.
  - Minimum Supported Rust Version (MSRV) verification (`rust-version = "1.56"`).
  - GitHub CodeQL static analysis and `cargo-audit` dependency vulnerability scanning.
  - Workflow file validation with `actionlint`.
- **Changelog Generation**:
  - Structured release notes generated from conventional commits via `git-cliff`.

---

## Quickstart: Using this Template

1. **Click "Use this template"** to create your new repository.
2. **Configure your package metadata** in `Cargo.toml`:
   - Change `name`, `description`, `repository`, and `authors`.
   - Keep `version = "0.0.0"` until you are ready for your first release.
3. **Configure GitHub Repository Secrets**:
   - In your repository settings, create an environment named `production`.
   - Add the secret `CARGO_REGISTRY_TOKEN` containing your crates.io API token.
4. **Enable Local Git Hooks**:
   ```sh
   git config core.hooksPath .githooks
   ```

---

## Release Lifecycle

### 1. The `0.0.0` Baseline
The repository begins at `version = "0.0.0"`. This baseline indicates an unreleased repository state:
- Pushes to `main` at `0.0.0` will run all tests and coverage checks, but the release gate will output `release=false, publish=false`.
- No tag will be created and nothing will be published to crates.io.
- Attempting to manually trigger a release of `0.0.0` is explicitly rejected.

### 2. Preparing a Release
When you are ready to cut your first release:
1. Go to **Actions** → **Prepare Release** workflow.
2. Click **Run workflow** and enter the desired semver version (e.g. `0.1.0` or `0.1.0-alpha.1`).
3. The workflow will:
   - Validate that the version exceeds `0.0.0` and has not already been published.
   - Create a dedicated branch `release/vX.Y.Z`.
   - Update `Cargo.toml`.
   - Open a release pull request with a preview of the release notes.

### 3. Merging and Publishing
1. Pull request CI runs full validation, builds release notes preview, and reports coverage.
2. Merge the release pull request into `main`.
3. The `CI` workflow detects the version bump, packages the crate, pushes the version tag, publishes to crates.io, and publishes the GitHub release.

---

## Local Verification

Run the exact checks performed in CI:

```sh
# Run unit and integration tests
cargo test

# Run commit message linter tests
cargo test --manifest-path tools/commit_check/Cargo.toml

# Check code formatting
cargo fmt --all -- --check
cargo fmt --manifest-path tools/commit_check/Cargo.toml -- --check

# Check clippy warnings
cargo clippy --all-targets --all-features -- -D warnings
cargo clippy --manifest-path tools/commit_check/Cargo.toml --all-targets -- -D warnings

# Validate release gate automation
python3 -m unittest discover -s scripts -p 'test_*.py'

# Dry-run cargo packaging
cargo publish --dry-run
```

---

## License

Dual-licensed under either of:
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT License ([LICENSE-MIT](LICENSE-MIT))
