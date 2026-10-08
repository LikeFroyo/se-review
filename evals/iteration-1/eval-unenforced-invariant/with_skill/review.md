Reviewing the file and run directory.
Found the comment-only preconditions. Gathering eval context.
Single-file scope confirmed — loading the review rubric.
I've mapped the defects to the rubric — now verifying them with execution.
# Review: `evals/fixtures/unenforced_invariant.py`

`5 findings · C:2 M:0 m:2 i:1 · Mean 91/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/unenforced_invariant.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust-boundary crossings identified in single-file scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 47/100 · Security: 100/100 · Leanness: 100/100 · Maintainability: 97/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` + `weakest domain: Correctness` — any Critical caps at F; weakest band is F.

Serial mode: 1 file in scope, no fan-out.

## Findings

### [CRITICAL] Advisory-only lock + transaction preconditions allow lost update / wrong score
- **Domain:** Correctness (A3)
- **Verified by:** RAN — executed module with stubbed `db`; `score_transaction('a1', 5000)` returned `15` with no lock check and no transaction check, no exception. DERIVED trace: `db.last_score` read → compute → `db.write_score` write with no atomicity.
- **Evidence:** `unenforced_invariant.py:4-20` — function `score_transaction`:
  > `# Callers must hold the account lock before calling this.`
  > `# Caller must invoke inside a transaction or the score is lost.`
  > `previous = db.last_score(account_id)` / `db.write_score(account_id, score)`
- **Failure scenario:** Two concurrent callers for the same `account_id` both read `previous=10`, both compute `10 + amount//1000`, both write — one increment is silently lost, fraud score is wrong, no error raised. A caller outside a transaction crashes after `write_score` and the score is lost. Downstream effect is a wrong fraud decision, not a call-boundary error. Documented-in-comments does not downgrade per ground rules.
- **Fix:** Enforce at the boundary, scope: boundary. Require caller to pass a held lock / transaction handle, or acquire them inside: `assert lock.held(account_id)` + `assert db.in_transaction()` as fail-fast, or move `acquire_lock` + `with db.transaction():` into the function and remove the comment contract.
- **Trade-off:** Adds lock-acquisition latency and transaction-hold time to this path; callers that already hold both pay a redundant check (nanoseconds + one branch) unless the contract is migrated to callee-owns.

### [CRITICAL] `enrich` always raises `NameError: db`
- **Domain:** Correctness (A1)
- **Verified by:** RAN — executed `enrich({'account_id':'a1'})` with stubbed `db` in `sys.modules`; observed `NameError: name 'db' is not defined`.
- **Evidence:** `unenforced_invariant.py:16,24-27` — function `enrich`: `import db` exists only as a local inside `score_transaction:16`; `enrich:26` uses global `db.tenant_for(...)` with no module-level import.
- **Failure scenario:** Every call to `enrich` raises `NameError` before dispatch. Any path that decorates a payload with tenant is a total outage for that path.
- **Fix:** Add top-level `import db`, scope: local. Delete the function-local `import db`.
- **Trade-off:** None beyond the import; no behavior change except the function becomes callable.

### [MINOR] `enrich` mutates caller dict and raises `KeyError` on missing `account_id`
- **Domain:** Correctness (A1)
- **Verified by:** READ
- **Evidence:** `unenforced_invariant.py:24-27` — function `enrich`: `payload["tenant"] = db.tenant_for(payload["account_id"])` with no key validation and in-place mutation + return of same object.
- **Fix:** Copy before decorating (`out = dict(payload)`), validate `account_id` presence and raise a typed error / return early.

### [MINOR] Unexplained magic bounds `100`, `1000`
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `unenforced_invariant.py:19` — function `score_transaction`: `score = min(100, previous + (amount_cents // 1000))`.
- **Fix:** Name constants (`MAX_SCORE = 100`, `CENTS_PER_POINT = 1000`) with unit comment.

### [INFO / SUGGESTION] No audit trail for fraud score write
- **Domain:** Operations (C4)
- **Verified by:** READ
- **Evidence:** `unenforced_invariant.py:18-20` — `db.last_score` / `db.write_score` with no structured log, correlation id, or audit record.
- **Fix:** Emit a structured log on score computation (`account_id`, `previous`, `score`, `amount_cents`); redact PII per retention policy.

## Aligns well
- Small, single-purpose helpers with type hints (`str`, `int`, `Dict[str, Any]`) — (A8).
- Integer-cents arithmetic avoids float-money rounding — (D3).