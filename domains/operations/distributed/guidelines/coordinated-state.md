# Coordinated state — leases, fencing, and the records that make them work

Audit state shared across nodes where correctness depends on who is allowed to write right now, and on what the coordination record itself costs.

## Leases without fencing

- **TTL key as a lock:** A distributed lock implemented as a key with an expiry, where the holder then writes without presenting anything that proves it still holds the lease.
- **Fencing token not checked on write:** A monotonic token is issued on acquire but the storage operation does not reject a write carrying a stale one, so the guard is decorative.
- **Lock released on a timer:** Ownership released by an expiry or heartbeat rather than in a `finally`, so an exception path leaks the lease or drops it early.
- **Advisory lock assumed to be exclusive:** A database advisory lock used as a correctness guarantee where the same rows are also written by a path that does not take it.

## The coordination record's own cost

- **Unbounded deduplication store:** An inbox or dedupe table that only ever grows, with no retention policy, so the mechanism that guarantees exactly-once eventually exhausts storage.
- **Dedupe window shorter than redelivery:** A dedupe record expired sooner than the broker's maximum redelivery window, after which a duplicate is indistinguishable from a new message.
- **Leader election with no fencing:** An elected leader that writes under its own identity, so a partitioned old leader keeps writing while believing it still leads.
