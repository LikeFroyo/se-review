Reviewing the memory leak case — inspecting its files.
Found the unbounded cache — now mapping the surrounding eval harness.
This is the only fixture — now gathering review context.
Initial triage points to an operations defect — now verifying scope across remaining domains.
Guidelines confirm the pattern — now running a quick reproduction to verify.
# Review: `evals/fixtures/memory_leak.py` (focused)

`3 findings · C:0 M:1 m:2 i:0 · Mean 97.3/100 · Final Grade A`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/memory_leak.py` · Not examined: 0 — none
Paths: none resolved · Unmapped: 0 — no trust-boundary crossing identified in single-function scope
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 100/100 · Correctness: 97/100 · Security: 100/100 · Maintainability: 97/100 · Operations: 90/100 · Interoperability: 100/100
Gated by: neither — highest grade reached — weakest domain Operations 90/100 (Grade A), mean 97.3/100 (Grade A), no Critical

Serial review (1 file, 49 lines — below fan-out ceiling).

## Findings

### [MAJOR] Unbounded global `QUERY_RESULT_CACHE` — no cap, TTL, or eviction
- **Domain:** Operations (C1)
- **Verified by:** `RAN` — imported fixture, cleared cache, called `fetch_analytics_report` 5,000x with distinct `sess-{i}/2026-01-{i}` keys and 10-row dataset: `len(QUERY_RESULT_CACHE)==5000`; duplicate key did not grow; no `ttl`/`evict`/`lru`/`maxsize` attribute exists.
- **Evidence:** `evals/fixtures/memory_leak.py:11` — `QUERY_RESULT_CACHE: Dict[str, Dict[str, Any]] = {}` module-global; `evals/fixtures/memory_leak.py:25` — `cache_key = f"{session_id}:{query_params.get('metric')}:{query_params.get('start_date')}"` high-cardinality; `evals/fixtures/memory_leak.py:43-47` — unconditional `QUERY_RESULT_CACHE[cache_key] = {...}` with `"raw_samples": raw_dataset[:100]` retained, never expired/invalidated.
- **Failure scenario:** Continuous analytics traffic uses per-session IDs. Every new session/metric/date inserts a new entry holding up to 100 raw rows. Resident memory grows monotonically until OOM kill / process restart; long-lived reporter is the outage. Matches `performance/guidelines/memory-retention.md` (unbounded collection, high-cardinality keys, object-graph retention) and `performance/guidelines/caching.md` (no staleness bound, no invalidation path).
- **Fix:** Module scope. Replace bare dict with bounded eviction: `functools.lru_cache(maxsize=N)` + TTL wrapper, or `cachetools.TTLCache(maxsize=1000, ttl=300)`, plus explicit `invalidate(session_id)` on session close; do not store `raw_samples` unless caller needs it — store aggregates only.
- **Trade-off:** Extra latency on evicted-key recompute and added complexity (clock/expiry tests, size tuning). Cost at module scope: one dependency or ~20 lines; boundary unchanged if `fetch_analytics_report` signature is kept.

### [MINOR] Partial cache key ignores remaining `query_params` and dataset identity
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — chain `fetch_analytics_report:25` key build → `fetch_analytics_report:27-28` early return. Key uses only `session_id/metric/start_date`; `metric` default (`views`), other filters, and `raw_dataset` contents/version are not in the key.
- **Evidence:** `evals/fixtures/memory_leak.py:25,27-28,31-32`
- **Fix:** Local. Include a canonical hash of all value-determining inputs in `cache_key` (sorted `query_params` items + dataset version/hash), or bypass cache when inputs are not fully keyed.

### [MINOR] Module-global mutable cache is ambient state with no seam
- **Domain:** Maintainability (B2)
- **Verified by:** `READ` — `QUERY_RESULT_CACHE` mutated in place at `memory_leak.py:43`, read at `:27`, no constructor injection, no `clear()`/reset helper, no lock.
- **Evidence:** `evals/fixtures/memory_leak.py:11,27,43`
- **Fix:** Local/module. Inject cache (parameter or small `ReportCache` class with `get/put/clear`), defaulting to current behavior, so tests can isolate without global reset.

## Aligns well
- Small single-purpose function; aggregation logic (`sum`, `count`) is straightforward — Correctness (A1).
- Defect is self-documented in module/function docstrings — Maintainability (B4).