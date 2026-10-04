# Waste Sub-Domain Evaluator

Evaluates code for unnecessary weight: dead code, unearned abstractions, and redundancy.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **L1 Dead Code** | Unreachable code, orphaned symbols, proof procedure | `guidelines/dead-code.md` |
| **L1 Dead Persistence** | Unread tables, columns, migrations, config keys | `guidelines/dead-persistence.md` |
| **L2/L3 Speculative Generality** | Unused surfaces, single implementors, YAGNI | `guidelines/speculative-generality.md` |
| **L4 Redundancy** | Duplicate implementations, pass-through wrappers, un-synced forks, multi-writer state | `guidelines/redundancy.md` |

## Sub-domain scoring & deduction rules
- Every verified L1–L4 finding is **CRITICAL** (-25 points).
- Fix is always **deletion**, never improvement.
- Proof of death required before grading Critical.
- Prose explaining *why* is never L1–L4 bloat.
- Orphaned configuration or secret, or an un-synced vendored fork: **MAJOR** (-10 points).
