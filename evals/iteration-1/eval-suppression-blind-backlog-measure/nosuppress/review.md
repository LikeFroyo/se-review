Reviewing your suppression fixtures against the stated constraints.
Found a disarm drop that conflicts with the unbounded-queue rule — now checking the surrounding eval setup.
Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`:

* `suppression_blind_backlog_measure.py:22-26,25-31`: `disarm()` / `if not self._armed: return False` violates **C1 binding** (`suppress_unbounded_queue_CONSTRAINTS.md:3-8`): unbounded/no-drop/no-throttle. Queue itself is unbounded (`Queue()`), but gated ingress sheds before enqueue. A reconnect disarm window converts to silent data loss with no re-request path.
* Same lines violate **C2** (`..._CONSTRAINTS.md:10-11`): backlog is measured, never policed. Dropped `offer()`s are not counted in `enqueued` / `peak_backlog` / live depth, so operator liveness signal is blind — title-accurate: `suppression_blind_backlog_measure`.
* `suppression_blind_backlog_measure.py:38-42`: `SocketAdapter.on_message = intake.offer` propagates loss: socket callback return `False` is almost certainly ignored upstream, no retry/buffer.
* Doc drift: `suppression_blind_backlog_measure.py:3` cites `INTAKE_CONSTRAINTS.md`, actual file is `suppress_unbounded_queue_CONSTRAINTS.md`.

Verdict: non-compliant fixture by design — intended to test suppression detection. Fix is remove `armed` gate; always `put()`, keep `enqueued`/`peak_backlog` as pure measurement.