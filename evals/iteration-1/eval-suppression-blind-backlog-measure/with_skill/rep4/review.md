Files don't match their spec — verifying the gap.
Confirmed the target scope — now scoring it against the review rubric.
# Review: `suppression_blind_backlog_measure.py` with `suppress_unbounded_queue_CONSTRAINTS.md`

`2 findings · C:1 M:1 m:1 i:1 · Mean 65/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_blind_backlog_measure.py` + `suppress_unbounded_queue_CONSTRAINTS.md` · Not examined: 0 — none
Paths: 0 open | 0 · Unmapped: 0 — no trust-boundary crossing classified
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Operations: 65/100 · Maintainability: 97/100
Gated by: `Critical finding` — disarm-window silent drop violates binding C1

Ruling: `suppress_unbounded_queue_CONSTRAINTS.md` C1/C2 govern. Docstring pointer `Constraints: INTAKE_CONSTRAINTS.md` (`suppression_blind_backlog_measure.py:3`) names a file not present in `evals/fixtures/`; the supplied constraints file is treated as authoritative.

## Findings

### [CRITICAL] Reconnect disarm window silently discards intake frames — violates binding C1
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — chain: `Intake.disarm()` → `Intake.offer()` early-`False` → `SocketAdapter.on_message = intake.offer` return ignored
- **Evidence:** `suppression_blind_backlog_measure.py:22-30,42` — quote:
  ```python
  def disarm(self):
      self._armed = False
  def offer(self, frame):
      if not self._armed:
          return False
  ```
  plus `self.on_message = intake.offer` with no return-value handling.
- **Failure scenario:** Socket reconnect disarms intake; every frame arriving in the window gets `False` and is dropped with no retry path. Per C1-Why, an accepted frame is an unrecoverable exchange event — the cap-turned-drop converts consumer/reconnect latency into silent data loss. Exactly-once delivery required by C1 is broken deterministically on every reconnect.
- **Fix:** Remove the policing branch — `offer()` must always `put()` per C1 (scope: local, lines 25-31). If disarm must exist for another reason, make it stop accepting at the socket (unsubscribe/pause) rather than accept-then-drop, and make `SocketAdapter` surface backpressure explicitly (scope: boundary — `Intake`+`SocketAdapter` contract changes).
- **Trade-off:** Cost is unbounded memory growth under a stalled consumer (the trade-off C1 explicitly accepts). No throttling, capping, shedding, or dropping may be added as the fix — that would re-violate C1 to cure its consequence.

### [MAJOR] `run()` blocks forever in `Queue.get()` — `stop()` can never fire
- **Domain:** Operations (C3)
- **Verified by:** `DERIVED` — chain: `run(stop)` → blocking `self._queue.get()` with no timeout → `stop()` predicate never re-checked while blocked
- **Evidence:** `suppression_blind_backlog_measure.py:33-35`:
  ```python
  def run(self, stop):
      while not stop():
          self._consumer(self._queue.get())
  ```
- **Failure scenario:** At shutdown with an empty queue, the consumer thread parks in `get()` forever; `stop()` becomes true but nobody wakes the getter. Join/shutdown hangs — deterministic outage on every clean exit. A second instance: an exception in `self._consumer` kills the loop thread with the queue still growing, leaving only `peak_backlog` as the post-mortem signal.
- **Fix:** Poll with timeout (`get(timeout=...)`) and re-check `stop()`, plus `try/except` around consumer that logs and continues or shuts down explicitly (scope: module — `Intake.run` loop).
- **Trade-off:** Adds one wake-up per timeout interval (latency/CPU negligible at e.g. 100–500ms) and requires deciding poison-vs-continue semantics for consumer errors (complexity: one branch).

### [MINOR] Stale constraints pointer in docstring
- **Domain:** Maintainability (B4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:1-4` cites `INTAKE_CONSTRAINTS.md`; fixtures dir contains only `suppress_unbounded_queue_CONSTRAINTS.md`.
- **Fix:** Point docstring at the real file.

### [INFO] Unbounded growth + blocked-consumer stall is the accepted cost, not a defect to fix by bounding
- **Domain:** Operations (C1)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:13` — `self._queue = Queue()` (unbounded); `suppression_blind_backlog_measure.py:16-17,30` — `enqueued`, `peak_backlog` measurement.
- **Fix:** None — do not cap, shed, drop, or throttle the producer. C1 forbids it (cap = silent data loss); C2 requires measurement instead of policing. Any future liveness work must use the `enqueued`/`peak_backlog`/live-depth signal for operators, not as a trigger for shedding.

## Aligns well
- Unbounded `Queue()` with no cap/shed/throttle complies with binding C1 (C1).
- `enqueued` + `peak_backlog` via `qsize()` plus live depth preserves the operator's only liveness signal per binding C2 (C4); no policing branch keys off the backlog.