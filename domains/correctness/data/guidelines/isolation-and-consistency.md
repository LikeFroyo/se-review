# Isolation & consistency — what concurrent writers can lose

Audit multi-writer paths for updates that read and write in separate steps across a transaction boundary, and for reads that are not guaranteed to see what was just written.

## Isolation level

- **Read-modify-write across transactions:** A value read in one transaction and written in another, or a counter updated as `read` then `set`, with no atomic operation and no row lock, so two concurrent callers both read the old value and both write — one update is lost with no error raised.
- **Default isolation relied on for an invariant:** An invariant held only because a check and its write happen to be adjacent, at an isolation level that permits another transaction to interleave between them.
- **Non-serializable aggregate update:** A sum, balance, or total maintained as a column by concurrent writers, where each writes a value derived from a stale read of the aggregate.
- **Read skew across a multi-row read:** Two rows read in separate statements or transactions that must be consistent with each other, so a reader observes a combination that never existed at a single instant.

## Consistency of what is read

- **Own write not visible:** A write followed by a read through a replica, a read-through cache, or a search index that has not caught up, so the code concludes its own write failed.
- **Constraint enforced only in the application:** Referential integrity, uniqueness, and check constraints enforced in code rather than in the schema, so a second writer or a manual fix bypasses them.
- **Soft-deleted row still participates:** A row marked deleted still occupying a unique constraint, still included in an aggregate, or still returned by a default-scoped query, so a legitimate insert is rejected and a report over-counts.
- **Counter drift with no reconciliation:** A denormalised count or total that no job ever re-derives from the source rows, so a missed increment is permanent and grows silently.
