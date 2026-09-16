# somelse!

**Keep the `Some`. Diverge on `None`. Carry on.**

`somelse!` is a dependency-free, `no_std` macro that extracts an `Option::Some`
payload, applies optional inline transforms or sequential conditionals with
caller-scope control flow, and dispatches `None` through diverging `else` clauses.

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

The expression runs once. A `Some` becomes the value of the macro. The `else`
clause matches `None` and must leave the current path through `return`, `break`,
`continue`, panic, or another never-returning expression.

## The repeated pattern

Rust's [`let-else`](https://rust-lang.github.io/rfcs/3137-let-else.html) keeps
the inner value in the surrounding scope and requires the failure branch to
diverge. However, `let-else` is a statement rather than an expression, cannot be
used directly within nested sub-expressions or function arguments, and does not
support inline conditional pipelines on the extracted value before assignment.

A `match` allows binding, conditional checks, and divergence, but introduces
repetitive structural ceremony:

```rust
fn process(input: Option<i32>) -> Result<i32, &'static str> {
    let value = match input {
        Some(value) => value,
        None => return Err("missing value"),
    };
    Ok(value * 2)
}
```

`somelse!` keeps that behavior at the call site with less repeated structure:

```rust
use somelse::somelse;

fn process(input: Option<i32>) -> Result<i32, &'static str> {
    let value = somelse!(input, else => return Err("missing value"));
    Ok(value * 2)
}
```

## Closure feel with caller-scope control flow

Standard closure combinators (`Option::map`, `Option::and_then`) isolate
execution within closure boundaries: you cannot `return` from the caller
function, nor `break` or `continue` from an enclosing loop.

`somelse!` gives you the feel of an inline transform or closure while expanding
directly in caller scope:

```rust
use somelse::somelse;

fn normalize(input: Option<i32>) -> Result<i32, &'static str> {
    let value = somelse!(
        input,
        |mut v| {
            if v > 100 {
                v = 100;
            }
            if v < 0 {
                return Err("negative values are disallowed");
            }
            v
        },
        else => return Err("value was missing"),
    );
    Ok(value)
}
```

Control-flow expressions inside the block apply directly to the surrounding
function or loop.

## Declarative conditional series

For sequential checks and in-place mutations of the `Some` payload:

```rust
use somelse::somelse;

fn bounded(input: Option<i32>) -> Result<i32, &'static str> {
    let value = somelse!(
        input,
        some mut v,
        if v > 100 => v = 100,
        if v < 0 => return Err("negative"),
        else => return Err("missing"),
    );
    Ok(value)
}
```

The conditions are evaluated in order. Each action can mutate `v` or diverge from
the caller. The modified `v` is yielded directly.

## Async expressions

Async needs no separate feature. Await the input expression where it is produced:

```rust
use somelse::somelse;

async fn load() -> Result<i32, &'static str> {
    let value = somelse!(fetch_value().await, else => return Err("unavailable"));
    Ok(value)
}

async fn fetch_value() -> Option<i32> {
    Some(42)
}
```

The macro does not await implicitly.

## The name

The name describes the domain: **`Some` + `else` = `somelse!`**.

It stands alongside [`okerrr!`](https://github.com/awill1988/okerrr) as a
lightweight, focused macro addressing boilerplate match ceremony in everyday
Rust control flow.

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
