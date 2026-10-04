# Workflow compensation — sagas across service boundaries

Audit multi-step business flows whose steps commit independently. The question is not whether a step can fail — it is what un-does the steps that already succeeded.

## Missing compensation

- **Forward-only flow with no saga:** A multi-service business flow (reserve, charge, ship, notify) whose steps each commit on their own, with no saga record, no compensating action, and no reconciler for the partially-completed state.
- **Compensation that is not a real reversal:** An "undo" that does not restore the prior state — restocking inventory that was already shipped, or refunding a charge that had already been captured and reconciled.
- **No terminal state for the in-between:** A flow that can end in "three of four steps done" with nothing deciding whether to continue, compensate, or escalate.
- **Silent partial success:** The flow reports overall success to its caller while individual steps failed, so the caller has no signal to reconcile against.

## Compensation that cannot run

- **Compensation depends on the failed system:** The rollback path calls the same service that just failed, so a partial outage leaves the compensation unable to start.
- **Non-idempotent compensation:** A refund or reversal with no idempotency key, so a retried saga compensates the same step twice.
- **No reconciliation process:** Nothing periodically searches for flows stuck in an intermediate state, so a compensation that failed once is never retried and the inconsistency is permanent.
