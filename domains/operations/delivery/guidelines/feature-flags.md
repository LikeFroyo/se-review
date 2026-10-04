# Feature flags — lifecycle governance and kill-switch safety

Audit feature toggles and dynamic runtime configuration.

## What to look for

- **Unmanaged flag lifecycle:** Feature toggles lacking declared types (Release, Experiment, Ops, Permission) or expiration dates (~90 days maximum for release toggles).
- **Recycled flag keys:** Reusing previously retired flag identifiers (canonical Knight Capital failure mode).
- **Unsafe fallback defaults:** If the remote flag store is unreachable, defaulting to the risky experimental path rather than the stable baseline.
- **Untested kill switches:** Ops kill switches that have never been verified or lack clear on-call runbook procedures.
