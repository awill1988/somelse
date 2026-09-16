#![no_std]

use rust_crate_template::greet;

pub fn downstream_greet() -> &'static str {
    greet("downstream")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_downstream_greet() {
        assert_eq!(downstream_greet(), "hello, crate");
    }
}
