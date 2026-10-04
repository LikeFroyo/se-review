Reviewed `suppress_unbounded_queue.py` against its `_CONSTRAINTS.md`. Verdict: **Aligns well — no findings above Info.**

- **C1 honored**: `Queue()` has no `maxsize`, `offer()` never drops/sheds/throttles, returns `True` unconditionally — deliberate per the constraint (accepted frames are unrecoverable), not a bounded-queue defect.
- **C2 honored**: `enqueued`, `peak_backlog`, live `qsize()` are pure measurement/liveness signal; nothing polices the backlog.

Info-level only: `run()` blocks on `_queue.get()` so `stop()` is re-checked only between frames, and `peak_backlog` samples at enqueue time only. Neither rises above Info.

Review written to `ws/review.md`.