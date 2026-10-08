Reviewing target files — reading fixture and run directory.
Found classic race conditions — now mapping the full eval context.
I've mapped the core defects — now checking scoring rules for the final report.
# Review: `evals/fixtures/lost_update_race.py`

`4 findings · C:1 M:3 m:0 i:0 · Mean 89/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/lost_update_race.py` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no untrusted entry to sink traced in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 55/100 · Maintainability: 90/100 · Operations: 90/100 · Security: 100/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: `reserve() lost-update oversell` — **always printed.**

## Findings

### [CRITICAL] `reserve()` check-then-act lost update oversells stock
- **Domain:** Correctness (A2)
- **Verified by:** DERIVED — `reserve()` SELECT `available` → Python `if available < qty` → separate `UPDATE available - qty` at `DEFAULT_ISOLATION = READ COMMITTED`, no `FOR UPDATE`, no atomic predicate.
- **Evidence:** `lost_update_race.py:7,20-30` — `cur.execute("SELECT available FROM stock WHERE sku = %s")` then `cur.execute("UPDATE stock SET available = available - %s ...")`; self-documented in docstring lines 13-18.
- **Failure scenario:** Last 5 units, T1+T2 both read `available=5`, both pass check, both write `reserved+5`. Stock goes negative/oversold with no error and no row to reconcile.
- **Fix:** Single atomic reservation, scope local: `UPDATE stock SET available=available-%s, reserved=reserved+%s WHERE sku=%s AND available>=%s` and commit only if `cur.rowcount==1`, else return `reserved: False`. Or `SELECT ... FOR UPDATE` in explicit transaction.
- **Trade-off:** Adds row-lock contention on hot `sku`; cost is one contended row lock vs. silent oversell. Scope local.

### [MAJOR] `increment_view_counter()` non-atomic read-modify-write loses views
- **Domain:** Correctness (A2)
- **Verified by:** DERIVED — `SELECT views` → `current+1` in Python → `UPDATE articles SET views=%s`, same lost-update shape as `reserve()`.
- **Evidence:** `lost_update_race.py:34-41` — `cur.execute("SELECT views ...")` / `current = cur.fetchone()[0]` / `UPDATE articles SET views = %s ... (current+1)`.
- **Failure scenario:** Concurrent views read same `current`, both write `N+1`; one view permanently lost, counter drifts with no reconciliation.
- **Fix:** Atomic increment, scope local: `UPDATE articles SET views=views+1 WHERE id=%s RETURNING views`.
- **Trade-off:** Same row-lock cost as above; removes Python-side `current` return unless taken from `RETURNING`.

### [MAJOR] `read_after_write()` reads replica, breaks read-your-write
- **Domain:** Correctness (A3)
- **Verified by:** DERIVED — write path uses primary `_conn` (`stock`), confirm path opens `postgresql://replica/stock` and `SELECT`s immediately.
- **Evidence:** `lost_update_race.py:44-49` — `replica = psycopg2.connect("postgresql://replica/stock")` then `SELECT views ...`.
- **Failure scenario:** Under async replication lag, confirmation returns stale/missing row; caller retries or reports failure for a write that succeeded.
- **Fix:** Read confirmation from primary or enforce bounded staleness/causal read, scope boundary (write/confirm contract).
- **Trade-off:** Primary read adds primary load; alternative is explicit lag-aware retry with deadline, adding latency/complexity.

### [MAJOR] Module-global shared `_conn` with import-time connect
- **Domain:** Maintainability (B2)
- **Verified by:** READ
- **Evidence:** `lost_update_race.py:6` — `_conn = psycopg2.connect(...)` at import; reused by `reserve`, `increment_view_counter` with bare `_conn.commit()`, no rollback/pooling/timeout.
- **Failure scenario:** Import fails without DB; shared connection/cursor is not safe for threaded use, one failed txn poisons subsequent calls, no `rollback()` path.
- **Fix:** Per-request connection/cursor from pool with `try/except: rollback`, DSN from config/env, scope module.
- **Trade-off:** Adds pool/config plumbing vs. one global; eliminates import side-effect and cross-request state bleed.

## Aligns well
- Defect is explicitly documented in `reserve()` docstring (A1) — does not fix it per `documented is not resolved`, but makes intent auditable.