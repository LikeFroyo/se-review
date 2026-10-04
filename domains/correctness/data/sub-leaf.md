# Data & State Sub-Domain Evaluator

Evaluates database queries, indexing, transactions, and schema migrations.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Query Patterns** | N+1 query loops, unbounded SELECT, missing indexes, soft-deleted scope | `guidelines/query-patterns.md` |
| **Transactions & Migrations** | ACID boundaries, long-running transactions, expand-contract | `guidelines/transactions-migrations.md` |
| **Isolation & Consistency** | Isolation level, lost updates, read skew, own-write visibility | `guidelines/isolation-and-consistency.md` |
| **Incremental Aggregate Drift** | Accumulators never reconciled against a full recompute | `guidelines/incremental-aggregate-drift.md` |

## Sub-domain scoring & deduction rules
- N+1 query loop on production read path: **MAJOR** (-10 points).
- Unatomized co-dependent writes or destructive migration: **CRITICAL** (-25 points).
- Missing index on queried foreign key: **MAJOR** (-10 points).
- Read-modify-write across transactions at the default isolation level, losing an update: **CRITICAL** (-25 points).
- Soft-deleted row still in a unique constraint or an aggregate: **MAJOR** (-10 points).
