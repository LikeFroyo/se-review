Reviewing your unchecked casts fixtures — inspecting the run.
Got it — running a full multi-domain review on that file.
This file is all unchecked types and loose payloads — pulling the relevant checks to grade it.
I've mapped the main risk areas — now verifying the final scoring details.
# Review: `evals/fixtures/unchecked_casts.py`

`9 findings · C:3 M:6 m:0 i:0 · Mean 77/100 · Final Grade F`
`Covered: 1/1 files · Scope: focused on: evals/fixtures/unchecked_casts.py · Not examined: 0 — none`
`Paths: 0 · Unmapped: 0 — no attacker-reachable source→boundary→sink demonstrated`
`Unclassified: 0 findings fit no axis code`
`Domain Scores: Correctness: 10/100 · Security: 100/100 · Maintainability: 90/100 · Interoperability: 75/100 · Operations: 90/100 · Leanness: 100/100`
`Gated by: Critical finding — weakest domain: Correctness (F)`

Serial review (1 file, 66 lines; below fan-out ceiling). All line cites below are `unchecked_casts.py`.

## Findings

### [CRITICAL] Payment client and response fully unchecked on money path
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `PAYMENT_CLIENT: Any` (line 6) → `PAYMENT_CLIENT.post(...)` (line 26) resolves to nothing → `response: Any` → `response.json()` (line 27) returned as `Dict[str, Any]` with no field, status, or error check.
- **Evidence:** `unchecked_casts.py:6,20-27` — `PAYMENT_CLIENT: Any = httpx.Client(...)`; `response: Any = PAYMENT_CLIENT.post("/charges", json={"amount": amount, "card": card})`; `return response.json()`.
- **Failure scenario:** Gateway returns an error, HTML page, or `{error: ...}` shape; `.json()` raises or returns a non-charge dict that the caller treats as a successful charge. Wrong amount charged with no detection; type checker is silent because both ends are `Any`.
- **Fix:** Define a narrow `ChargeResult` (TypedDict/dataclass), validate `response.status_code`, parse with explicit required-field checks, raise on error. Scope: module.
- **Trade-off:** Adds a response schema plus one error branch; one extra parse step per charge, negligible vs network cost.

### [CRITICAL] Webhook ledger insert trusts unshaped dict on money path
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `entry: dict` (line 30) → `entry["account"]`, `entry["amount"]`, `entry["postedAt"]` (lines 37-40) → `LEDGER.insert(...)` where `LEDGER: Any` (line 7), so missing keys raise `KeyError` at write time and wrong types post silently.
- **Evidence:** `unchecked_casts.py:7,30-41` — `LEDGER: Any = None`; `LEDGER.insert(account=entry["account"], amount=entry["amount"], ... posted_at=entry["postedAt"])`.
- **Failure scenario:** Producer omits `amount` or sends a string `"12.50"` vs decimal; ledger posts a corrupt/missing-money row or crashes the webhook worker mid-batch. `currency` default further masks a missing required field.
- **Fix:** Validate webhook against a single `LedgerEntry` schema (required keys, types, `postedAt` format) before `insert`; reject unknown/missing with a 4xx, no default for required fields. Scope: boundary.
- **Trade-off:** Adds a schema plus validation at the webhook boundary; producers sending bad payloads now fail loudly instead of posting silently.

### [CRITICAL] Money held and transported as binary float
- **Domain:** Interoperability (D3)
- **Verified by:** DERIVED — `charge(amount: float, ...)` (line 20) → serialised to JSON `{"amount": amount}` (line 26); `total_for(...) -> float` sums `float(...)` values (line 50) — both sides carry money as IEEE-754 float, so `0.1+0.2 != 0.3` and cent-level drift accumulates.
- **Evidence:** `unchecked_casts.py:20,26,44-50` — `def charge(amount: float, ...)`; `json={"amount": amount, ...}`; `return sum(float(e.get("amount", 0)) for e in entries)`.
- **Failure scenario:** Batch totals disagree with per-row sums by cents; ledger vs gateway reconciliation never matches. Cross-references Correctness A8 float coercion; owner here because the defect is the cross-boundary representation.
- **Fix:** Use integer minor units or `Decimal` with fixed scale end-to-end (API contract + ledger + summation). Scope: boundary.
- **Trade-off:** Requires contract migration (gateway + ledger + feed agree on units/scale); short-term conversion shims at each reader until cutover.

### [MAJOR] Order lookup trusts DB row as typed dict
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `connection: Any` (line 8) → `.execute(...).fetchone()` (line 16) → `dict(row)` returned as `Optional[Dict[str, Any]]` (line 17) with no column, nullability, or type check.
- **Evidence:** `unchecked_casts.py:8,11-17` — `row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()`; `return dict(row) if row else None`.
- **Failure scenario:** Schema rename or NULL column flows downstream as a mistyped value; `SELECT *` widens the blast radius to every future column. Callers index keys that are silently absent.
- **Fix:** Project explicit columns and validate the row into an `Order` record before returning. Scope: module.
- **Trade-off:** Adds a record type plus per-query column list; schema changes now touch the query instead of flowing through silently.

### [MAJOR] Ledger total masks missing amounts as zero with string coercion
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `entries: List[dict]` (line 44) → `e.get("amount", 0)` (line 50) → `float(...)` — absent maps to `0.0`, `"abc"` raises `ValueError` mid-sum, and `"12"` coerces silently.
- **Evidence:** `unchecked_casts.py:44-50` — `def total_for(entries: List[dict]) -> float:`; `return sum(float(e.get("amount", 0)) for e in entries)`.
- **Failure scenario:** Feed drops `amount` on 5% of rows; reported total is silently short and the shortfall is indistinguishable from real zeros. Cross-ref Interoperability (D4) absent-consumed-as-zero; owned here by the demonstrated wrong-total trace.
- **Fix:** Require `amount` per entry, parse with a strict decimal parser, reject missing/malformed rows loudly. Scope: local.
- **Trade-off:** Malformed feeds now fail the batch instead of producing a plausible-but-wrong total; needs a dead-letter path for bad rows.

### [MAJOR] Dynamic config lookup used as typed value
- **Domain:** Correctness (A8)
- **Verified by:** READ
- **Evidence:** `unchecked_casts.py:53-55` — `def config_value(key: str) -> Any: return getattr(connection, key, None)`.
- **Failure scenario:** Typo in `key` returns `None`, which callers use as a real config value; misconfiguration becomes a wrong default rather than a startup failure. No record of what keys exist.
- **Fix:** Replace string-keyed lookup with an explicit config object / allowlist and fail on unknown keys. Scope: module.
- **Trade-off:** Adds a config schema; dynamic callers must migrate to declared keys.

### [MAJOR] Status read assumes a schema the payload does not guarantee
- **Domain:** Correctness (A8)
- **Verified by:** DERIVED — `raw: dict` (line 58) → `raw["status"]` (line 65) → `.upper()` (line 66); a `state`-renamed or non-string payload raises `KeyError`/`AttributeError` instead of degrading.
- **Evidence:** `unchecked_casts.py:58-66` — `status: str = raw["status"]`; `return status.upper()`.
- **Failure scenario:** Producer renames `status` to `state` or emits `null`; every consumer crashes. The annotation `str` suppresses the check rather than enforcing it. Cross-ref Interoperability (D4) versioning fragility; owned here by the crash trace.
- **Fix:** Validate `raw` against a versioned payload schema; reject unknown status values explicitly. Scope: local.
- **Trade-off:** Adds an enum + validator; producer evolution now requires a contract bump.

### [MAJOR] Payment POST has no timeout on the critical path
- **Domain:** Operations (C3)
- **Verified by:** READ — `httpx.Client(base_url=...)` (line 6) sets no timeout; `.post("/charges", ...)` (line 26) passes none, so the charge can block indefinitely.
- **Evidence:** `unchecked_casts.py:6,26` — `PAYMENT_CLIENT: Any = httpx.Client(base_url="https://payments.internal")`; `PAYMENT_CLIENT.post("/charges", json={...})`.
- **Failure scenario:** Gateway stall hangs the worker/thread forever; under load, all workers pile onto a dead downstream with no breaker or deadline.
- **Fix:** Set an explicit connect/read/write timeout plus a retry budget with jitter only with an idempotency key. Scope: module.
- **Trade-off:** Adds timeout tuning and idempotency-key plumbing; overly tight timeouts trade hangs for false failures.

### [MAJOR] Module globals leave no seam at the highest-churn dependencies
- **Domain:** Maintainability (B2)
- **Verified by:** READ — `PAYMENT_CLIENT`, `LEDGER`, `connection` (lines 6-8) are module-level `Any` globals read directly by every function, so tests must stand up the real gateway/DB/ledger.
- **Evidence:** `unchecked_casts.py:6-8` — `PAYMENT_CLIENT: Any = ...`; `LEDGER: Any = None`; `connection: Any = None`.
- **Failure scenario:** Any change to charge/lookup/ledger behaviour can only be verified against live systems; unit verification cost stays permanently high.
- **Fix:** Inject clients/connections via parameters or a narrow interface seam. Scope: module.
- **Trade-off:** Adds constructor/call-site plumbing; every caller passes the dependency explicitly.

## Aligns well
- Parameterised order query (`... WHERE id = ?`, `(order_id,)` at line 16) keeps caller input out of SQL text — no SQL-injection path (S3).
- Each function docstring states the trust assumption plainly, making the unchecked boundaries easy to locate (B4).

Disputed: none.