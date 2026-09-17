#![no_std]

//! # somelse
//!
//! A `no_std` declarative macro for extracting an `Option<T>` payload or
//! diverging from the caller on `None`.
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
//! The `Some` payload continues in the surrounding scope. The `else` expression
//! handles `None` and must diverge. A handler can `return`, `break`, `continue`,
//! panic, loop forever, or call another never-returning expression.
//!
//! The input is evaluated exactly once. Because [`somelse!`] is an expression,
//! it can be nested inside another expression or passed directly as a function
//! argument. An expression containing `.await` works when the invocation is in
//! an async context; the macro does not await implicitly.

/// Extracts a `Some` payload and handles `None` through a diverging `else`
/// expression.
///
/// Every `else` handler must diverge (`return`, `break`, `continue`, panic, or
/// invoke another non-returning expression).
///
/// A non-diverging handler is rejected:
///
/// ```compile_fail
/// use somelse::somelse;
///
/// let _: i32 = somelse!(None::<i32>, else => 0);
/// ```
#[macro_export]
macro_rules! somelse {
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
}
