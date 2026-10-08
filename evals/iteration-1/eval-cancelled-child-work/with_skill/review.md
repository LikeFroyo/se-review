Reviewing the cancelled-child fixture and run bundle.
Found several async cancellation gaps — now gathering the eval context to complete the review.
I've mapped the review framework to this async code — now examining the specific defect patterns.
I've identified the likely failure modes — now verifying them with runtime checks.
# Review: `evals/fixtures/cancelled_child_work.py` (focused)

`6 findings · C:3 M:2 m:1 i:0 · Mean 85/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/cancelled_child_work.py` · Not examined: 0 — none
Paths: 0 open · Unmapped: 2 — `httpx.AsyncClient().get()` sink and `charge()` sink reachability unverified without callers
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 25/100 · Security: 100/100 · Maintainability: 97/100 · Operations: 90/100 · Leanness: 100/100 · Interoperability: 97/100
Gated by: `Critical finding` — **always printed.**

## Findings

### [CRITICAL] Fire-and-forget `warm_cache` retains no handle and observes no error
- **Domain:** Correctness (A2)
- **Verified by:** RAN — stubbed `httpx`, called `await warm_cache('t1')`, observed `Task exception was never retrieved: AttributeError` from `rebuild_cache`; pending task had no handle and no callback.
- **Evidence:** `cancelled_child_work.py:48-51` — `asyncio.create_task(rebuild_cache(tenant_id))` with `return None`; no variable, no `await`, no `add_done_callback`, no `try/except` boundary.
- **Failure scenario:** `rebuild_cache` fails (network, DNS, 5xx) → exception lives only on the orphan task → never logged, never metered, cache stays stale while caller already returned success. Under load this also competes with request-serving work on the same loop.
- **Fix:** Module scope — `await` it in the request path, or return the `Task` to a supervised set with a done-callback that logs/meters; add panic boundary per `error-handling.md`. If backgrounding is required, use a bounded queue/worker, not per-request `create_task`.
- **Trade-off:** Awaiting adds latency of one downstream GET to the write path; a queue adds complexity (backpressure, DLQ, shutdown drain) but isolates serving from refresh.

### [CRITICAL] Undefined globals `metrics` and `charge` crash every call
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `flush_metrics('x')` raised `NameError: name 'metrics' is not defined`; `await charge_once('o1')` raised `NameError: name 'charge' is not defined`.
- **Evidence:** `cancelled_child_work.py:58-59` — `metrics.emit(metric)` with no `import metrics` and no parameter; `cancelled_child_work.py:62-66` — `charge(amount_cents=1000, order_id=order_id)` with no import/definition.
- **Failure scenario:** Any `charge_once` invocation raises before charging or after a partial charge, and any metrics flush raises — total outage of those paths, plus `charge` succeeding then `flush_metrics` raising leaves a charged-but-unrecorded order.
- **Fix:** Local scope — import/inject `metrics` and `charge` (or delete dead path); order as `charge` → persist receipt → `flush_metrics`, with `flush_metrics` failure not masking charge outcome.
- **Trade-off:** Injecting clients adds parameter/plumbing complexity; the alternative (module-global import) is cheaper but harder to fake in tests.

### [CRITICAL] Timeout return claims `cancelled` without cancelling/awaiting `export_task`
- **Domain:** Correctness (A2)
- **Verified by:** DERIVED — chain `handle_cancellation_request:35` `create_task(run_export)` → `36` `wait_for(export_task, timeout)` → `38-40` `except TimeoutError: return {"cancelled": True}` with no `export_task.cancel()`, no `await`, no `try/finally` in `run_export:44-45`.
- **Evidence:** `cancelled_child_work.py:33-41` — quoted above; `run_export` is bare `await asyncio.sleep(60)` with no `CancelledError` handling or cleanup.
- **Failure scenario:** Caller times out and reports cancelled while `run_export` keeps running up to 60s and keeps writing; a retry then double-exports. If `run_export` ever shields/ignores `CancelledError`, the leak is unbounded.
- **Fix:** Local scope — on `TimeoutError`: `export_task.cancel(); await export_task` (swallow `CancelledError`) before returning; give `run_export` a `try/finally` for partial-output cleanup.
- **Trade-off:** Awaiting cancellation adds up to cleanup latency to the timeout path; not awaiting reports fast but lies about completion.

### [MAJOR] Downstream `rebuild_cache` GET has no timeout and leaks `AsyncClient`
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — chain `warm_cache:50` fire-and-forget → `rebuild_cache:54-55` `await httpx.AsyncClient().get(f"{QUEUE}?tenant={tenant_id}")` with no `timeout=`, no caller cancellation wired, no `async with`/`aclose()`.
- **Evidence:** `cancelled_child_work.py:54-55` as quoted.
- **Failure scenario:** One slow `internal.example.com` response parks a loop task indefinitely with an open connection pool; repeated writes accumulate hung tasks/sockets and stall cache refresh with no breaker.
- **Fix:** Local scope — `async with httpx.AsyncClient(timeout=...)` or shared client with `timeout`, propagate `asyncio.timeout`/deadline from caller.
- **Trade-off:** A tight timeout adds false-negative refreshes under tail latency; needs one retry with jitter or stale-while-revalidate to avoid thundering-refresh.

### [MAJOR] `handle_order_event` gather has no partial-failure compensation
- **Domain:** Operations (C5)
- **Verified by:** DERIVED — chain `16-19` `asyncio.gather(reserve_stock(...), notify_warehouse(...))` → either branch can raise after the other already succeeded (`reserved %s` / `notified %s` at `25,30`); no `try/except`, no saga/compensating release, no `return_exceptions` handling.
- **Evidence:** `cancelled_child_work.py:13-20` — quoted `gather` with two independent side effects and bare `return {"accepted": order_id}`.
- **Failure scenario:** Stock reserved but warehouse never notified (or vice versa) → order accepted in an inconsistent state; retry double-reserves.
- **Fix:** Boundary scope — define order-placement saga: idempotency key per `order_id`, compensating `release_stock` on notify failure, or outbox + reconciler.
- **Trade-off:** Saga/outbox adds a state store and reconciler complexity versus best-effort dual-write; local `try/except` alone cannot fix crash-between-writes.

### [MINOR] `charge_once` contract promises exactly-once with no idempotency key
- **Domain:** Correctness (A4)
- **Verified by:** READ
- **Evidence:** `cancelled_child_work.py:62-66` — docstring `Charge exactly once` but signature is `(order_id)` only, no `Idempotency-Key` header/key store, no 409/422 on replay with conflicting payload.
- **Fix:** Pass through caller-supplied idempotency key with 24–48h TTL and payload-match check before executing `charge`.

## Aligns well
- `handle_order_event` uses `asyncio.gather` for independent I/O rather than serial awaits (C1).
- No invented axis codes; cancellation defects map to registered (A2) per `cancellation-lifecycle.md`.