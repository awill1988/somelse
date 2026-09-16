# Instructions for `rust-crate-template`

## Commit Standards

### 1. Conventional Commits & Strict Lowercase
All commit messages MUST follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`, `ci:`).

- **No Capitalization**: The first line of any commit message MUST be completely lowercase under all circumstances.
  - ✅ `feat: add feature`
  - ❌ `feat: Add feature`
  - ❌ `Feat: add feature`
- **Exception**: Capitalization is permitted ONLY inside a leading ticket identifier prefix if applicable (e.g., `[TICKET-123] feat: add feature`).

### 2. Strict Character Limits
- **Header (Subject Line)**: Capped at **50 characters** recommended (absolute hard limit: **72 characters**).
- **Body Lines**: Wrapped at **72 characters** per line.
- Do not use trailing periods in subject lines.

### 3. Zero AI Attribution Policy
- NEVER add AI co-authorship tags, footers, or signatures (e.g. `Co-Authored-By`, `Generated-By`, `Assisted-By`, `🤖`).
- Ensure all commit messages are concise, direct, and written from a human developer perspective.

## Push Safety
- Always verify active branch (`git branch --show-current`) prior to push.
- Use plain `git push` (never explicit refspecs).
- Never push to `main` without approval.

## Validation
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
