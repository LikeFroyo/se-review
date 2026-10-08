Reviewing your lease fixture and run bundle.
Found the missing fencing defect — now mapping the full evaluation bundle.
I've charted the core race and unsafe release — now checking the remaining quality domains.
Scoring points to a gated failure — now verifying the faults hold up.
# Review: `evals/fixtures/lease_no_fencing.py`

`4 findings · C:1 M:1 m:2 i:0 · Mean 93/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/lease_no_fencing.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no crossing nothing could reach or classify
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 97/100 · Operations: 72/100 · Maintainability: 90/100 · Security: 100/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — lease without fencing token (C5)

Mode: serial — 1 file, well below 30-file / 5,000-line fan-out ceiling per `shared/domain-fanout.md`. Gate domains (security, leanness) ran first; no gate blocker before pillar scoring. Severity assigned by orchestrator.

## Findings

### [CRITICAL] Distributed lease without fencing token; stale holder writes after expiry
- **Domain:** Operations (C5)
- **Verified by:** DERIVED — trace: `acquire_lock` SET NX EX 30 → `process_batch` holds across `sleep(0.5)` loop with no renewal → key expires mid-batch → second worker `SET NX` succeeds → first worker `write_invoice` → `db.upsert_invoice` with no token. Chain spans `lease_no_fencing.py:13-21` → `45-53` → `29-42`.
- **Evidence:** `evals/fixtures/lease_no_fencing.py:20-21` — `acquire_lock`, symbol `acquire_lock`: `CLIENT.set(f"lock:{resource}", "held", nx=True, ex=LEASE_SECONDS)` / `return "held" if acquired else None`; `write_invoice`, `lease_no_fencing.py:29-42`: `db.upsert_invoice(invoice_id, amount_cents)` with no token argument and no version check; `process_batch`, `lease_no_fencing.py:45-53`: `acquire_lock("invoices")` return ignored, `finally: pass` — release left to TTL.
- **Failure scenario:** Worker A holds `lock:invoices`, stalls >30s (GC, slow `db` call, partition). Key expires. Worker B acquires, writes invoice X=$1.00. Worker A resumes, writes X=$1.00 (or different amount) believing it holds the lock. Last-writer-wins with no error; financial state corrupted in an order neither observed. `release_lock` (`lease_no_fencing.py:24-26`, `CLIENT.delete(f"lock:{resource}")` with no ownership check) extends this: A can delete B's live lock after expiry.
- **Fix:** Boundary scope. Issue monotonic fencing token on acquire (e.g. `SET key <token> NX EX`, return token); thread token through `write_invoice(invoice_id, amount, token)`; reject stale tokens at the store (`UPDATE ... WHERE fencing = $token` / Lua compare-and-delete for release); check `acquire_lock` return and abort if not held; release in `finally` via token-guarded delete, plus bound `process_batch` work to lease (renewal or chunking).
- **Trade-off:** Adds a token column / Lua script and a write-path contract change (boundary). Cost: one migration + every writer must present a token; stale writes now fail and need retry handling. Alternative of only shortening work / lengthening TTL does not fix the race.

Disputed: Correctness graded A2 Major — same root cause, owner stands with Operations which states the cross-node failure scenario. No separate deduction.

### [MAJOR] No seam at Redis/db boundary; untestable ambient state
- **Domain:** Maintainability (B2)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/lease_no_fencing.py:7-8`, symbol module `CLIENT`: `POOL = redis.ConnectionPool(host="redis.internal", ...)` / `CLIENT = redis.Redis(...)` module-global, hardcoded host; `lease_no_fencing.py:39`, symbol `write_invoice`: `import db` inline inside function, direct `db.upsert_invoice` call.
- **Failure scenario:** Any unit change to `acquire_lock` / `write_invoice` / `process_batch` requires live `redis.internal` plus real `db`; no injection point, no fake. Next change pays integration-env cost; regression verification is blocked without the fleet.
- **Fix:** Module scope. Inject client/db (constructor arg or function param with default), read host from config/env.
- **Trade-off:** Adds one parameter / config lookup and updates 3 call sites; small indirection cost for testability.

### [MINOR] Undefined `Dict` annotation; `get_type_hints` / checkers fail
- **Domain:** Correctness (A8)
- **Verified by:** RAN — executed `ast` parse confirming `Dict` name use at `lease_no_fencing.py:29` with imports limited to `Any, Optional` (`lease_no_fencing.py:3`); `exec` under stubbed `redis` succeeds on Python 3.14 only because annotations are deferred — `typing.get_type_hints(write_invoice)` raises `NameError: Dict`. Static checkers fail identically.
- **Evidence:** `evals/fixtures/lease_no_fencing.py:3` vs `:29` — `from typing import Any, Optional` but `-> Dict[str, Any]`.
- **Fix:** `from typing import Any, Dict, Optional` (or `dict[str, Any]`).

### [MINOR] Invoice writes have no audit record / correlation
- **Domain:** Operations (C4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/lease_no_fencing.py:29-42`, symbol `write_invoice`: `db.upsert_invoice` then return dict; no log, no request/correlation id, no fencing-token or holder identity emitted.
- **Fix:** Emit structured log on acquire/expiry/write with `invoice_id`, holder token, outcome.

## Aligns well
- Intent is stated honestly: docstrings at `acquire_lock` and `write_invoice` disclose the missing fencing rather than hiding it (Clarity).
- No dead code, no speculative surface, no supply-chain change in scope (Leanness L1-L5 clean).
- No cross-boundary encoding/time/numeric conversion in scope; amounts stay `int` cents on both sides (Interoperability restrained, no finding).
- Security: no attacker-reachable Source → Boundary → Sink demonstrated in this slice (parameters have no entry point inventory); capped at clean, 0 open paths. A lock-key/amount pair controlled by an untrusted caller would be a lead, not graded here without reachability.