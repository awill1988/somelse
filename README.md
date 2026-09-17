# somelse!

**Keep the `Some`. Diverge on `None`.**

`somelse!` is a dependency-free, `no_std` macro that extracts an `Option::Some`
payload as an expression and requires `None` to diverge from the current path.

[![Crates.io](https://img.shields.io/crates/v/somelse.svg)](https://crates.io/crates/somelse)
[![Documentation](https://docs.rs/somelse/badge.svg)](https://docs.rs/somelse)
[![CI](https://github.com/awill1988/somelse/actions/workflows/ci.yml/badge.svg)](https://github.com/awill1988/somelse/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-blue.svg)](LICENSE-MIT)

```rust
use somelse::somelse;

fn process(input: Option<i32>) -> Result<i32, &'static str> {
    let value = somelse!(input, else => return Err("missing value"));
    Ok(value * 2)
}
```

The input runs once. A `Some` becomes the value of the macro. The `else`
expression matches `None` and must leave the current path through `return`,
`break`, `continue`, panic, or another never-returning expression.

## Why an expression

Rust's [`let-else`](https://rust-lang.github.io/rfcs/3137-let-else.html) keeps
the inner value in the surrounding scope and requires the failure branch to
diverge. It is a statement, so it cannot be placed directly inside another
expression or function argument.

A `match` works in those positions but repeats the `Some` and `None` structure:

```rust
fn process(input: Option<i32>) -> Result<i32, &'static str> {
    let value = match input {
        Some(value) => value,
        None => return Err("missing value"),
    };
    Ok(value * 2)
}
```

`somelse!` keeps the same control flow in expression position:

```rust
use somelse::somelse;

fn process(input: Option<i32>) -> Result<i32, &'static str> {
    Ok(somelse!(input, else => return Err("missing value")) * 2)
}
```

Prefer `let-else` when a statement is sufficient and `match` when multiple
branches need meaningful behavior. This macro exists only for concise extraction
where expression placement and caller-selected divergence are both useful.

## The name

The name describes the complete domain: **`Some` + `else` = `somelse!`**.

## Contributor checks

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change.

The conventional commit linter is written in Rust. Activate the tracked hooks:

```sh
git config core.hooksPath .githooks
```

Run local validation:

```sh
cargo test
cargo fmt --all -- --check
cargo fmt --manifest-path tools/commit_check/Cargo.toml -- --check
cargo fmt --manifest-path tests/fixtures/downstream/Cargo.toml -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo clippy --manifest-path tools/commit_check/Cargo.toml --all-targets -- -D warnings
cargo clippy --manifest-path tests/fixtures/downstream/Cargo.toml --all-targets -- -D warnings
python3 -m unittest discover -s scripts -p 'test_*.py'
cargo test --manifest-path tools/commit_check/Cargo.toml
cargo check --manifest-path tests/fixtures/downstream/Cargo.toml
cargo publish --dry-run
```

## License

Dual-licensed under [MIT](LICENSE-MIT) or [Apache 2.0](LICENSE-APACHE).
