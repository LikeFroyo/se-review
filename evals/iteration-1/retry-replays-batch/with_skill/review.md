Reviewing the retry fixture and replay batch.
Found a non-idempotent ledger pattern — gathering full context for the review.
This is a targeted file review — discovering available review domains.
The retry-duplication defect is confirmed in the rubric — verifying it executes and checking remaining domains.
Execution confirms duplicates on retry — finalizing domain scoring.
# Review: work_unit_retry.py (retry replays batch)

`1 findings · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/work_unit_retry.py · Not examined: 0 — none
Paths: 0 open · Unmapped: 0 — no trust-boundary crossings in single-file batch ledger
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 100/100 · Interoperability: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Operations: 75/100 · Security: 100/100
Gated by: Critical finding — **always printed**

## Findings

### [CRITICAL] Batch retry re-applies completed ledger entries
- **Domain:** Operations (C3)
- **Verified by:** RAN — ran `run_batch(path, [{id:1},{id:2},{id:3}], failed_index=1)` then re-ran whole batch; observed `{"id":1},{"id":2}` after crash and 5 lines (`1,2,1,2,3`) after retry
- **Evidence:** `work_unit_retry.py:5-12` — `apply_entry` appends (`lines.append(json.dumps(entry))`); `work_unit_retry.py:15-20` — `run_batch` applies then raises, docstring states "retrying re-runs the whole batch from the start" with no cursor/skip
- **Failure scenario:** Crash at `failed_index=1` leaves entries 0..1 durable. Retry from index 0 appends them again, so the ledger permanently double-counts every entry before the failure. Any downstream total/billing/reconciliation over the ledger is corrupted.
- **Fix:** Module scope (`run_batch` + `apply_entry`): persist a cursor/offset of applied entries and resume after it, or make `apply_entry` idempotent by checking for an existing stable entry ID before appending and using atomic append + fsync.
- **Trade-off:** Costs one existence-check read per entry and requires stable entry IDs; cursor state adds a second durable value to keep consistent with the ledger.

## Aligns well
- Minimal, readable batch loop with explicit failure-injection parameter for testing (A6)
- No dead code, unused surface, or speculative generality (L1-L4)