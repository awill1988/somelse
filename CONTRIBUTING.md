# Contributing to Rust Crate Template

Thank you for contributing! Bug reports, documentation updates, design discussions, and pull requests are welcome.

## Development Setup

Activate the repository git hooks:

```sh
git config core.hooksPath .githooks
```

## Commit Standards

All commit messages MUST follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`, `ci:`).

- **Strict Lowercase**: The subject line must be lowercase (e.g. `feat: add feature`, not `feat: Add feature`).
  - Capitalization is permitted only inside a leading ticket prefix (e.g. `[PROJ-123] feat: add feature`).
- **Character Limits**:
  - Header: 50 characters recommended, hard cap at 72 characters.
  - Body lines: wrapped at 72 characters.
  - No trailing period in subject line.
- **Zero AI Attribution**:
  - Do not include AI attribution footers or signatures (e.g. `Co-Authored-By`, `Generated-By`, `Assisted-By`, or emojis).

## Verification Before Review

Before submitting a pull request, run the local verification suite:

```sh
cargo test
cargo fmt --all -- --check
cargo fmt --manifest-path tools/commit_check/Cargo.toml -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo clippy --manifest-path tools/commit_check/Cargo.toml --all-targets -- -D warnings
python3 -m unittest discover -s scripts -p 'test_*.py'
cargo test --manifest-path tools/commit_check/Cargo.toml
cargo publish --dry-run
```

## License

Contributions are submitted under the dual MIT OR Apache-2.0 license.
