# Pagination & list contracts — stable windows over changing data

Audit how a collection is paged and what a client is told to expect. A page contract that is not stable over time loses data without raising.

## What to look for

- **Offset pagination over mutable data:** A `LIMIT`/`OFFSET` or page-number walk over a collection that rows are inserted into or deleted from between requests, so rows are skipped or served twice across pages.
- **Unstable sort with ties:** Ordering by a column that is not unique, without a tiebreaker, so two pages can return the same row twice or omit it entirely.
- **Unbounded page size:** No maximum on `limit` or page size, so a client can request the whole collection in one response and the server materialises it.
- **Total count that disagrees with the page:** A `total` computed on a different filter, snapshot, or store than the rows returned, so the client cannot detect that it has missed something.
- **Snapshot not held across pages:** A multi-page read with no consistent snapshot, so a row updated mid-walk appears in one page and not the next.
- **Cursor that does not encode its position:** A pagination cursor that carries an offset or an id alone, with no filter, sort, or version, so reusing a cursor against a changed query returns a window that never existed.
