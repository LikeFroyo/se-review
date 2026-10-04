Reviewing your suppression fixtures against the constraints.
Found a disarm path that looks like silent drop — checking how it's actually used.
Only those two files exist — running a quick check to confirm the drop behavior.
Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`:

Verdict: violates C1 and C2.

* C1 violation - `suppression_blind_backlog_measure.py:22-27`: `disarm()` makes `offer()` return `False` without enqueue. `Queue` itself is unbounded (`suppression_blind_backlog_measure.py:13`), but the armed-gate is a cap/shed: producer is throttled, frame is discarded with no re-request path. Verified: `offer('a') armed -> True`, `offer('b') disarmed -> False`, `enqueued` stays `1`.
* C2 violation - `suppression_blind_backlog_measure.py:28-31`: suppression is blind. No dropped/suppressed counter, no log, `enqueued`/`peak_backlog` don't move while disarmed. Operator cannot distinguish idle from suppressing.
* Wiring amplifies loss - `suppression_blind_backlog_measure.py:38-42`: `SocketAdapter.on_message = intake.offer` exposes the `False` directly to the socket callback. No handling/retry documented.
* Doc drift: docstring says `INTAKE_CONSTRAINTS.md` (`suppression_blind_backlog_measure.py:3`), actual file is `suppress_unbounded_queue_CONSTRAINTS.md`.

Fix: remove `disarm` reject path (`nosuppress`); keep intake always-accept unbounded, keep measuring. If a reconnect window is needed, buffer, don't return `False`.

Secondary: `run()` blocks forever on `queue.get()` (`suppression_blind_backlog_measure.py:33-35`) with no shutdown; `_armed` unsynchronized; `qsize()`-based `peak_backlog` approximate.