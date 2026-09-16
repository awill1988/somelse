#![no_std]

use somelse::somelse;

pub struct Opaque;

pub fn ordinary(input: Option<u8>) -> Result<u8, Opaque> {
    let value = somelse!(input, else => return Err(Opaque));
    Ok(value)
}

pub fn transformed(input: Option<u8>) -> Result<u8, Opaque> {
    let value = somelse!(
        input,
        some mut v,
        if v > 100 => v = 100,
        else => return Err(Opaque),
    );
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

    #[test]
    fn test_transformed() {
        assert!(matches!(transformed(Some(120)), Ok(100)));
        assert!(matches!(transformed(Some(50)), Ok(50)));
        assert!(transformed(None).is_err());
    }
}
