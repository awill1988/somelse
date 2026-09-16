#![no_std]

//! # somelse
//!
//! A `no_std` declarative macro for unwrapping and transforming `Option<T>`
//! with caller-scope control flow and diverging `else` clauses.
//!
//! ## The pattern
//!
//! A `match` lets an absence handler diverge and return from the caller:
//!
//! ```rust
//! fn process(input: Option<i32>) -> Result<i32, &'static str> {
//!     let value = match input {
//!         Some(value) => value,
//!         None => return Err("missing value"),
//!     };
//!     Ok(value * 2)
//! }
//! ```
//!
//! [`somelse!`] keeps that behavior at the call site with less repeated
//! structure:
//!
//! ```rust
//! use somelse::somelse;
//!
//! fn process(input: Option<i32>) -> Result<i32, &'static str> {
//!     let value = somelse!(input, else => return Err("missing value"));
//!     Ok(value * 2)
//! }
//! ```
//!
//! The `Some` payload continues in the surrounding scope. The `else` clause
//! handles `None` and must diverge. A handler can `return`, `break`,
//! `continue`, panic, loop forever, or call another never-returning expression.
//!
//! ## Closure feel with caller-scope control flow
//!
//! Beyond basic unwrapping, [`somelse!`] allows inserting inline transforms
//! and conditional checks while preserving caller-scope control flow:
//!
//! ```rust
//! use somelse::somelse;
//!
//! fn normalize(input: Option<i32>) -> Result<i32, &'static str> {
//!     let value = somelse!(
//!         input,
//!         |mut v| {
//!             if v > 100 {
//!                 v = 100;
//!             }
//!             if v < 0 {
//!                 return Err("negative values are disallowed");
//!             }
//!             v
//!         },
//!         else => return Err("value was missing"),
//!     );
//!     Ok(value)
//! }
//! ```
//!
//! Unlike standard closure combinators (`Option::map`, `Option::and_then`),
//! control-flow expressions inside the transform block act directly on the
//! surrounding function or loop.
//!
//! ## Declarative conditional series
//!
//! For sequential guard conditions and in-place modifications:
//!
//! ```rust
//! use somelse::somelse;
//!
//! fn bounded(input: Option<i32>) -> Result<i32, &'static str> {
//!     let value = somelse!(
//!         input,
//!         some mut v,
//!         if v > 100 => v = 100,
//!         if v < 0 => return Err("negative"),
//!         else => return Err("missing"),
//!     );
//!     Ok(value)
//! }
//! ```
//!
//! The input is evaluated exactly once. An expression containing `.await` works
//! when the invocation is in an async context; the macro does not await implicitly.

/// Extracts a `Some` payload, optionally applies inline conditionals or transforms,
/// and handles `None` through a diverging `else` clause.
///
/// # Forms
///
/// - `somelse!(expr, else => handler)`
///   Extracts the inner value of `Some`. If `None`, executes the diverging `handler`.
///
/// - `somelse!(expr, |pat| transform, else => handler)`
///   Extracts `Some(pat)` and evaluates `transform` inline within the caller's scope.
///   If `None`, executes the diverging `handler`.
///
/// - `somelse!(expr, some mut ident, $(if guard => action),+, else => handler)`
///   Sequentially evaluates guard conditions against the bound mutable payload,
///   executes matching actions, and yields the mutated value.
///
/// - `somelse!(expr, some ident, $(if guard => action),+, else => handler)`
///   Sequentially evaluates guard conditions against an immutable payload and yields it.
///
/// Every `else` handler must diverge (`return`, `break`, `continue`, panic, or
/// invoke another non-returning expression).
#[macro_export]
macro_rules! somelse {
    // Basic unwrap or diverge: else => handler
    (
        $expr:expr,
        else => $else_handler:expr $(,)?
    ) => {{
        match $expr {
            ::core::option::Option::Some(__somelse_val) => __somelse_val,
            ::core::option::Option::None => {
                #[allow(unreachable_code, clippy::diverging_sub_expression)]
                let __somelse_never: ::core::convert::Infallible = $else_handler;
                #[allow(unreachable_code, unused_variables)]
                match __somelse_never {}
            }
        }
    }};

    // Basic unwrap or diverge: else { block }
    (
        $expr:expr,
        else $else_block:block $(,)?
    ) => {
        $crate::somelse!($expr, else => $else_block)
    };

    // Closure-style inline transform: else => handler
    (
        $expr:expr,
        |$val:pat_param| $body:expr,
        else => $else_handler:expr $(,)?
    ) => {{
        match $expr {
            ::core::option::Option::Some($val) => $body,
            ::core::option::Option::None => {
                #[allow(unreachable_code, clippy::diverging_sub_expression)]
                let __somelse_never: ::core::convert::Infallible = $else_handler;
                #[allow(unreachable_code, unused_variables)]
                match __somelse_never {}
            }
        }
    }};

    // Closure-style inline transform: else { block }
    (
        $expr:expr,
        |$val:pat_param| $body:expr,
        else $else_block:block $(,)?
    ) => {
        $crate::somelse!($expr, |$val| $body, else => $else_block)
    };

    // Declarative series of conditionals (mutable binding): else => handler
    (
        $expr:expr,
        some mut $val:ident,
        $(if $guard:expr => $action:expr),+ $(,)?,
        else => $else_handler:expr $(,)?
    ) => {{
        match $expr {
            ::core::option::Option::Some(mut $val) => {
                $(
                    if $guard {
                        $action;
                    }
                )+
                $val
            }
            ::core::option::Option::None => {
                #[allow(unreachable_code, clippy::diverging_sub_expression)]
                let __somelse_never: ::core::convert::Infallible = $else_handler;
                #[allow(unreachable_code, unused_variables)]
                match __somelse_never {}
            }
        }
    }};

    // Declarative series of conditionals (mutable binding): else { block }
    (
        $expr:expr,
        some mut $val:ident,
        $(if $guard:expr => $action:expr),+ $(,)?,
        else $else_block:block $(,)?
    ) => {
        $crate::somelse!($expr, some mut $val, $(if $guard => $action),+, else => $else_block)
    };

    // Declarative series of conditionals (immutable binding): else => handler
    (
        $expr:expr,
        some $val:ident,
        $(if $guard:expr => $action:expr),+ $(,)?,
        else => $else_handler:expr $(,)?
    ) => {{
        match $expr {
            ::core::option::Option::Some($val) => {
                $(
                    if $guard {
                        $action;
                    }
                )+
                $val
            }
            ::core::option::Option::None => {
                #[allow(unreachable_code, clippy::diverging_sub_expression)]
                let __somelse_never: ::core::convert::Infallible = $else_handler;
                #[allow(unreachable_code, unused_variables)]
                match __somelse_never {}
            }
        }
    }};

    // Declarative series of conditionals (immutable binding): else { block }
    (
        $expr:expr,
        some $val:ident,
        $(if $guard:expr => $action:expr),+ $(,)?,
        else $else_block:block $(,)?
    ) => {
        $crate::somelse!($expr, some $val, $(if $guard => $action),+, else => $else_block)
    };
}

/// Convenience alias for [`somelse!`]. Prefer `somelse!` in new code.
#[macro_export]
macro_rules! some_else {
    ($($tok:tt)*) => {
        $crate::somelse!($($tok)*)
    };
}
