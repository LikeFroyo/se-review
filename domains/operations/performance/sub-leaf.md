# Performance Sub-Domain Evaluator

Evaluates memory retention, allocation pressure, leaks, loop efficiency, cost growth with load, and cache correctness.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Memory Retention** | Unbounded collections, memory leaks, high-cardinality keys | `guidelines/memory-retention.md` |
| **Hot Loops & Allocations** | Growth-by-append, string concatenation in loops, unbuffered I/O | `guidelines/hot-loops-allocations.md` |
| **Scaling Bounds** | Unbounded fan-out, superlinear work, unbounded result sets, ReDoS | `guidelines/scaling-bounds.md` |
| **Caching** | Staleness bounds, invalidation path, flush stampede | `guidelines/caching.md` |

## Sub-domain scoring & deduction rules
- Unbounded global cache or memory leak leading to OOM: **MAJOR** or **CRITICAL** (-10 to -25 points).
- Severe allocation pressure / blocking I/O on hot paths: **MAJOR** (-10 points).
- Minor allocation inefficiency (unpreallocated slice): **MINOR** (-3 points).
- Unbounded fan-out or superlinear work over request-sized data (handler times out at load): **CRITICAL** (-25 points).
- Cache with no invalidation path, or a flush that stampedes the origin: **MAJOR** (-10 points).
