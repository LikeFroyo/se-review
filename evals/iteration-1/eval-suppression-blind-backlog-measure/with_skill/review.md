Reviewing your fixture against its constraints — pulling the files now.
Got the intake code and its constraints — now checking the surrounding eval context.
I see the pattern — an unbounded-queue constraint paired with a drop-on-disarm intake. I'll run the full review against the skill rubric.
# Review: `evals/fixtures/suppression_blind_backlog_measure.py` with `suppress_unbounded_queue_CONSTRAINTS.md`

`4 findings · C:2 M:2 m:1 i:1 · Mean 88/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_blind_backlog_measure.py` + `suppress_unbounded_queue_CONSTRAINTS.md` as binding intent · Not examined: 0 — none
Paths: 0 open · Unmapped: 0 — socket entry `SocketAdapter.on_message` classified, no attacker-controlled harm path demonstrated
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 65/100 · Operations: 70/100 · Security: 100/100 · Maintainability: 97/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps at F; weakest domain Correctness F also binds

Ruling: `suppress_unbounded_queue_CONSTRAINTS.md` C1/C2 bind over code-as-written. Where code polices what constraints say to only measure, constraints win. No fix below caps, sheds, drops, or throttles the producer.

## Findings

### [CRITICAL] Disarm window silently discards exchange frames
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — trace `SocketAdapter.__init__:42` (`self.on_message = intake.offer`) → `Intake.offer:25-27` (`if not self._armed: return False`) → socket byte-callback return ignored, frame never queued, never retried.
- **Evidence:** `suppression_blind_backlog_measure.py:22-27` — class `Intake`, methods `disarm`/`offer`:
  > `def disarm(self): self._armed = False` / `def offer(self, frame): if not self._armed: return False`
- **Failure scenario:** Reconnect calls `disarm()`. Every frame arriving in that window returns `False` and is lost. Per C1 a frame once accepted is an unrecoverable exchange event with no re-request path, so this converts consumer/reconnect latency into silent data loss violating exactly-once delivery.
- **Fix:** Remove the drop gate (scope: module). Keep accepting into the existing unbounded `Queue` while disarmed and let `enqueued`/`peak_backlog`/live depth report the spike; drain on `arm()`. If `disarm` must exist for another reason, it must not gate `offer`.
- **Trade-off:** Cost is memory growth during the window instead of data loss. Per C1/C2 that is the required trade: operator scales or waits on the backlog signal rather than losing frames.

### [CRITICAL] `run()` abandons accepted backlog on shutdown and hangs when idle
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — trace `Intake.run:33-35` (`while not stop(): self._consumer(self._queue.get())`): blocking `get()` with no timeout means `stop` is never polled when idle; when `stop()` goes true with items still queued, the loop exits without draining.
- **Evidence:** `suppression_blind_backlog_measure.py:33-35` — `Intake.run`:
  > `while not stop(): self._consumer(self._queue.get())`
- **Failure scenario:** Shutdown with 10k accepted frames queued delivers zero of them — same C1 violation as above, plus a hang: idle consumer blocks in `get()` forever after `stop()` is set, blocking graceful shutdown.
- **Fix:** Poll with timeout and drain after stop (scope: module): `get(timeout=...)` loop, then drain remaining queue with `get_nowait` before returning; add `task_done()`/`join()` if lifecycle needs it.
- **Trade-off:** Adds a wake-up latency vs. shutdown latency knob (timeout interval) and a drain phase that delays process exit proportional to backlog; no data-plane cap involved.

### [MAJOR] Consumer exception kills the pump; poison frame wedges all delivery
- **Domain:** Operations (C3)
- **Verified by:** `DERIVED` — `run:35` calls `self._consumer(...)` with no `try/except`, no DLQ, no error metric. First raising frame terminates `run`, queue grows unbounded with no delivery.
- **Evidence:** `suppression_blind_backlog_measure.py:33-35` — `Intake.run` consumer call with no guard.
- **Failure scenario:** One malformed frame raises in `_consumer`; pump thread dies; all subsequent (valid) frames queue forever. Operator sees only backlog growth with no cause signal.
- **Fix:** Guard the dispatch (scope: module): `try/except` around `_consumer`, park poison in a side queue/metric and continue; count + log with frame identity. Never drop-and-forget to "fix" the wedge — park and measure.
- **Trade-off:** Adds exception-handling + poison-storage cost (memory for parked frames, log volume); keeps liveness at the price of operator triage.

### [MAJOR] Dropped offers are blind — no count, no log, breaks C2 signal
- **Domain:** Operations (C4)
- **Verified by:** `DERIVED` — `Intake.__init__:16-17` tracks `enqueued`/`peak_backlog`; `offer:25-31` increments only on accept and emits no log on the `return False` path. `peak_backlog` via `qsize()` is also approximate.
- **Evidence:** `suppression_blind_backlog_measure.py:16-17,25-31` — `Intake.enqueued`/`peak_backlog` vs. disarm-drop path with zero telemetry.
- **Failure scenario:** During a disarm storm the operator's "only liveness signal" (C2) shows flat `enqueued` and cannot distinguish "no traffic" from "dropping everything." Silent-failure path with zero logs.
- **Fix:** Measure, never police (scope: local): add `dropped` counter + structured log/sampled metric on the drop path (while the Critical fix removes the path, keep the counter as the guard), expose live depth accessor alongside `enqueued`/`peak_backlog`.
- **Trade-off:** Negligible counter/log cost; explicitly not a cap, shed, or throttle — purely signal.

### [MINOR] Unsynchronised `_armed` gate and counters; stale constraint reference
- **Domain:** Maintainability (B4)
- **Verified by:** `READ` — `offer:26-30` check-then-act on `self._armed` plus `enqueued += 1` / `peak_backlog = max(...)` with no lock, called from socket-callback thread vs. `run` thread; docstring `1-4` cites `INTAKE_CONSTRAINTS.md` while the binding file is `suppress_unbounded_queue_CONSTRAINTS.md`.
- **Evidence:** `suppression_blind_backlog_measure.py:1-4,19-30`
- **Fix:** Local cleanup: removing the drop gate (Critical #1) deletes the `_armed` race outright; otherwise guard with a lock. Fix the docstring filename.

### [INFO / SUGGESTION] Explicit non-fix: do not bound this queue
- **Domain:** Operations (C1)
- **Verified by:** `READ` — `Intake.__init__:13` (`self._queue = Queue()`, unbounded) is correct per C1 and must stay that way.
- **Evidence:** `suppression_blind_backlog_measure.py:13` + `suppress_unbounded_queue_CONSTRAINTS.md:3-11` (C1/C2).
- **Fix:** No change. Any future pressure from unbounded growth is handled by scaling the consumer and watching `enqueued`/`peak_backlog`/live depth — never by `maxsize`, `put_nowait`-shed, `drop-oldest`, or producer throttle.

## Aligns well
- Unbounded ingress `Queue()` with no cap/shed/throttle honours C1 (C1).
- Existing `enqueued`, `peak_backlog`, live `qsize()` measurement is the correct C2 shape — extend it, do not replace it with policing (C4).