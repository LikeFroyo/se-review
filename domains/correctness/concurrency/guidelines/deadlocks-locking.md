# Deadlocks & locking — lock ordering and contention

Audit synchronization mechanisms for deadlock hazards and excessive blocking.

## What to look for

- **Inconsistent lock ordering:** Acquiring multiple locks in different orders across different methods (e.g. Lock A then Lock B in one method; Lock B then Lock A in another).
- **Nested locks with external calls:** Calling foreign callbacks, listeners, or RPC endpoints while holding an internal mutex lock (violating the open-calls principle).
- **Unbounded lock hold times:** Performing slow disk I/O, network requests, or database transactions while holding an in-memory thread lock.
- **Double-checked locking bugs:** Implementing double-checked locking without proper memory barriers (e.g. missing `volatile` in Java or improper atomic load).

## Starvation and unfair progress

- **Lock held across a loop or a drain:** A lock acquired outside a `while` that then processes a queue, a batch, or a collection, so every item serialises behind one holder and throughput collapses to a single worker even though nothing is deadlocked.
- **Unfair queue with no reordering:** Work handed to a pool served strictly first-in-first-out with no ageing or priority, so a steady stream of small items starves the large ones indefinitely and a large item never completes.
- **Reader starving writer:** A read path with no yield point or a read preference that never lets a waiting writer take the lock, so writes stop completing under sustained read load.
- **Unbounded wait with no timeout:** A blocking acquire with no deadline and no cancellation, so a holder that never releases turns every waiter into a permanently blocked thread.
