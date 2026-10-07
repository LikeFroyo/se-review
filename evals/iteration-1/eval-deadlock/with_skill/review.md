Reviewing your deadlock fixture and eval run.
Found the lock-ordering bug — now mapping the full review scope.
I've pinpointed the ordering flaw — now verifying it with a live reproduction.
# Review: `evals/fixtures/deadlock.py` (lock-order inversion)

`1 findings · C:0 M:1 m:0 i:0 · Mean 95/100 · Final Grade A`
`Covered: 1/1 files · Scope: focused on: evals/fixtures/deadlock.py · Not examined: 0 — none`
`Unclassified: 0 findings fit no axis code`
`Domain Scores: Correctness: 90/100 · Leanness: 100/100 (2 of 6 domains unmeasured — grade covers the 2 assessed)`
`Gated by: neither — highest grade reached`

Mode: serial (1 file, below 30-file / 5,000-line fan-out ceiling). Second path in request (`.../se-run-eval-deadlock-with_skill-r1-1d6ff2`) is the skill/eval harness holding the fixture; harness files were not graded as product code.

## Findings

### [MAJOR] Nested lock acquisition in argument order causes deadlock
- **Domain:** Correctness (A2)
- **Verified by:** `RAN` — ran opposite-direction concurrent transfers (`A->B` / `B->A`) plus self-transfer; both threads still alive after 2s timeout
- **Evidence:** `evals/fixtures/deadlock.py:18-20` — `transfer()` in `deadlock.py:11`
```python
with source.lock:        # deadlock.py:18
    time.sleep(0.01)    # deadlock.py:19 — widens race window while holding lock
    with target.lock:    # deadlock.py:20
```
`Account.lock` is non-reentrant `threading.Lock()` (`deadlock.py:9`).
- **Failure scenario:** `DERIVED` chain: T1 `transfer(A,B)` holds `A.lock`, sleeps, waits on `B.lock`; T2 `transfer(B,A)` holds `B.lock`, waits on `A.lock` → both block forever, transfers never complete. Same root cause self-deadlocks on `transfer(X,X)`: same thread re-acquires its own non-reentrant lock at `:20`. Documented in docstring (`deadlock.py:11-17`) — documented is not resolved per ground rules.
- **Fix:** Acquire in a global order + guard identity, scope: module (`transfer` only):
```python
if source is target:
    return amount <= source.balance  # or no-op per spec, no locking
first, second = sorted((source, target), key=lambda a: a.account_id)
with first.lock:
    with second.lock:
        ...
```
Remove `sleep(0.01)` from the critical section; if real I/O is needed, do it before/after locking or use `lock.acquire(timeout=...)`.
- **Trade-off:** One string compare per transfer; negligible latency. Requires a total order — `account_id` must be unique; tie-break with `id()` if not.

## Aligns well
- Minimal 25-line fixture with per-account locks and clear `Account` / `transfer` separation (A2).
- Gate clean: no dead code, unused surface, or speculative generality found (Leanness 100/100).

`Cut by 15-cap: 0 findings (C:0 M:0 m:0 i:0). Excluded by --min: none applied.`