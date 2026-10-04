# Query patterns — database access, N+1 loops, and indexing

Audit SQL, ORM operations, and database query shapes.

## What to look for

- **N+1 queries:** Executing queries inside a loop over prior results (e.g. fetching related records one by one instead of a single batched `JOIN` or `IN` query).
- **Unbounded queries:** `SELECT` queries without explicit `LIMIT` clauses on user-facing endpoints, risking memory exhaustion on large tables.
- **Missing indexes:** Queries filtering (`WHERE`), joining, or ordering by unindexed columns on production tables.
- **`SELECT *` in production:** Querying all table columns indiscriminately instead of projecting only the required fields.
- **Client-side filtering of database sets:** Pulling entire database tables into application memory to perform filtering or sorting in application code.
- **Soft-deleted rows left in scope:** A default query filter that omits the deletion marker, so archived rows are returned, counted, or aggregated as if they were live.
- **Soft-deleted rows still holding a unique key:** A uniqueness constraint spanning a deleted row, so recreating a record the user deleted fails on a key that only exists on the tombstone.
- **Aggregate including tombstones:** A `COUNT` or `SUM` over a table where soft-deleted rows are not excluded, so a reported total never matches the visible list.
