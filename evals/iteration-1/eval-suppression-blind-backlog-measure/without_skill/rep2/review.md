Reviewing your fixtures against the constraints.
Fixture looks compliant on first pass — checking run context for blind spots.
Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md` — compliant.

* C1 (unbounded, never capped/shed/drop/throttle): pass.
  * `suppression_blind_backlog_measure.py:13` `Queue()` with no `maxsize` — unbounded.
  * `suppression_blind_backlog_measure.py:26-31` `offer()` has no size check, no cap, no shed, no drop on full; `suppression_blind_backlog_measure.py:33-35` `run()` blocking `get()` -> exactly-once delivery, no loss path.
  * `suppression_blind_backlog_measure.py:26-27` `if not armed: return False` is reconnect-gate, not backlog-policing; not driven by depth, so not a C1 cap.
* C2 (measured, never policed): pass.
  * `suppression_blind_backlog_measure.py:30` `enqueued`, `peak_backlog` + `qsize()` live depth maintained as liveness signal.
  * No policing branch on those values anywhere; `SocketAdapter:42` bridges directly to `offer` without throttle.

No silent data-loss, no backlog policing introduced.