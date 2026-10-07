Reviewing your concurrency fixture and eval bundle.
Found the race condition — now mapping the full eval layout.
I've got the scope and scoring rules — now verifying the findings before finalizing.
# Concurrency Review: `evals/fixtures/concurrency.py`

`1 findings · C:0 M:1 m:0 i:0 · Sub-Domain Score: 90/100 (Grade B)`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/concurrency.py` · Not examined: 0 — none
Paths: resolved open | 0 · Unmapped: 0 — none

## Findings

### [MAJOR] Unsynchronized check-then-act + read-modify-write bypasses rate limit
- **Domain:** Correctness (A2)
- **Verified by:** DERIVED — `is_rate_limited`: `if ip not in REQUEST_COUNTS` → insert (lines 17-19) races with `entry["count"]+1` → store (line 29) on shared global `REQUEST_COUNTS` (line 5) with no lock. `RAN` burst test (200 threads, barrier-aligned 100×1000 increments) showed no lost update on this CPython/GIL build — does not refute the trace; free-threaded/alternate runtimes and preemption between check and act still interleave.
- **Evidence:** `evals/fixtures/concurrency.py:5,17-19,29` — `REQUEST_COUNTS = {}` ; `if client_ip not in REQUEST_COUNTS: REQUEST_COUNTS[client_ip] = {"count": 1, ...}` ; `entry["count"] = entry["count"] + 1`
- **Failure scenario:** Burst of concurrent requests for one IP both observe missing/expired entry and reset to `count=1`, or lose increments, so counter under-counts and `count > MAX_REQUESTS (100)` never trips — attacker exceeds 100/60s window (brute-force/scrape/flood).
- **Fix:** Guard whole check-expire-increment under one `threading.Lock` (module scope, local fix); no I/O while held so no deadlock risk. Alternative: per-IP locks/striping if contention matters.
- **Trade-off:** Serializes increments (ns-scale critical section); negligible latency vs. correctness. No added memory.

## Aligns well
- Window-reset logic (`reset_at`, expiry branch) is explicit and easy to reason about (A2).
- Inline comments correctly identify both race sites rather than hiding them.