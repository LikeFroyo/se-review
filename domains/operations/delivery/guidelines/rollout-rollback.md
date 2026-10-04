# Rollout & rollback — deployment safety and canary stages

Audit release processes, canary verification, and rollback readiness.

## What to look for

- **Big-bang rollouts:** Enabling 100% of production traffic instantly without a progressive ramp (dogfood -> canary -> staged % -> 100%).
- **Missing automated rollback:** Releases without an automated mechanism to revert traffic upon error rate spikes or latency breaches.
- **Migration deploy coupling:** Deploying code that immediately expects new database columns before those columns have been created and populated in a previous deploy.

## Rollback that cannot execute

- **Irreversible migration shipped with the code:** A dropped or renamed column, a type narrowing, or a destructive backfill released in the same deploy as the code that needs it, leaving no reversal path at all.
- **Backward-incompatible schema change:** A release where the previous version cannot read the new schema, so the documented rollback command starts a binary that immediately fails.
- **Rollback procedure never rehearsed:** A documented rollback step that has not been executed against production data, so its first real use is during the incident it was written for.
- **State written in the old shape:** A release where the previous version cannot interpret data the new version has already written, so rolling back corrupts or hides it.

## Change provenance

- **Direct production edits:** A hotfix, configuration change, or data correction applied to a running environment and never committed, so the next deploy silently reverts it and the outage it fixed returns.
