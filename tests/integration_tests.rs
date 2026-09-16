use somelse::{some_else, somelse};
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
fn extracts_some_payload_with_block_syntax() {
    fn double(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(input, else {
            return Err("missing");
        });
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
fn closure_transforms_payload() {
    fn transform(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(input, |v| v * 3, else => return Err("empty"));
        Ok(value)
    }

    assert_eq!(transform(Some(10)), Ok(30));
    assert_eq!(transform(None), Err("empty"));
}

#[test]
fn closure_modifies_with_conditionals() {
    fn sanitize(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(
            input,
            |mut v| {
                if v > 100 {
                    v = 100;
                }
                if v < 0 {
                    return Err("negative forbidden");
                }
                v
            },
            else => return Err("missing")
        );
        Ok(value)
    }

    assert_eq!(sanitize(Some(150)), Ok(100));
    assert_eq!(sanitize(Some(42)), Ok(42));
    assert_eq!(sanitize(Some(-5)), Err("negative forbidden"));
    assert_eq!(sanitize(None), Err("missing"));
}

#[test]
fn closure_diverges_from_caller_loop() {
    let items = [Some(10), Some(0), Some(20), None];
    let mut sum = 0;

    for item in items {
        let val = somelse!(
            item,
            |v| {
                if v == 0 {
                    continue;
                }
                v
            },
            else => break
        );
        sum += val;
    }

    assert_eq!(sum, 30);
}

#[test]
fn declarative_conditional_series_modifies_in_place() {
    fn normalize(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(
            input,
            some mut val,
            if val > 100 => val = 100,
            if val < 50 => val += 10,
            if val == 0 => return Err("zero rejected"),
            else => return Err("missing")
        );
        Ok(value)
    }

    assert_eq!(normalize(Some(150)), Ok(100));
    assert_eq!(normalize(Some(30)), Ok(40));
    assert_eq!(normalize(Some(60)), Ok(60));
    assert_eq!(normalize(None), Err("missing"));
}

#[test]
fn declarative_conditional_series_with_early_exit() {
    fn validate(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(
            input,
            some mut val,
            if val < 0 => return Err("negative"),
            if val == 10 => val *= 2,
            else => return Err("missing")
        );
        Ok(value)
    }

    assert_eq!(validate(Some(10)), Ok(20));
    assert_eq!(validate(Some(-1)), Err("negative"));
    assert_eq!(validate(None), Err("missing"));
}

#[test]
fn declarative_conditional_series_immutable_binding() {
    fn check_positive(input: Option<i32>) -> Result<i32, &'static str> {
        let value = somelse!(
            input,
            some val,
            if val < 0 => return Err("negative"),
            else => return Err("missing")
        );
        Ok(value)
    }

    assert_eq!(check_positive(Some(42)), Ok(42));
    assert_eq!(check_positive(Some(-1)), Err("negative"));
    assert_eq!(check_positive(None), Err("missing"));
}

#[test]
fn some_else_alias_works() {
    fn double(input: Option<i32>) -> Result<i32, &'static str> {
        let value = some_else!(input, else => return Err("missing"));
        Ok(value * 2)
    }

    assert_eq!(double(Some(10)), Ok(20));
    assert_eq!(double(None), Err("missing"));
}
