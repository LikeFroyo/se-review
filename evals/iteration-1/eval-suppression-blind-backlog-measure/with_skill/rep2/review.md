Reviewing your suppression backlog fixtures — reading the sources now.
Got the intake code and its constraints — now checking how they connect to the rest of the eval.
Only those two fixture files exist — now pulling the review standards to judge them.
I've mapped the intake against its unbounded-queue constraints — now verifying the failure modes before writing the report.
# Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`

`3 findings · C:1 M:1 m:1 i:1 · Mean 81/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_blind_backlog_measure.py` · Not examined: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Operations: 65/100 · Correctness: 97/100
Gated by: `Critical finding` — disarm drop violates C1, caps at F regardless of mean.

## Findings

### [CRITICAL] `disarm()` sheds ingress — violates C1 unbounded/no-drop
- **Domain:** Operations (C5)
- **Verified by:** `RAN` — offered `a` armed, disarmed, offered `b`; got `False`, `enqueued=1`, `qsize=1`.
- **Evidence:** `suppression_blind_backlog_measure.py:25-27` — `if not self._armed: return False`; bridged unchecked at `:42` — `self.on_message = intake.offer`.
- **Failure scenario:** Reconnect window calls `disarm()`; socket callbacks during window return `False`, which a byte-callback ignores — frame is silently lost. C1 states accepted frames are unrecoverable exchange events with no re-request path, so latency becomes data loss.
- **Fix:** Module scope: remove `arm/disarm` gate; always `put()`. If reconnect backpressure is required, change constraint first — do not police behind a measurement.
- **Trade-off:** Unbounded memory growth under slow consumer; that is the cost C1 explicitly accepts over loss.

### [MAJOR] `run()` unresponsive shutdown, single poison frame kills consumer
- **Domain:** Operations (C3)
- **Verified by:** `DERIVED` — trace `run:33-36` → `while not stop(): consumer(queue.get())`: empty queue blocks in `get()` without timeout so `stop()` is never polled; exception in `consumer` unwinds thread, orphaning all queued frames.
- **Evidence:** `suppression_blind_backlog_measure.py:33-36` — quoted above.
- **Failure scenario:** Idle service hangs on shutdown; one bad frame stops all delivery with backlog stranded in `Queue`.
- **Fix:** Module scope: `get(timeout=...)` + `try/except` around `consumer`, `task_done()`, shutdown drain.
- **Trade-off:** Poll interval adds wake-up latency/CPU; exception containment requires DLQ/logging policy.

### [MINOR] Check-then-act race on `_armed`; approximate `peak_backlog`
- **Domain:** Correctness (A2)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:26-30` — checks `_armed`, then `put()` + `qsize()`; plain attributes shared producer/consumer with no lock.
- **Fix:** Localized cleanup: remove gate per C1; if gate stays, guard with `Lock` and note `qsize()` is approximate.

### [INFO] Stale constraint reference in docstring
- **Domain:** Maintainability (B4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:1-3` — `Constraints: INTAKE_CONSTRAINTS.md`; no such file exists — actual is `suppress_unbounded_queue_CONSTRAINTS.md`.
- **Fix:** Update docstring to the real filename.

## Aligns well
- `Queue()` unbounded with no `maxsize`, no cap/shed on storage side — complies with C1 storage half (C1).
- `enqueued`, `peak_backlog`, live `qsize()` exposes operator liveness signal — complies with C2 measure-never-police (C4).