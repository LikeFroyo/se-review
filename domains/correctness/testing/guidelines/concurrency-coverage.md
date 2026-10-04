# Concurrency coverage — concurrent code checked as if it were sequential

Audit whether checks for concurrent or asynchronous code actually exercise the concurrency they
claim to cover. A race that is never interleaved is a race that has never been observed.

- **Sequential exercise of concurrent code:** Code with locks, atomic operations, or parallel branches is checked only in one thread or one at a time, so no interleaving is ever taken.
- **Single lucky run:** The concurrent path is exercised once in a favourable order rather than repeatedly under stress, where one pass proves nothing about ordering.
- **Cancellation and timeout never entered:** The timeout, cancellation, and backoff branches of concurrent code are never reached by any check.
- **Unsynchronised check state:** A check reads or writes shared mutable state across threads without its own synchronisation, making the check itself order-dependent and its failures unattributable.
- **Fixed-order awaiting:** Asynchronous results are awaited in a fixed sequence, never out of order or concurrently, so completion-order handling is untested.
- **Final-value assertion only:** The check asserts only the settled result and never inspects an intermediate state that must never be externally observable.
- **Detection enabled but never triggered:** Race or interleaving detection is switched on, but the run is too short or too quiet for a failure to ever be scheduled, so green means nothing.
