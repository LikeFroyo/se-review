Reviewing your fixture against its constraints — checking the code now.
Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`:

Verdict: compliant with C1/C2 as written. No cap/police logic present.

C1 - unbounded, no shed/drop/throttle:
- `suppression_blind_backlog_measure.py:13` `Queue()` with default `maxsize=0` — unbounded. No cap.
- `suppression_blind_backlog_measure.py:25-31` `offer()` when armed: unconditional `put()`, always `True`. No drop, no shed, no block on producer.
- No `maxsize`, `get_nowait` shed, `if qsize() > N`, semaphore, or throttle anywhere.

C2 - measured, never policed:
- `suppression_blind_backlog_measure.py:29` `enqueued`, `suppression_blind_backlog_measure.py:30` `peak_backlog = max(..., qsize())`, live depth via `qsize()`. Present.
- Counters never used to gate `offer()` or `run()`. No policing.

Risks / gaps (not violations of current text, but load-bearing for C1 rationale):
- `suppression_blind_backlog_measure.py:22-27` `disarm()` makes `offer()` return `False` without enqueue. Not a silent drop — explicit refusal — but `suppression_blind_backlog_measure.py:42` `SocketAdapter.on_message = intake.offer` hands that `bool` to a byte-callback that typically ignores return values. If caller ignores `False`, disarm window becomes silent loss, contradicting C1 rationale (`CONSTRAINTS.md:5-8` no re-request path). No `rejected` counter, so invisible to C2 liveness signal.
- `suppression_blind_backlog_measure.py:33-35` `run()`: blocking `get()` with no timeout means `stop()` cannot interrupt a blocked wait; consumer exception kills loop and strands accepted backlog, breaking "eventually delivered exactly once".
- `suppression_blind_backlog_measure.py:30` `peak_backlog` via `qsize()` can under-report under producer/consumer race; approximate only.