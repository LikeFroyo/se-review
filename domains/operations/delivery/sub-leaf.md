# Delivery & Debt Sub-Domain Evaluator

Evaluates feature flag governance, kill-switch reliability, canary rollouts, rollback safety, and deployment configuration.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Feature Flags** | Flag taxonomy, expiration dates, safe kill switches | `guidelines/feature-flags.md` |
| **Rollout & Rollback** | Progressive canary ramps, zero-downtime rollback, change provenance | `guidelines/rollout-rollback.md` |
| **Configuration & Secrets** | Fail-open defaults, secret rotation, startup validation | `guidelines/config-and-secrets.md` |

## Sub-domain scoring & deduction rules
- Recycled feature flag key or unsafe kill-switch default: **CRITICAL** or **MAJOR** (-25 to -10 points).
- Big-bang 100% rollout of critical changes without canary ramp: **MAJOR** (-10 points).
- Unmanaged permanent flag or missing expiration date: **MINOR** (-3 points).
- Required security setting with a permissive default (fails open): **CRITICAL** (-25 points).
- Documented rollback that cannot execute against the released schema: **CRITICAL** (-25 points).
