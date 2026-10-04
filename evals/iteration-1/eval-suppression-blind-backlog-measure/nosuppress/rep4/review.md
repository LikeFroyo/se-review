Reviewing your flagged eval fixtures — inspecting the harness and constraints.
Only the pair found in evals — widening scope to the run context for proper review.
I've mapped the constraints against the intake code — now verifying the shutdown and backlog behavior.
# Review: `suppression_blind_backlog_measure.py` with `suppress_unbounded_queue_CONSTRAINTS.md`

`4 findings · C:0 M:2 m:1 i:1 · Mean 92/100 · Final Grade B`
`Covered: 1/1 files · Scope: focused on: evals/fixtures/suppression_blind_backlog_measure.py (authority: suppress_unbounded_queue_CONSTRAINTS.md) · Not examined: 0 — none`
`Unclassified: 0 findings fit no axis code`
`Domain Scores: Correctness: 97/100 · Operations: 80/100 · Leanness: 100/100`
`Gated by: weakest domain: Operations (B) — neither Critical cap bound`

Ruling: `suppress_unbounded_queue_CONSTRAINTS.md` C1/C2 are binding. Code is judged against them, not against generic "bound the queue" guidance.

## Findings

### [MAJOR] `Intake.run()` never observes `stop()` while idle — blocks forever in `Queue.get()`
- **Domain:** Operations (C3)
- **Verified by:** `RAN` — started `Intake(lambda x: None).run()`, set `stop_flag=True` while idle, `join(timeout=1.0)`; thread still alive.
- **Evidence:** `suppression_blind_backlog_measure.py:33-35` — `while not stop(): self._consumer(self._queue.get())` with no timeout, no sentinel, no `task_done`.
- **Failure scenario:** Every clean shutdown when the queue is empty hangs the consumer thread; non-daemon use blocks process exit, daemon use leaks the thread.
- **Fix:** Module scope. Poll with timeout (`get(timeout=...)` on `Empty` re-check `stop()`) or a shutdown sentinel. Keep unbounded queue; change wakeup only.
- **Trade-off:** Adds ~one wakeup per timeout interval (latency vs. shutdown responsiveness); sentinel is cheaper but changes the `stop()` contract at the boundary.

### [MAJOR] Consumer exception kills the loop and strands accepted backlog
- **Domain:** Operations (C3)
- **Verified by:** `RAN` — `consumer` raising `RuntimeError`, `offer` x2, thread dies, `is_alive()==False` with `qsize()==1` stranded.
- **Evidence:** `suppression_blind_backlog_measure.py:33-35` — no `try/except` around `self._consumer(...)`, no logging, no restart/DLQ.
- **Failure scenario:** One poison frame stops all subsequent delivery. Under C1 ("every accepted frame is eventually delivered exactly once") this is a liveness outage of the intake; backlog sits in the unbounded queue with no consumer. Frames are stranded, not yet dropped, so Major not Critical.
- **Fix:** Module scope. Catch per-frame exceptions, log with frame identity, continue loop (and optionally count poison frames). Do not shed backlog to "fix" this — C1 forbids caps/drops.
- **Trade-off:** Continuing past poison frames risks repeated failure on a deterministically bad frame (CPU loop); mitigate with a poison counter + alert, still without dropping.

### [MINOR] `arm/disarm/offer` check-then-act race; counters non-atomic
- **Domain:** Correctness (A2)
- **Verified by:** `DERIVED` — chain: `SocketAdapter.on_message = intake.offer` (I/O thread) `suppression_blind_backlog_measure.py:42` → `offer` checks `self._armed` then `put` `suppression_blind_backlog_measure.py:25-31` vs. concurrent `disarm()` `suppression_blind_backlog_measure.py:22-23` on reconnect thread.
- **Evidence:** `suppression_blind_backlog_measure.py:15,22-31` — plain `bool _armed`, `enqueued += 1` / `peak_backlog = max(...)` with racy `qsize()`.
- **Fix:** Local/module cleanup. Guard `_armed` + `put` + counters with a `Lock`, or document single-threaded-offer assumption.
- **Note:** `qsize()` is approximate by design; use as signal only, which already complies with C2.

### [INFO] Disarmed `offer → False` has no observable signal; docstring points at wrong constraint file
- **Domain:** Operations (C4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:1-3` cites `INTAKE_CONSTRAINTS.md`, actual authority is `suppress_unbounded_queue_CONSTRAINTS.md`; `offer:26-27` returns `False` and `SocketAdapter:42` aliases it as `on_message`, a callback shape callers typically ignore.
- **Fix:** Rename docstring reference; add a rejected-frame counter/log for the disarm window. Ambiguous whether callers check the return, so Info only.

## Aligns well

- **C1 honoured (unbounded, no policing):** `Queue()` default `maxsize=0` (`suppression_blind_backlog_measure.py:13`), verified `maxsize==0` by execution. No cap, shed, drop-after-accept, or producer throttle present. Do not "fix" growth with a bound — that would convert latency into silent loss per C1.
- **C2 honoured (measured, never policed):** `enqueued`, `peak_backlog`, live `qsize()` (`suppression_blind_backlog_measure.py:16-17,30`) are tracked and never used to reject. Verified `offer` armed increments both, disarmed changes neither.
- **Disarm is pre-accept reject, not post-accept drop:** `offer` returns `False` before `put` when disarmed. Graded as intent-ambiguous (Info above), not as a C1 violation.