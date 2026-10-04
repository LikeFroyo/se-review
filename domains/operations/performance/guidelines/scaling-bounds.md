# Scaling bounds — how work grows with load

Audit every path whose cost grows with the size of its input or with the number of things it fans out to.

## Unbounded fan-out

- **Whole-collection parallelism:** `Promise.all`, `asyncio.gather`, a stream, or a thread pool fanned out over an unbounded result set with no semaphore or worker cap.
- **Unbounded per-item worker:** A loop spawning a goroutine, thread, or task per record with nothing bounding how many run at once.
- **Recovery as a herd:** A replay, backfill, or re-drive loop re-issuing every failed call simultaneously the moment a dependency recovers.

## Superlinear work on request-sized data

- **Nested iteration over results:** Loops over a query result nested inside another loop, where the inner data could have been indexed once.
- **Linear membership in a loop:** `in`, `.index`, or `.remove` against a list inside a loop instead of a set or dict, making the handler quadratic.
- **Repeated re-sorting or re-computation:** The same collection sorted, filtered, or serialized again per element instead of once before the loop.
- **Catastrophic regex backtracking:** A pattern with nested quantifiers or overlapping alternation applied to attacker-controlled text, where a short input can consume unbounded CPU (ReDoS).

## Unbounded request scope

- **No ceiling on bulk input:** A batch, bulk, or import endpoint with no maximum item count, so one request can demand more work than the service sized itself for.
