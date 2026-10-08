Reviewing the collapse fixture and run bundle.
Found the operational fragility patterns — now mapping the full evaluation context.
I've mapped the scoring framework — now digging into the specific operational checks.
Core defects confirmed — now checking for cross-domain impacts before scoring.
# Review: `evals/fixtures/operations_collapse.py`

`7 findings · C:0 M:6 m:1 i:0 · Mean 87/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/operations_collapse.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry point reaches a sink in this file
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 100/100 · Correctness: 80/100 · Security: 100/100 · Maintainability: 97/100 · Operations: 50/100 · Interoperability: 100/100
Gated by: `weakest domain: Operations` — mean is B, weakest evaluated domain is F, no Critical to trip the F-cap.

## Findings

### [MAJOR] Tight 503 retry with no delay, jitter, or budget
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `fetch_enrichment` lines 66-81 → `requests.post` 67-70 → `if 503: continue` 71-72, no `sleep`/`backoff`/`jitter`/`Retry-After` anywhere in file (verified by text search; only `timeout=` in file is `stop_requested.wait(timeout=60)` line 105).
- **Evidence:** `operations_collapse.py:66-72` — `for _ in range(MAX_ATTEMPTS): response = requests.post(...); if response.status_code == 503: continue`
- **Failure scenario:** Downstream starts shedding load with 503s; every caller retries immediately 3x in a tight loop, keeping it saturated. Fleet-wide this is a thundering herd that prevents recovery.
- **Fix:** Exponential backoff with jitter + respect `Retry-After`, bounded retry budget. Scope: module (`fetch_enrichment`).
- **Trade-off:** Adds latency on the degraded path (tens–hundreds of ms of sleep) and one small helper; the happy path is unchanged.

### [MAJOR] Outbound POST with no timeout, deadline, or breaker
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — chain above; `requests.post(...)` takes only `json=`, no `timeout=`; no deadline propagation, no breaker around `ENRICHMENT_ENDPOINT`.
- **Evidence:** `operations_collapse.py:67-70`
- **Failure scenario:** One slow downstream holds a worker thread indefinitely (default TCP hang is minutes). Under partial slowdown all request threads pile up; reconciler pass (lines 101-105) also blocks serially on each key.
- **Fix:** Explicit `timeout=(connect, read)` plus deadline propagation and a circuit breaker around the enrichment dependency. Scope: module.
- **Trade-off:** Timeouts turn hangs into errors — callers must handle `None`/fallback (already do); breaker adds state and tuning cost.

### [MAJOR] Unbounded never-evicted cache (growth + permanent staleness)
- **Domain:** Operations (C2)
- **Verified by:** DERIVED — `EnrichmentCache` 38-54 + docstring 39-44 + `CACHE = EnrichmentCache()` 56; no `TTL`/`expire`/`evict`/`maxsize`/`LRU` in file (verified by search).
- **Evidence:** `operations_collapse.py:38-54` — `self._entries: dict[str, Enrichment]` written on first lookup, never removed, no size ceiling, no TTL/version/invalidation.
- **Failure scenario:** Every distinct `customer_id` pins an entry for process lifetime → memory grows with cardinality until OOM. Simultaneously there is no staleness bound: a changed segment / lifetime value is served forever.
- **Fix:** Bounded cache (size cap + TTL, e.g. TTLCache) with an explicit invalidation path on source-of-truth change. Scope: module (`EnrichmentCache` + `enrich_order`).
- **Trade-off:** Adds revalidation traffic and TTL tuning; stale-while-revalidate or single-flight if hot keys stampede.

### [MAJOR] Readiness that cannot fail
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `readiness` 112-117 never probes anything; docstring 113-116 admits it answers from "process is running".
- **Evidence:** `operations_collapse.py:112-117` — `return {"status": "ready", "pid": 1, ...}`; hardcoded `pid: 1`.
- **Failure scenario:** Instance loses its ability to serve (or is misconfigured) yet keeps reporting ready, so traffic keeps arriving instead of being shed. Hardcoded `pid` also misleads on-call triage.
- **Fix:** Readiness reflects servability (and withdraws before shutdown); report `os.getpid()`. Scope: local.
- **Trade-off:** A readiness check that touches dependencies must itself be cheap/cached or it becomes a coupled-health risk; keep it a lightweight servability gate, not a deep dependency probe.

### [MAJOR] Non-daemon reconciler with no shutdown path
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `start_reconciler` 96-109 creates `Thread(...)` with default `daemon=False`, no `daemon` flag, no SIGTERM handling, no join/drain; `Not examined`: full platform shutdown wiring outside this file.
- **Evidence:** `operations_collapse.py:96-109` — `worker = threading.Thread(target=reconcile_forever, ...); worker.start(); return worker`
- **Failure scenario:** Platform asks the process to stop; the non-daemon worker blocks interpreter exit, live requests are killed instead of drained, and the 60s sleep plus a serial pass over an unbounded dict makes termination time unbounded.
- **Fix:** Daemonize or preferably register SIGTERM handling: withdraw readiness, stop intake, join worker with a grace period longer than the longest pass. Scope: boundary (process lifecycle contract).
- **Trade-off:** Graceful drain delays shutdown by up to the grace period; requires the platform grace period to actually exceed the longest request/pass.

### [MAJOR] Cache key mismatch — `get` never hits, reconciler feeds prefixed IDs
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — `get` 49-50 uses raw `customer_id`; `put` 52-53 stores `f"{CACHE_KEY_PREFIX}{...}"`; reconciler 103-104 iterates raw `CACHE._entries` keys (already prefixed) and passes them back as `customer_id`. Confirmed by AST/text execution.
- **Evidence:** `operations_collapse.py:49-53` vs `103-104`
- **Failure scenario:** Every repeat lookup misses, so every `enrich_order` pays a downstream call and the cache grows without ever serving — amplifying O1/O2/O3. The reconciler additionally looks up/fetches `"customer:<id>"` downstream, sending IDs the service never issued.
- **Fix:** Single key-construction helper used by both `get` and `put`, and iterate stored `Enrichment.customer_id`, not dict keys. Scope: module. Operations cross-references here and takes no separate deduction (owner stands).
- **Trade-off:** One helper + key migration; existing entries keyed with the prefix need a one-time clear or dual-read.

### [MINOR] Reconciler reaches into private cache state and does unbounded serial work
- **Domain:** Maintainability (B5)
- **Verified by:** READ
- **Evidence:** `operations_collapse.py:103` — `list(CACHE._entries)`; loop body 104 calls blocking `enrich_order` per key.
- **Fix:** Expose a bounded `snapshot_ids()` / `reconcile_batch(limit)` method on `EnrichmentCache` instead of touching `_entries`.

## Aligns well
- `enrich_and_time` (C4): `time.monotonic()` + `*1000` with `request_id=%s elapsed_ms=%.1f` log gives a correct, correlatable latency signal.
- No float-money or encoding defects (D3/D1): `lifetime_value_cents` stays `int` end to end; no byte truncation.
- No dead code (L1): every symbol in the 126-line file is reachable; leanness gate passes.