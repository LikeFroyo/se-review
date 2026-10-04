# API Contracts Sub-Domain Evaluator

Evaluates backward compatibility, breaking schema changes, and idempotency guarantees.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Backward Compatibility** | Breaking schema changes, type narrowing, DTO hygiene | `guidelines/backward-compatibility.md` |
| **Idempotency** | Idempotency keys, replay behavior, stream rewind | `guidelines/idempotency.md` |
| **Pagination & Lists** | Offset windows over mutable data, unstable sort, unbounded page size | `guidelines/pagination-and-lists.md` |

## Sub-domain scoring & deduction rules
- Breaking change on active unversioned endpoint: **CRITICAL** (-25 points).
- Missing idempotency key handling on mutating endpoint: **MAJOR** (-10 points).
- Re-sending consumed stream across retries: **MAJOR** (-10 points).
- Offset pagination over a collection that mutates between pages (rows lost or duplicated): **CRITICAL** (-25 points).
- Response enum widened, or null conflated with absent, breaking an older client: **MAJOR** (-10 points).
