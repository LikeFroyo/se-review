Reviewing the unstable pagination fixture and run directory.
Found the unstable ORDER BY and injection risks — now checking the surrounding eval context.
Identified six review domains — now loading the scoring rubrics and checklists.
# Review: `evals/fixtures/unstable_pagination.py`

`7 findings · C:2 M:3 m:1 i:1 · Mean 86/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/unstable_pagination.py` · Not examined: 0 — none
Paths: 1 · Unmapped: 0 — none, all `db.query` sinks traced to entry points
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 62/100 · Security: 75/100 · Operations: 90/100 · Interoperability: 90/100 · Maintainability: 100/100 · Leanness: 100/100
Gated by: `Critical finding` — SQL injection + silent pagination loss cap at F; weakest domain Correctness (D) also binds

## Findings

### [CRITICAL] SQL injection via string-interpolated `status` / LIMIT/OFFSET
- **Domain:** Security (S3)
- **Verified by:** DERIVED — `list_orders(page, page_size, status)` param → f-string → `db.query` sink, no validation or binding
- **Evidence:** `unstable_pagination.py:21-25` in `list_orders` — `f"WHERE status = '{status}' ORDER BY created_at LIMIT {page_size} OFFSET {offset}"` and `f"SELECT COUNT(*) FROM orders WHERE status = '{status}'"`
- **Failure scenario:** Caller passes `status="x' OR '1'='1"` or `"; DROP TABLE orders; --"` from `GET /orders?status=`; exfiltrates/alters `orders` table. Source → Boundary → Sink: `status/page_size` HTTP input → `list_orders` no-validation crossing → `db.query` SQL execution.
- **Fix:** Parameterize all inputs; scope: local. `db.query("SELECT ... WHERE status = %s ORDER BY created_at, id LIMIT %s OFFSET %s", (status, page_size, offset))`, plus allowlist `status`.
- **Trade-off:** Adds placeholder plumbing at one call site; negligible latency, requires `db.query` supports bindings — verify driver.

### [CRITICAL] Unstable LIMIT/OFFSET over non-unique `created_at` with concurrent inserts
- **Domain:** Correctness (A2)
- **Verified by:** DERIVED — `ORDER BY created_at` non-unique + `LIMIT/OFFSET` + concurrent `INSERT` shifts window; `COUNT(*)` in separate query confirms no snapshot
- **Evidence:** `unstable_pagination.py:9-26` in `list_orders` — `ORDER BY created_at LIMIT {page_size} OFFSET {offset}`; docstring admits duplicate-first-of-page-2 / missed order, total looks correct
- **Failure scenario:** Client walks pages while new orders arrive: every later row shifts down one, page N+1 first row repeats page N last row, client dedupes duplicate and silently misses one real order; reconciliation and billing undercount with no error.
- **Fix:** Keyset pagination on `(created_at, id)` with stable tiebreaker, single snapshot/repeatable-read or cursor token; scope: boundary (API contract changes from `page` to `cursor`). Minimum local hardening: `ORDER BY created_at, id`.
- **Trade-off:** Cursor pagination adds opaque-token handling and index on `(created_at, id)`; higher implementation cost but eliminates drift without locking the table.

### [MAJOR] Default `status="all"` filters to zero rows
- **Domain:** Correctness (A1)
- **Evidence:** `unstable_pagination.py:9,23` in `list_orders` — default `status="all"`Interpolated as `WHERE status = 'all'`, no branch for all-statuses
- **Failure scenario:** Default `GET /orders` invocation returns empty list; every caller using defaults sees no orders.
- **Fix:** Branch on allowlisted value: if `status == "all"` omit `WHERE` clause; else bind validated status; scope: local.
- **Trade-off:** One conditional; cost is agreeing `all` semantics with `list_order_statuses` closed set.

### [MAJOR] Unbounded `SELECT *` with no pagination
- **Domain:** Operations (C1)
- **Evidence:** `unstable_pagination.py:29-31` in `list_all_orders` — `return db.query("SELECT * FROM orders")`
- **Failure scenario:** Table growth → full-table load into memory per call, latency cliff / OOM on worker, outage under production order volume.
- **Fix:** Delete endpoint or route through keyset `list_orders`; scope: boundary (removes/rate-limits a route).
- **Trade-off:** Callers must adopt paginated iteration; slightly more round-trips, bounded memory.

### [MAJOR] Wire field mapping mismatch + projection gap
- **Domain:** Interoperability (D4)
- **Evidence:** `unstable_pagination.py:21-22,39-47` in `list_orders` + `serialize_order` — SELECT returns `id, created_at, total` but serializer reads `id/status/total/ship_date/cancelled_date` and emits `shipped_at/cancelled_at`; docstring notes `shipDate` vs `shipped_at`
- **Failure scenario:** Producer writes `ship_date`, consumer reads `shipped_at`/`cancelled_at` via `.get()` → silent `None`; `status` never selected so serialization fails/misreports; shipped/cancelled state misread across service boundary.
- **Fix:** Align projection and contract: `SELECT id, status, total, ship_date, cancelled_date, created_at` and freeze one wire name (`shipped_at` vs `shipDate`) with versioning; scope: boundary.
- **Trade-off:** Contract rename breaks existing clients; requires versioned field or dual-emit window.

### [MINOR] Unvalidated `page`/`page_size`, `MAX_PAGE_SIZE` unenforced
- **Domain:** Correctness (A8)
- **Verified by:** READ
- **Evidence:** `unstable_pagination.py:6,9,20` in `list_orders` — `MAX_PAGE_SIZE = 200` never referenced; `offset = (page - 1) * page_size` with no range check
- **Fix:** Clamp/validate: `1 <= page`, `1 <= page_size <= MAX_PAGE_SIZE`, else 422; scope: local.

### [INFO / SUGGESTION] Hardcoded status set will drift from DB
- **Domain:** Maintainability (B2)
- **Verified by:** READ
- **Evidence:** `unstable_pagination.py:34-36` in `list_order_statuses` — `{"statuses": ["pending", "paid", "shipped", "cancelled"]}`
- **Fix:** Source from single authority (DB `DISTINCT status` or shared enum) or add contract test; scope: module.

## Aligns well
- Defect documented inline at `list_orders:13-18` — admits race instead of hiding it (A6)
- `MAX_PAGE_SIZE = 200` intent declared as named constant, not magic literal (B4)