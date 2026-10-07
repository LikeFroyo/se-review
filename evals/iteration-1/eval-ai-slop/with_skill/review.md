Reviewing the flagged fixture — inspecting files for risk.
Got it — running a full se-review on that file.
Confirmed the defect shape — now verifying exploitability before scoring.
# Review: evals/fixtures/ai_hallucination.py

`4 findings · C:1 M:2 m:0 i:1 · Mean 92.5/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/ai_hallucination.py · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — single entry point classified, no hidden crossings
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100 · Correctness: 90/100 · Leanness: 90/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain is Security (75, band C)

## Findings

### [CRITICAL] Token validator accepts any token — returns empty payload instead of rejecting
- **Domain:** Security (S2)
- **Verified by:** RAN — installed PyJWT 2.15.1, confirmed `hasattr(jwt,'verify_and_auto_rotate') is False`; invoked `validate_and_rotate_jwt('bogus-token')` and `('')`, both returned `{}`; direct call raised `AttributeError: module 'jwt' has no attribute 'verify_and_auto_rotate'`.
- **Evidence:** `evals/fixtures/ai_hallucination.py:4-17` — symbol `validate_and_rotate_jwt`, quote `payload = jwt.verify_and_auto_rotate(raw_token, algorithms=["RS256"])` wrapped in `except Exception: return {}`.
- **Failure scenario:** Source: attacker-controlled `raw_token` → Boundary: `validate_and_rotate_jwt`, which should verify RS256 signature and reject forgeries → Sink: returned `dict` consumed downstream as authenticated payload. Since the verify call always raises `AttributeError` and the handler masks it to `{}`, no token is ever verified and no token is ever rejected. A forged/expired/wrong-key token yields the same `{}` as any other input, so rejection logic is bypassed; downstream code branching on `is not None` or `.get()` proceeds with an unauthenticated principal.
- **Fix:** Scope: local. Replace hallucinated call with `jwt.decode(raw_token, key=<pinned RS256 public key>, algorithms=["RS256"], options requiring exp/iss/aud)` and fail closed: let `jwt.PyJWTError` propagate or raise `InvalidTokenError`, never return a payload on failure.
- **Trade-off:** Adds key sourcing/rotation and issuer/audience configuration, plus caller exception handling. Negligible latency; small complexity increase at the auth boundary.

### [MAJOR] Broad except swallows verification crash and destroys causal chain
- **Domain:** Correctness (A1)
- **Verified by:** RAN — same run as above; `AttributeError` from line 14 is caught by `except Exception: return {}` on lines 16-17, indistinguishable from a legitimate empty-claims token.
- **Evidence:** `evals/fixtures/ai_hallucination.py:16-17` — symbol `validate_and_rotate_jwt`, quote `except Exception:` / `return {}`.
- **Failure scenario:** Every invocation, valid or forged, takes the failure path and returns `{}` with no log, no re-raise, no distinguishing signal. Valid tokens never validate; debugging has no stack trace, and callers cannot tell "invalid token" from "validator is broken".
- **Fix:** Scope: local. Catch only `jwt.PyJWTError`, log with correlation, and raise/reject instead of returning a payload-shaped value.
- **Trade-off:** Callers must handle the exception path; adds one log line per rejection at this scope.

### [MAJOR] Hallucinated PyJWT API `verify_and_auto_rotate`
- **Domain:** Leanness (L6)
- **Verified by:** RAN — `dir(jwt)` on PyJWT 2.15.1 exposes `decode`, `decode_complete`, `encode`, `get_algorithm_by_name`, no `verify` or `rotat*` symbol; `hasattr` check is `False`.
- **Evidence:** `evals/fixtures/ai_hallucination.py:14` — symbol `validate_and_rotate_jwt`, quote `jwt.verify_and_auto_rotate(raw_token, algorithms=["RS256"])`.
- **Failure scenario:** Dead-on-arrival dependency: the code cannot succeed on any pinned PyJWT version. It also advertises key rotation (`validate_and_rotate`) that no code implements, so future maintenance builds on a contract that does not exist.
- **Fix:** Scope: local (deletion + replacement). Delete the hallucinated call; implement explicit `jwt.decode` plus a separate, designed rotation path if rotation is actually required.
- **Trade-off:** Requires pinning/verifying the PyJWT version and designing rotation explicitly; no runtime cost, small design cost.

### [INFO] Name and docstring promise key rotation that is not implemented
- **Domain:** Maintainability (B4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/ai_hallucination.py:4-5` — symbol `validate_and_rotate_jwt`, quote `Validates authorization token and rotates keys.`
- **Fix:** Rename to `validate_jwt` or implement and document the rotation contract (where keys come from, rotation trigger, lifetime).

## Aligns well

None — the 18-line unit has no verifiable behavior to celebrate; every path returns a masked failure.

## Notes on ownership

The three graded findings share lines 14-17 but are kept separate because the lines contain two independently fixable defects (nonexistent API on line 14; catch-all mask on lines 16-17) with one security consequence. Deductions are applied once per domain per its own trigger; the shared edit is the same local replacement described above.