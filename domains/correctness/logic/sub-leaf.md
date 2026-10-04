# Logic Sub-Domain Evaluator

Evaluates core logic, boundary conditions, and exception propagation.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Edge Cases** | Boundary off-by-one, numeric float precision, time | `guidelines/edge-cases.md` |
| **Error Handling** | Swallowed exceptions, unchecked returns, causal chains, short-circuited effects | `guidelines/error-handling.md` |
| **Coercion & Types** | String truthiness, wrong-typed identifiers, unvalidated boundaries | `guidelines/coercion-and-types.md` |
| **Numeric Plausibility** | Decaying denominators, finite-but-wrong values, unguarded magnitudes | `guidelines/numeric-plausibility.md` |
| **State Machine Completeness** | Missing transitions, unreachable exits, non-idempotent effects | `guidelines/state-machine-completeness.md` |
| **Cold Start & Reset** | Low-sample behaviour, continuity across restart, what resets | `guidelines/cold-start-and-reset.md` |

## Sub-domain scoring & deduction rules
- Swallowed exception with state corruption: **CRITICAL** (-25 points).
- Boundary logic failure causing severe defect: **MAJOR** (-10 points).
- Minor unhandled edge case without state corruption: **MINOR** (-3 points).
- String truthiness or silent coercion of a wrong-typed value inverting a decision: **CRITICAL** (-25 points).
- Guard clause skipping the audit, metric, or event the success path performs: **MAJOR** (-10 points).
