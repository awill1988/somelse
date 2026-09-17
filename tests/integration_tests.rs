use somelse::somelse;
use std::cell::Cell;
use std::future::Future;
use std::sync::Arc;
use std::task::{Context, Poll, Wake, Waker};

struct NoopWake;

impl Wake for NoopWake {
    fn wake(self: Arc<Self>) {}
}

fn poll_ready<F: Future>(future: F) -> F::Output {
    let waker = Waker::from(Arc::new(NoopWake));
    let mut context = Context::from_waker(&waker);
    let mut future = Box::pin(future);

    match future.as_mut().poll(&mut context) {
        Poll::Ready(output) => output,
        Poll::Pending => panic!("test future unexpectedly returned pending"),
    }
}

#[test]
fn extracts_some_payload() {
    fn double(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(input, else => return Err("missing"));
        Ok(value * 2)
    }

    assert_eq!(double(Some(21)), Ok(42));
    assert_eq!(double(None), Err("missing"));
}

#[test]
fn evaluates_input_once() {
    fn extract(calls: &Cell<usize>, input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(
            {
                calls.set(calls.get() + 1);
                input
            },
            else => return Err("missing")
        );
        Ok(value)
    }

    let calls = Cell::new(0);
    assert_eq!(extract(&calls, Some(7)), Ok(7));
    assert_eq!(calls.get(), 1);

    assert_eq!(extract(&calls, None), Err("missing"));
    assert_eq!(calls.get(), 2);
}

#[test]
fn controls_enclosing_loop() {
    let items = [Some(1), None, Some(3), None, Some(5)];
    let mut sum = 0;

    for item in items {
        let value = somelse!(item, else => continue);
        sum += value;
    }

    assert_eq!(sum, 9);

    let mut sum_until_none = 0;
    for item in items {
        let value = somelse!(item, else => break);
        sum_until_none += value;
    }

    assert_eq!(sum_until_none, 1);
}

#[test]
fn accepts_explicit_panic() {
    let panic = std::panic::catch_unwind(|| {
        let input: Option<i32> = None;
        somelse!(input, else => panic!("required value was missing"))
    });

    assert!(panic.is_err());
}

#[test]
fn accepts_awaited_input_in_async_context() {
    async fn load(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(async { input }.await, else => return Err("unavailable"));
        Ok(value)
    }

    assert_eq!(poll_ready(load(Some(7))), Ok(7));
    assert_eq!(poll_ready(load(None)), Err("unavailable"));
}

#[test]
fn borrows_shared_payload_without_consuming_option() {
    fn extract(input: &Option<String>) -> Result<&str, &'static str> {
        let value = somelse!(input, else => return Err("missing"));
        Ok(value.as_str())
    }

    let input = Some(String::from("value"));
    assert_eq!(extract(&input), Ok("value"));
    assert_eq!(input.as_deref(), Some("value"));
}

#[test]
fn borrows_mutable_payload() {
    fn increment(input: &mut Option<i32>) {
        let value = somelse!(input, else => return);
        *value += 1;
    }

    let mut success = Some(1);
    increment(&mut success);
    assert_eq!(success, Some(2));

    let mut absent = None;
    increment(&mut absent);
    assert_eq!(absent, None);
}

#[test]
fn composes_inside_an_expression() {
    fn multiply(value: i32, factor: i32) -> i32 {
        value * factor
    }

    fn double(input: Option<i32>) -> Result<i32, &'static str> {
        Ok(multiply(somelse!(input, else => return Err("missing")), 2))
    }

    assert_eq!(double(Some(21)), Ok(42));
    assert_eq!(double(None), Err("missing"));
}
