Reviewing the trust fixture and run context.
Found the auth bypass and injection — gathering evaluation context to complete the review.
# Review: `trust_by_location.py`

`3 findings · C:2 M:1 m:1 i:0 · Mean 89/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/trust_by_location.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 50/100 · Correctness: 90/100 · Maintainability: 97/100 · Operations: 97/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — **always printed.**

## Findings

### [CRITICAL] Origin-or-header auth bypass on admin function
- **Domain:** Security (S2)
- **Verified by:** DERIVED — `request.remote_addr`/`request.headers` at `trust_by_location.py:13-20` → privileged `db().execute()` at `trust_by_location.py:25`
- **Evidence:** `trust_by_location.py:20` — `if not _is_internal() and request.headers.get(INTERNAL_HEADER) != INTERNAL_TOKEN:`
- **Failure scenario:** Source: external HTTP `POST /admin/reindex?table=...` + `X-Internal-Call` header → Boundary: `and` means external caller with token passes; `_is_internal()` only checks `== "127.0.0.1"` (misses `::1`, spoofable behind proxy via `X-Forwarded-For` if trusted) → Sink: unauthenticated `reindex()` execution. Docstring at `:1` says “reachable only from loopback” but code grants external-with-token.
- **Fix:** Enforce loopback only, remove header fallback: `if not _is_internal(): return 403`. Scope: local. Bind to socket/interface or middleware allowlist, include `::1`.
- **Trade-off:** Breaks current external token clients; requires internal callers to go through loopback/proxy correctly. No latency cost.

### [CRITICAL] SQL injection via unvalidated `table` interpolation
- **Domain:** Security (S3)
- **Verified by:** DERIVED — `request.args.get("table","")` at `trust_by_location.py:22` → `f"SELECT * FROM {table}"` at `trust_by_location.py:25`
- **Evidence:** `trust_by_location.py:22-25` — `table = request.args.get("table", "")` then `db().execute(f"SELECT * FROM {table}")`
- **Failure scenario:** Source: attacker-controlled `?table=` (reachable once Finding 1 bypassed, or by malicious/compromised internal caller) → Boundary: no allowlist/validation; comment admits “shape check is left to the caller” → Sink: `execute()` with arbitrary SQL (`users; DROP TABLE ...`, `sqlite_master` exfil). Data loss/exfil.
- **Fix:** Allowlist known tables or quote identifier; reject else 400. Scope: local.
- **Trade-off:** Adds maintenance of table list; rejects dynamic tables unless allowlisted. Negligible runtime cost.

### [MAJOR] Undefined `db()` — endpoint always raises `NameError`
- **Domain:** Correctness (A1)
- **Verified by:** READ — no import/definition of `db` in `trust_by_location.py:1-27`; called at `:25`.
- **Evidence:** `trust_by_location.py:25` — `rows = db().execute(...)` with no `db` imported/defined.
- **Failure scenario:** Any `POST /admin/reindex` that passes auth raises `NameError: db`, 500. Admin reindex never works.
- **Fix:** Import/inject `db` (e.g. `from myapp.db import db`). Scope: module.
- **Trade-off:** None beyond wiring dependency; needs null/error handling for DB failures.

### [MINOR] Hardcoded internal token in source
- **Domain:** Security (S4)
- **Verified by:** READ
- **Evidence:** `trust_by_location.py:10` — `INTERNAL_TOKEN = "svc-internal-token"`
- **Fix:** Load from env/secret manager, rotate current value.

## Aligns well
- Parameterized logging `log.info("reindexed %s", table)` avoids log injection (C4).
- Narrow `request.args.get("table","")` default avoids `None` handling bug (A1).