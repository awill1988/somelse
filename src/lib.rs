#![no_std]

/// Returns a greeting string based on the given name.
///
/// If `name` is empty, returns `"hello, world"`. Otherwise, returns `"hello, crate"`.
///
/// # Examples
///
/// ```
/// use rust_crate_template::greet;
///
/// assert_eq!(greet(""), "hello, world");
/// assert_eq!(greet("rust"), "hello, crate");
/// ```
pub fn greet(name: &str) -> &'static str {
    if name.is_empty() {
        "hello, world"
    } else {
        "hello, crate"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_greet_empty() {
        assert_eq!(greet(""), "hello, world");
    }

    #[test]
    fn test_greet_non_empty() {
        assert_eq!(greet("rust"), "hello, crate");
    }
}
