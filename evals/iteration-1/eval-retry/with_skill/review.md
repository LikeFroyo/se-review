Reviewing your retry fixture and run bundle.
Found a tight retry loop — now mapping the full evaluation context.
That retry logic needs a closer look for reliability gaps — checking the remaining fixtures and rulebooks.
I've pinpointed the failure modes — now pulling the report template to finalize.
# Review: `retry.py`

`3 findings · C:0 M:3 m:1 i:1 · Covered: 1/1 files · Scope: focused on: evals/fixtures/retry.py`
`Unclassified: 0`

Target: `evals/fixtures/retry.py:8-14`:
```python
def push(payload):
    for _ in range(5):
        resp = requests.post(SYNC_URL, json=payload, timeout=TIMEOUT_S)
        if resp.status_code < 500:
            return resp
    resp.raise_for_status()
```

## Findings

### [MAJOR] Tight retry loop with no backoff/jitter
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `retry.py:10-11` `for _ in range(5): requests.post(...)` with no `sleep`, delay, jitter; trace: 5xx → immediate re-`POST`.
- **Evidence:** `evals/fixtures/retry.py:10-11`
- **Failure scenario:** Downstream returns 503 overloaded; 5 rapid retries from each client keep it saturated / thundering herd on recovery. Guideline match verbatim: `domains/operations/resilience/guidelines/retries-backoff.md:7`.
- **Fix:** Exponential backoff + jitter between attempts, honor `Retry-After` on 429/503. Scope: local.
- **Trade-off:** Adds latency to `push` (seconds) and a `time`/`random` dependency; required for recovery.

### [MAJOR] Retry of non-idempotent `POST` without idempotency key
- **Domain:** Correctness (A4)
- **Verified by:** DERIVED — `retry.py:11` re-sends `POST` to `SYNC_URL` (`.../v1/push`) with only `json=payload`; no `Idempotency-Key` header.
- **Evidence:** `evals/fixtures/retry.py:4,11`
- **Failure scenario:** Server applies push then returns 500 (or response lost); retry applies same push twice → duplicate side effect. Violates `idempotency.md:7` and `retries-backoff.md:11`.
- **Fix:** Send stable `Idempotency-Key` per logical push; server must dedupe on key + return 409/422 on key+conflicting payload. Scope: boundary (client + server contract).
- **Trade-off:** Requires key generation/storage (24-48h TTL) and server-side key store.

### [MAJOR] Transport errors bypass retry budget
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — `requests.post` raises `ConnectionError`/`Timeout` instead of returning `resp`; `retry.py:10-12` only branches on `status_code`, no `try/except`, so first blip aborts.
- **Evidence:** `evals/fixtures/retry.py:10-12`
- **Failure scenario:** Transient RST/DNS/timeout on attempt 1 raises immediately despite 5-attempt intent; most common retryable case is unretried.
- **Fix:** Catch retryable `requests` exceptions (`ConnectionError`, `Timeout`, 5xx) in loop, back off, re-raise after budget. Scope: local.
- **Trade-off:** Must distinguish retryable vs. fatal (e.g. `SSLError`, 4xx) to avoid masking auth/config errors; small complexity increase.

### [MINOR] 429 treated as success
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `retry.py:12` `if < 500: return` returns 429 to caller with no delay/retry.
- **Evidence:** `evals/fixtures/retry.py:12`
- **Fix:** Treat 429 as retryable with `Retry-After`-bounded backoff.

### [INFO] No observability / breaker
- **Domain:** Operations (C4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/retry.py:8-14` — no logging, metric, or breaker.
- **Fix:** Log attempts with attempt count/status; add breaker if `push` is hot-path.

## Aligns well
- Explicit `TIMEOUT_S = 10` on outbound `POST` (`retry.py:5,11`) — avoids system-TCP hang (C3).
- Final `raise_for_status()` surfaces persistent 5xx instead of swallowing (A1).