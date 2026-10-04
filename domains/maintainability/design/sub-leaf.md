# Design Sub-Domain Evaluator

Evaluates SOLID principles, coupling, cohesion, and architectural boundaries.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **SOLID Principles** | SRP divergent change, OCP type switches, DIP concrete dependencies | `guidelines/solid-principles.md` |
| **Coupling & Cohesion** | Circular dependencies, mutable globals, shotgun surgery | `guidelines/coupling-cohesion.md` |
| **Boundaries & DDD** | Layer breaches, leaky abstractions, domain model purity | `guidelines/boundaries-ddd.md` |

## Sub-domain scoring & deduction rules
- Circular dependencies between modules: **CRITICAL** or **MAJOR** (-25 to -10 points).
- Violations of Single Responsibility causing high coupling: **MAJOR** (-10 points).
- Direct high-level dependency on low-level infrastructure (DIP): **MAJOR** (-10 points).
- Layer breach (domain logic importing web framework/database): **MAJOR** (-10 points).
- Undefined failure contract at a module boundary, so failure and absence are indistinguishable: **MAJOR** (-10 points).
