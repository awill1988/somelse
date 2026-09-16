use rust_crate_template::greet;

#[test]
fn test_integration_greet_empty() {
    assert_eq!(greet(""), "hello, world");
}

#[test]
fn test_integration_greet_name() {
    assert_eq!(greet("developer"), "hello, crate");
}
