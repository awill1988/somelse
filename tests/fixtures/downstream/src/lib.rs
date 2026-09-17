#![no_std]

use somelse::somelse;

pub struct Opaque;

pub fn ordinary(input: Option<u8>) -> Result<u8, Opaque> {
    let value = somelse!(input, else => return Err(Opaque));
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ordinary() {
        assert!(matches!(ordinary(Some(42)), Ok(42)));
        assert!(ordinary(None).is_err());
    }
}
