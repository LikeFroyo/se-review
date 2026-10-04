# Review: evals/fixtures/memory_leak.py

`1 finding · C:0 M:1 m:0 i:0`

## Findings

### [MAJOR] Unbounded in-memory cache accumulation causes process memory leak
- **Axis:** C1 (Performance)
- **Evidence:** `evals/fixtures/memory_leak.py:10,39-44` — `QUERY_RESULT_CACHE` is a module-level dictionary keyed by high-cardinality composite strings (`session_id:metric:start_date`). Every query executes `QUERY_RESULT_CACHE[cache_key] = ...` retaining full result dictionaries and `raw_samples` object references indefinitely, with no TTL expiry, no maximum size bound, and no eviction policy.
- **Failure scenario:** Under continuous production analytics traffic with unique session IDs, the process resident memory climbs monotonically. The Python garbage collector cannot reclaim the retained query objects because they remain strongly referenced by the global dictionary. Eventually, the Linux OOM killer will abruptly terminate the application worker process, dropping active connections and degrading availability.
- **Fix:** Replace the unbounded global dictionary with a bounded cache structure featuring size limits and time-to-live expiration (e.g. `cachetools.TTLCache(maxsize=1000, ttl=300)` or `functools.lru_cache`). For distributed deployments across multiple workers, move the cache to an external store such as Redis with explicit key expiration.
- **Trade-off:** Introducing a bounded cache means cache misses will occur under high churn, adding recomputation latency for expired or evicted session entries. Using Redis introduces network serialization overhead and a dependency on external infrastructure.

## Aligns well
- Metric calculation gracefully defaults to `"views"` if not explicitly specified in the query parameters (A1).
- Key construction incorporates all query filtering dimensions (`metric` and `start_date`) to prevent cross-filter cache collisions (A3).
