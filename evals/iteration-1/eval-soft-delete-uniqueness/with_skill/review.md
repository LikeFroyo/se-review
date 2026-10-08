Reviewing your fixture in its self-contained workspace.
Found the fixture's flagged defects — now checking the workspace skill rules to complete the review.
I've mapped the defects to the correctness guidelines — now gathering final context for the report.
# Review: `evals/fixtures/soft_delete_uniqueness.py`

`2 findings · C:0 M:2 m:0 i:0 · Mean 97/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/soft_delete_uniqueness.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no source→boundary→sink traced in this file
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 80/100 · Security: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: weakest domain: Correctness (B) — **always printed.**

## Findings

### [MAJOR] Unique indexes span tombstone row, re-create after delete fails
- **Domain:** Correctness (A3)
- **Verified by:** DERIVED — `soft_delete()` retains row holding keys → `ux_customer_email`/`ux_customer_ref` span deleted rows → `create_customer()` inserts same key → duplicate-key/500.
- **Evidence:** `evals/fixtures/soft_delete_uniqueness.py:6-7` — `UNIQUE INDEX ux_customer_email ON customer(email) -- spans deleted rows`; `evals/fixtures/soft_delete_uniqueness.py:28-34` — `soft_delete(customer_id: int)` only sets `deleted_at`; `evals/fixtures/soft_delete_uniqueness.py:37-46` — `create_customer(email, reference_code, name)` does bare `db.insert()` with documented duplicate-key failure.
- **Failure scenario:** Delete customer, re-register same `email`/`reference_code` → DB rejects on tombstone key, handler returns 500 for an action the user was entitled to repeat.
- **Fix:** Shape first, boundary scope: partial unique indexes `WHERE deleted_at IS NULL`, or release/rotate key on `soft_delete`, or reuse tombstone row in `create_customer`. Covers both `email` and `reference_code`.
- **Trade-off:** Requires schema migration + backfill; concurrent delete/re-create needs transactional guard to avoid unique race.

### [MAJOR] Live reads and count omit deletion marker
- **Domain:** Correctness (A3)
- **Verified by:** DERIVED — `Customer.deleted_at` exists (`evals/fixtures/soft_delete_uniqueness.py:16`) but neither read filters it → archived rows returned and aggregated.
- **Evidence:** `evals/fixtures/soft_delete_uniqueness.py:49-57` — `active_customers()` uses `where={"segment": "enterprise"}` with no `deleted_at` predicate, returns archived as live; `evals/fixtures/soft_delete_uniqueness.py:60-61` — `customer_count()` same filter, total never matches visible list. One root cause, two sites.
- **Failure scenario:** After `soft_delete`, dashboard `COUNT` includes tombstones and deleted customers reappear in `active_customers` list.
- **Fix:** Local/module scope: add `deleted_at IS NULL` to both `select` and `count`, or install default live-scope.
- **Trade-off:** One extra predicate per query; add index covering `deleted_at` if table is large, negligible write cost.

## Aligns well
- `soft_delete()` archives via `deleted_at` instead of hard delete, preserving auditability.