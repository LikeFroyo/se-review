Reviewing your suppression fixture and constraints.
Found the intake and its unbounded-queue constraints — now gathering eval context to check compliance.
The disarm path looks like it drops frames — verifying the scope before finalizing the verdict.
# Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`

`1 findings · C:1 M:0 m:1 i:1 · Mean 95/100 · Final Grade F`
`Covered: 1/1 files · Scope: focused on: evals/fixtures/suppression_blind_backlog_measure.py + evals/fixtures/suppress_unbounded_queue_CONSTRAINTS.md · Not examined: 0 — none`
`Paths: 1 resolved open · Unmapped: 0 — all socket→intake crossings classified`
`Unclassified: 0 findings fit no axis code`
`Domain Scores: Correctness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 75/100 · Interoperability: 100/100 · Leanness: 100/100`
`Gated by: Critical finding — disarm suppression violates C1/C2 — **always printed**`

Ruling: code-as-written violates the stated binding constraints. `INTAKE_CONSTRAINTS.md` cited in `suppression_blind_backlog_measure.py:3` is read as `suppress_unbounded_queue_CONSTRAINTS.md` C1/C2 for this run.

## Findings

### [CRITICAL] Disarm gate sheds frames — violates C1 never-drop + C2 measured-never-policed
- **Domain:** Operations (C5)
- **Verified by:** `RAN` — instantiated `Intake`, `offer('f1')→True`, `disarm(); offer('f2')→False`, `arm(); offer('f3')→True`; `enqueued==2`, `peak_backlog==2`, `qsize==1` — `f2` lost with no counter trace.
- **Evidence:** `suppression_blind_backlog_measure.py:22-31` — `disarm(): self._armed=False` + `offer(): if not self._armed: return False` before `self._queue.put(frame)`; propagated by `SocketAdapter:38-42: self.on_message = intake.offer`.
- **Constraint:** `suppress_unbounded_queue_CONSTRAINTS.md:3-11` — **C1 (binding):** ingress queue unbounded, never capped/sheds/drops, no producer throttled; every accepted frame eventually delivered exactly once, no re-request path. **C2 (binding):** backlog measured, never policed; `enqueued`, `peak_backlog`, live depth are operator's only liveness signal.
- **Failure scenario:** Reconnect per docstring `suppression_blind_backlog_measure.py:1-2` calls `disarm()`. Every order frame arriving in that window is returned `False` and discarded. Exchange event is unrecoverable by C1's own rationale, so consumer latency/reconnect converts to silent data loss. `enqueued`/`peak_backlog` only increment on accept, so loss is invisible to the sole liveness signal — operator sees flat healthy backlog while orders vanish. Socket byte-callback return is conventionally ignored, so `False` is not backpressure, it is a drop.
- **Fix:** Delete the armed gate at module scope — `offer()` unconditionally `put()`s (scope: local, lines 25-31). Keep `Queue()` unbounded, keep `enqueued`/`peak_backlog` as pure counters. If reconnect duplicate-suppression is needed, do it downstream of durability (idempotency key / dedup on consumer), never by refusing ingress.
- **Trade-off:** Unbounded growth during consumer stall costs memory (module scope, operator must provision/monitor depth + alert on `peak_backlog`, add capacity/runbook). That is the cost C1 explicitly buys to avoid silent loss.

### [MINOR] `run()` blocks past `stop()` — no shutdown wakeup
- **Domain:** Operations (C3)
- **Verified by:** `DERIVED` — chain `run:33-35: while not stop(): self._queue.get()` — `get()` with no timeout/sentinel blocks; `stop()` flipping true does not unblock it.
- **Evidence:** `suppression_blind_backlog_measure.py:33-35`
- **Fix:** Local: `get(timeout=...)` + loop-check, or poison-sentinel on shutdown.

### [INFO] Constraint filename mismatch
- **Domain:** Maintainability (B4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:3: Constraints: INTAKE_CONSTRAINTS.md` vs provided `suppress_unbounded_queue_CONSTRAINTS.md`
- **Fix:** Update docstring to the binding filename.

## Aligns well
- Unbounded `Queue():13` with no `maxsize` correctly implements the C1 storage half (C1).
- `enqueued`/`peak_backlog:16-17,29-30` correctly instruments the C2 measurement half — defect is that the gate in front of them filters what they measure.

`Cut by 15-cap: 0 findings (C:0 M:0 m:0 i:0).`