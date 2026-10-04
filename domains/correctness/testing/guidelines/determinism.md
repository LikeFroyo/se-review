# Test determinism — flakiness elimination and isolation

Audit test stability, isolation, and environmental dependencies.

## What to look for

- **Sleep-based synchronization:** Using `time.sleep()` or fixed delays to await asynchronous tasks rather than polling with explicit conditions or condition variables.
- **Wall-clock time dependence:** Tests that fail across month-ends, leap years, or DST transitions because they invoke `datetime.now()` directly instead of using clock abstractions or fixed test dates.
- **Unordered container assumptions:** Asserting on the exact element order of dictionaries or sets where order is not guaranteed.
- **Shared test state:** Tests mutating global variables or database records without resetting them between runs, causing order-dependent test failures.
