Reviewing your fixtures against their constraints — inspecting the code and docs.
Found the unbounded-queue violation — gathering the remaining context to confirm scope.
I've mapped the core constraint conflict — now checking the review format requirements.
# Review: `suppression_blind_backlog_measure.py` vs `suppress_unbounded_queue_CONSTRAINTS.md`

`1 findings · C:1 M:0 m:0 i:1 · Covered: 1/1 files · Scope: focused`
`Unclassified: 0`

## Findings

### [CRITICAL] `disarm` window silently drops frames — violates C1
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — `SocketAdapter.on_message = intake.offer` → `Intake.offer:26-27` returns `False` without enqueue → frame never delivered, no re-request path.
- **Evidence:** `suppression_blind_backlog_measure.py:26-27`:
  ```
  if not self._armed:
      return False
  ```
  wired at `suppression_blind_backlog_measure.py:42`: `self.on_message = intake.offer`
- **Failure scenario:** Socket receives frames during reconnect `disarm()` window; all are discarded. Per constraints C1, an accepted frame is an unrecoverable exchange event — this converts consumer/reconnect latency into silent data loss, breaking "every accepted frame eventually delivered exactly once".
- **Fix:** Remove the drop path at module scope (boundary): buffer while disarmed or refuse to disarm with backlog pending; never return `False` for a received frame. Scope: module.
- **Trade-off:** Costs unbounded memory growth during outage — explicitly required by C1; operator monitors via `enqueued`/`peak_backlog`/depth instead.

### [INFO] Docstring cites wrong constraints file
- **Domain:** Maintainability (B4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_backlog_measure.py:3` says `Constraints: INTAKE_CONSTRAINTS.md`; actual file is `suppress_unbounded_queue_CONSTRAINTS.md`.
- **Fix:** Update docstring to the real filename.

## Aligns well
- **Suppressed — correctly unbounded:** `suppression_blind_backlog_measure.py:13` `Queue()` with no `maxsize` is compliant with C1 (binding: "never capped, never sheds, never drops, no producer throttled"). Do not flag as C1-unbounded-growth / CWE-770.
- **C2 compliant — measured, never policed:** `suppression_blind_backlog_measure.py:29-30` maintains `enqueued`, `peak_backlog` via `qsize()` with no cap/shed/throttle keyed off depth. This is the required liveness signal.

Ruling: code-is-wrong vs constraints-as-intent — constraints win; C1/C2 are binding.