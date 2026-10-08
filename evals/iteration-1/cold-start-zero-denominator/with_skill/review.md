Fixing on your fixture — checking its rules for the zero-denominator case.
I've got the scoring rules — now mapping the domains to grade this estimator.
The cold-start flaw checks out on paper — now running it to confirm the crash.
# Review: evals/fixtures/cold_start_estimator.py

`1 findings · C:0 M:1 m:0 i:0 · Mean 98/100 · Final Grade A`
Covered: 1/1 files · Scope: focused on: evals/fixtures/cold_start_estimator.py · Not examined: 0 — none
Paths: resolved open | 0 · Unmapped: 0 — no trust crossings in single-process numeric helper
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 90/100 · Leanness: 100/100 · Security: 100/100 · Operations: 100/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: weakest domain: Correctness (A) — no Critical, mean band A

## Findings

### [MAJOR] trend() raises on cold start (n=0, n=1) — zero denominator with no guard
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `python3 -c` importing `TrendEstimator` from `evals/fixtures/cold_start_estimator.py`; `trend()` on fresh instance raises `StatisticsError: fmean requires at least one data point` at n=0 and `ZeroDivisionError: division by zero` at n=1; n=2 returns `1.0`.
- **Evidence:** `evals/fixtures/cold_start_estimator.py:15-21` — `TrendEstimator.trend()`:
```
def trend(self) -> float:
    n = len(self._samples)
    mean_x = (n - 1) / 2
    mean_y = statistics.fmean(self._samples)
    num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(self._samples))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den
```
`den` is a derived sum that is `0` at n=0 (`range(0)` empty) and n=1 (`(0-0)**2 = 0`); `fmean([])` fails before the division at n=0. No `n < 2` guard, no documented minimum-sample contract.
- **Failure scenario:** Every fresh `TrendEstimator` crashes on its first two `trend()` polls. Any caller polling slope from startup (dashboard, autoscaler, alert threshold) gets an unhandled exception on exactly the cold-start path described in `domains/correctness/logic/guidelines/cold-start-and-reset.md` ("variance at n=1") and `domains/correctness/logic/guidelines/numeric-plausibility.md` ("ratio over a derived denominator ... with no guard"). Deterministic, not a rare race.
- **Fix:** Scope: local — add a cold-start guard at the top of `trend()`, e.g. `if n < 2: return 0.0` (neutral slope) or `raise ValueError("need >=2 samples")` with documented contract. Covers both n=0 and n=1 sites as one root cause.
- **Trade-off:** Returning `0.0` costs one branch and risks masking "no data" as "flat" to callers that distinguish them; raising `ValueError` costs caller handling but is fail-fast. Either is O(1) latency/memory.

## Aligns well
- Bounded memory via `deque(maxlen=capacity)` (C1): no unbounded growth.
- No dead code or speculative surface; minimal class earns its place (L1–L3).
- No trust boundary, injection sink, or secret handling; no open security path (S1–S4).
- Single-process floats with no encoding/time/wire crossing; no interoperability defect (D1–D4).