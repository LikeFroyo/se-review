# Evolvability Sub-Domain Evaluator

Evaluates how safely this code can be changed, and whether a change can be verified without standing up the whole system.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Implicit State** | Ambient time, randomness, identity, configuration read outside the signature | `guidelines/implicit-state.md` |
| **Change Surface** | Blown change blast radius, absent seams, test complexity vs code complexity | `guidelines/change-surface.md` |

## Sub-domain scoring & deduction rules
- Business rule reading ambient time, randomness, identity, or configuration so the same inputs give different answers: **CRITICAL** (-25 points).
- One rule duplicated across sites, or a change that cannot deploy independently of a schema or contract: **MAJOR** (-10 points).
- No seam at the highest-churn dependency, forcing tests to the real system: **MAJOR** (-10 points).
- Test complexity exceeding the complexity of the code it verifies: **MAJOR** (-10 points).
- Boundary behaviour or the failing path untested: **MINOR** (-3 points).
