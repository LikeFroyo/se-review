Grilling your suppression eval against its constraints — checking for blind spots.
Your fixture looks constraint-clean at first glance — now digging for hidden suppression paths.
Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`:

Compliant:

* `suppression_blind_backlog_measure.py:13`: `Queue()` unbounded, no `maxsize` — no cap.
* `suppression_blind_backlog_measure.py:25-31`: armed path never sheds/throttles, always `put`s.
* `suppression_blind_backlog_measure.py:30`: `enqueued`, `peak_backlog`, `qsize()` measured, never policed — no backlog-gated drop.

Non-compliant / blind:

1. `suppression_blind_backlog_measure.py:22-27` + `:38-42`: `disarm()` → `offer()` returns `False`, `SocketAdapter.on_message = intake.offer` swallows it. No log, no `rejected/dropped` counter, no retry/buffer. Pre-accept shed that is silent data loss — exactly what C1 forbids (`C1: never sheds/drops, no re-request path`).
2. C2 blind: `enqueued`/`peak_backlog` only count accepted frames. Disarmed window invisible to operator's "only liveness signal" — `suppression_blind_backlog_measure` by name.
3. Doc drift: `suppression_blind_backlog_measure.py:3` cites `INTAKE_CONSTRAINTS.md`, actual file is `suppress_unbounded_queue_CONSTRAINTS.md`.
4. Secondary `suppression_blind_backlog_measure.py:33-35`: `run()` blocks in `get()`, ignores `stop()` when empty; consumer exception kills loop, strands accepted frames — breaks `C1: eventually delivered exactly once`.

Verdict: fails C1/C2 as written if `disarm` overlaps traffic. Fix: remove drop-gate, or make rejection observable/recoverable with explicit counter + redelivery.