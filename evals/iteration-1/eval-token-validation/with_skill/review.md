Reviewing your token validation fixture and run directory.
Found the unverified JWT decode — now gathering surrounding eval context.
This is a focused security fixture — I'll run a targeted review against the rubric.
I've mapped the flaws to the rubric — now verifying exploitability.
# Review: `evals/fixtures/token_validation.py`

`4 findings · C:1 M:2 m:1 i:0 · Mean 92/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/token_validation.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 65/100 · Correctness: 87/100 · Leanness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F

## Findings

### [CRITICAL] JWT accepted without signature, audience, or expiry check
- **Domain:** Security (S2)
- **Verified by:** RAN — forged HS256 token with `attacker-key` accepted as `admin`; expired + wrong-`aud` token accepted
- **Evidence:** `evals/fixtures/token_validation.py:24-26` — `AuthGateway.authenticate`: `claims = jwt.decode(token, JWT_SECRET, options={"verify_signature": False})`
- **Failure scenario:** Source: attacker-crafted `Authorization: Bearer` header → Boundary: `authenticate()` crossing that should verify signature/`exp`/`aud` → Sink: returned `{"user_id","role"}` trusted as identity; attacker mints `{"sub":"attacker","role":"admin"}` and passes `is_permitted()` for `delete_workspace`/`billing_refund`.
- **Fix:** Verify signature, expiry, audience: `jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="expected-aud", options={"require":["exp","aud","sub"]})`, scope: local.
- **Trade-off:** Adds key-management and clock-skew handling; rejects expired/mis-audience tokens by design.

### [MAJOR] Hardcoded HMAC signing key in source
- **Domain:** Security (S4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/token_validation.py:9` — `AuthGateway`: `JWT_SECRET = "svc-signing-key-do-not-share"`
- **Failure scenario:** Key leaks via repo clone; once signature verification is enabled, anyone with read access can mint valid `admin` tokens.
- **Fix:** Load from secret manager/env, rotate, never commit; scope: boundary.
- **Trade-off:** Adds deployment/rotation complexity and requires secret-injection plumbing.

### [MAJOR] `is_permitted` uses role equality, locking out admin/editor from viewer actions
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `is_permitted({role:admin}, read_docs)=False`; `is_permitted({role:editor}, read_docs)=False`
- **Evidence:** `evals/fixtures/token_validation.py:28-31` — `AuthGateway.is_permitted`: `required = "admin" if ... else "viewer"; return ... principal["role"] == required`
- **Failure scenario:** Privileged users denied all baseline reads; no role hierarchy, no `editor` handling.
- **Fix:** Rank check e.g. `{"viewer":0,"editor":1,"admin":2}[principal["role"]] >= rank[required]`; scope: local.
- **Trade-off:** Adds one mapping table; must decide where `editor` sits per action.

### [MINOR] Unhandled malformed/missing-claim tokens raise instead of rejecting
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `Bearer not-a-jwt`, `Bearer `, `no-prefix` all raise `DecodeError`; missing `sub` raises `KeyError`
- **Evidence:** `evals/fixtures/token_validation.py:24-26`
- **Fix:** Catch `jwt.PyJWTError`/`KeyError` and raise domain `AuthenticationError`/return deny.

## Aligns well
- Fixture docstring accurately labels the bypass and unchecked `aud`/`exp` (A6).
- Narrow `ALLOWED_ROLES` tuple and typed `authenticate() -> Dict` signature (B4).