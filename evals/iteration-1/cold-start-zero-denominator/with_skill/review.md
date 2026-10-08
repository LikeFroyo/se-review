Fixing the denominator — reviewing your cold-start estimator.
Confirmed the crash path — now verifying the failure details.
Review: `evals/fixtures/cold_start_estimator.py:15-21`

**Defect — cold-start zero denominator (confirmed by execution):**
* `n=0`: `statistics.fmean([])` raises `StatisticsError` before division.
* `n=1`: `den = sum((i-mean_x)**2) = 0`, `trend()` raises `ZeroDivisionError: division by zero`. Verified: `n=0 -> StatisticsError`, `n=1 -> ZeroDivisionError`, `n=2 -> 2.0`.
* This is the textbook `cold-start-and-reset.md:8` pattern: least-squares slope / variance undefined at `n<2`.

**Fix:**
Guard at top of `trend()`:
```python
if n < 2:
    return 0.0
```
`0.0` (no trend yet) is the sane cold-start default; alternatives are `float('nan')` or raising `ValueError` — but the current implicit exception is not a contract, and empty-store-as-failure is explicitly called out as wrong.

Minor: no `capacity` validation — `deque(maxlen=0/negative)` makes `n<2` permanent; same guard covers it, but worth asserting `capacity >= 2` in `__init__`.