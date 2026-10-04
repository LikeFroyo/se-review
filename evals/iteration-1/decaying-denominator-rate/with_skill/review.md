# Review: evals/fixtures/numeric_plausibility.py

`2 findings · C:0 M:1 m:1 i:0 · Mean 97/100 · Final Grade A`
Covered: 1/1 files · Scope: focused on `evals/fixtures/numeric_plausibility.py` · Not examined: 0 —
Domain Scores: Correctness: 90/100 · Operations: 97/100 · Maintainability: 100/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: neither — band A reached on mean and weakest domain

## Findings

### [MAJOR] Rate denominator decays as events age out, inflating throughput and risking division by zero
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — executed the snippet below against the file; observed `fresh-window rate: 16.64` from a single event and `immediate rate: 387143.26` from one just-recorded event (script: `cd …/se-run-…` then `python3` repro importing `ThroughputMonitor`).
- **Evidence:** `numeric_plausibility.py:24-25` — `span = time.monotonic() - self._events[0]; return len(self._events) / span`. The denominator is the age of the oldest in-window event, which *shrinks* as `prune()` drops old events. The docstring at line 20 even guards only the empty case (`if not self._events: return 0.0`), not the near-zero span.
- **Failure scenario:** A monitor in a loop records a burst, goes quiet for a window, then gets a single fresh event; `events_per_second()` reports ~17/s (or hundreds of thousands per second if called immediately), driving alerts/autoscaling on a phantom. If `time.monotonic()` returns the same tick for both calls, `span == 0.0` → unhandled `ZeroDivisionError` in the caller.
- **Fix:** Divide by the advertised window (`len(self._events) / self.window_seconds`), or by `max(span, epsilon)` with a minimum-sample guard (e.g. require `span >= 1.0` and at least 2 samples before reporting a rate). Scope: local (one method).
- **Trade-off:** Window-based rate is less responsive to recent bursts — a real burst spread over 60s reads at its average rather than its instantaneous rate; the epsilon guard adds a constant to reason about. No added latency or memory.

### [MINOR] `record()` never prunes; buffer grows unbounded if `events_per_second()` is not called
- **Domain:** Operations (C1)
- **Verified by:** `READ` — `record()` (line 11-12) only appends; pruning happens solely inside `events_per_second()` (line 21).
- **Evidence:** `numeric_plausibility.py:11-12, 19-21` — `self._events.append(time.monotonic())` with no `prune()` call site.
- **Fix:** Call `self.prune()` inside `record()` (or bound the deque). Scope: local.

## Aligns well
- `prune()` correctly uses a monotonic clock and a strict `< cutoff` comparison, and the empty-window guard is present — the defect is narrowly the denominator, not the windowing logic.
- Type hints on the public surface and a one-line module docstring state intent plainly.

**Fix scope note:** Both fixes are local to `ThroughputMonitor`; cost is a few lines and one extra `prune()` pass per record (O(k) on expired events only — no measurable latency delta).