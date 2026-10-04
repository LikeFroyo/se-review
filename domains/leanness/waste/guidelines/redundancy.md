# Redundancy — L4 duplicate implementations and pass-through shims

Audit for unneeded duplication that taxes maintenance without delivering independent value.

## What to look for

- **Duplicate implementations:** Two separate modules or utility classes solving the same domain task in parallel.
- **Pass-through wrappers:** Classes or functions that merely forward arguments without modifying behavior, adding validation, or translating contracts.
- **Upstream re-validation:** Defensive branches re-checking invariants that the framework or caller layer already guarantees.
- **Stale compatibility shims:** Backwards-compatibility adapters or shims for deprecated runtime or library versions that are no longer supported.
- **Dead error branches:** Error checks for states that can never be reached given preceding invariants.
- **Un-synced vendored forks:** An in-tree copy of an upstream project or a generated client pinned to a version, with no tracking of upstream releases — invisible to dependency tooling, so every upstream fix becomes a hand-port.
- **Duplicated state with several writers:** The same record denormalized into two or more tables, caches, or files where no single component is authoritative and no reconciliation exists, turning a copy into a permanent divergence risk.
