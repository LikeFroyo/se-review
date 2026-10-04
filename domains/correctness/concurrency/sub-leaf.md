# Concurrency Sub-Domain Evaluator

Evaluates thread safety, shared mutable state, race conditions, and synchronization locks.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Race Conditions** | Check-then-act, non-atomic increments, shared state | `guidelines/race-conditions.md` |
| **Deadlocks & Locking** | Lock order, nested locks, open calls, lock contention, starvation | `guidelines/deadlocks-locking.md` |
| **Cancellation & Task Lifecycle** | Cancel propagation, task ownership, fire-and-forget | `guidelines/cancellation-lifecycle.md` |

## Sub-domain scoring & deduction rules
- Race condition causing state corruption or security bypass: **MAJOR** or **CRITICAL** (-10 to -25 points).
- Deadlock hazard under concurrency: **MAJOR** (-10 points).
- Lock held across a loop or drain, or an unfair queue starving some work: **MAJOR** (-10 points).
- Cancellation not propagated to spawned work, or a fire-and-forget task with no handle and no error handler: **CRITICAL** (-25 points).
