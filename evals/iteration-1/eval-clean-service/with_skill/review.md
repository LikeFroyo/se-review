I'll read that file.
Loading the skill's shared rules and the domain leaves relevant to this file.
# Review: `evals/fixtures/clean_service.py`

`4 findings · C:0 M:0 m:1 i:3 · Mean 99.4/100 · Final Grade A`
Domain Scores: Correctness: 97/100 · Operations: 100/100 · Maintainability: 100/100 · Interoperability: 100/100 · Leanness (gate): 100/100
*(Caps do not bind — no Critical, and the weakest domain, Correctness at 97, is already band A.)*

## Findings

### [MINOR] `max_attempts <= 0` falls off the end and returns `None` from a `-> dict` function
- **Domain:** Correctness (A1)
- **Evidence:** `evals/fixtures/clean_service.py:27,29` — `PaymentVerificationService.execute_with_resilience`, signature `def execute_with_resilience(self, task_func, max_attempts: int = 3, base_delay: float = 0.5) -> dict:` then `for attempt in range(1, max_attempts + 1):`. With `max_attempts` of `0` or negative, `range(1, 1)` is empty, the loop body never executes, no `return` is reached, and the function yields `None` while its annotation promises `dict`. Every other path exits via `return task_func()` or `raise`.
- **Failure scenario:** A caller wiring `max_attempts` from config passes `0`; the call returns `None` and the failure surfaces at the *consumer* as `TypeError: 'NoneType' object is not subscriptable`, a stack pointing away from the bad argument rather than at this boundary.
- **Fix (local):** reject the invalid argument where it enters — `if max_attempts < 1: raise ValueError("max_attempts must be >= 1")` before the loop. Converts a silent contract violation into an immediate, correctly-located error.

### [INFO / SUGGESTION] Retry-exhaustion log drops the exception it just caught
- **Domain:** Operations (C4)
- **Evidence:** `evals/fixtures/clean_service.py:32-35` — `except ConnectionError as exc:` binds `exc`, and the terminal branch logs `logger.warning("Payment verification failed after max retries", extra={"attempts": attempt})` carrying the attempt count but not the cause.
- **Failure scenario:** None — the bare `raise` immediately after propagates the original exception, so the cause is not lost to the caller. The gap is forensic: the last line this service emits before giving up states *that* it failed and *how many times*, but not *why*, and triage reads the log line before it reads the propagated traceback.
- **Fix (local):** include the cause — `extra={"attempts": attempt, "error": str(exc)}` or `logger.warning(..., exc_info=True)`. Zero cost; `exc` is already bound.

### [INFO / SUGGESTION] `execute_with_resilience` states no idempotency precondition
- **Domain:** Correctness (A5/A4 seam)
- **Evidence:** `evals/fixtures/clean_service.py:27-28` — the docstring reads "Executes task with exponential backoff and jitter" and nothing more; `task_func` is opaque to the retry policy.
- **Failure scenario:** The helper sits on a payment service and will eventually wrap mutating work. A retried capture double-charges, and nothing at the boundary rejects it. Raised as Info rather than Major: the defect is not demonstrated here (the call site is out of scope) and the precondition is *absent* rather than *documented-and-unenforced*, which is the Major case in `magic-values-comments.md`. Ruling: absence of a stated precondition is an observation, not a violated invariant.
- **Fix (local):** state it in the docstring — "retries `task_func`, which must be idempotent" — so the next caller reads the condition at the call site.

### [INFO / SUGGESTION] Backoff path has no seam: sleep and RNG are module globals
- **Domain:** Maintainability (B2)
- **Evidence:** `evals/fixtures/clean_service.py:38-39` — `sleep_duration = random.uniform(0, backoff)` then `time.sleep(sleep_duration)`, both reaching the module-global `random` and `time` rather than parameters.
- **Failure scenario:** Neither is a business rule, so the CRITICAL ambient-state trigger does not apply — jitter is the intended behaviour of a retry helper. The cost is testability: verifying the backoff path requires either patching globals or actually waiting (up to `0.5 + 1.0 = 1.5 s` at the defaults), and the duration differs every run, so an assertion on it cannot be exact.
- **Verification limit:** no test file is in scope, so I cannot assert this path *is* untested — only that it is untestable as written. Capped at Info for that reason.
- **Fix (module):** optional `sleep_fn=time.sleep` and `rng=random.uniform` keyword-only parameters defaulting to the real ones. Costs two lines; makes the whole method instant and deterministic under test.

## Aligns well

- **Tenant isolation enforced in the query, not in caller discipline** (A5): `clean_service.py:18-21` scopes the lookup with `WHERE id = ? AND tenant_id = ?`. Because the tenant predicate sits in the `WHERE` clause, a valid-but-foreign `transaction_id` returns `None` rather than another tenant's row — the failure mode is absence, not disclosure, which is the correct shape for a multi-tenant read. Caveat worth stating rather than grading: the *authenticity* of `caller_tenant_id` is the caller's responsibility, since the service receives it as an explicit parameter (the better form — the alternative, an ambient request-scoped tenant, is the anti-pattern in `implicit-state.md`). No caller is in scope to audit.
- **Parameterized query throughout, no f-string or concatenation** (A5): `clean_service.py:18-21` uses bound placeholders with a parameter tuple.
- **Retry is bounded, jittered, and exception-type-narrow** (C3): `clean_service.py:29-39` — full-jitter exponential backoff, `max_attempts` capped at 3, and only `ConnectionError` is retried, so a programming error is never masked by three extra attempts. This is the deliberate inverse of `fixtures/retry.py` (eval 2) and of eval 24's flaky `sleep`.
- **Proven column selection, no `SELECT *`** (A3): `clean_service.py:19` projects exactly `id, amount, status`.
- **Structured logging with no PII** (C4): the single log site uses `extra={...}` on a named logger rather than f-string interpolation, and no credential, card, or customer identifier is written.
- **Interoperability: correctly a non-finding** — `amount` is read from SQLite and returned in-process with no serialisation, no locale-dependent formatting, and no arithmetic, so there is no seam for D1–D4 to disagree across. Scoping note, not a finding.
- **Leanness gate clear** (L1–L4) — two methods, no manifest, no CI, no unreachable branch, no abstraction with a single speculative implementor. Neither method being uncalled elsewhere in the repo is fixture scope, not proof of death.

## Notes on scope

This file is eval 25's clean control (`evals/README.md:33`), whose stated expectation is 0 findings and 100/100. My read lands Grade **A** with one Minor, so it does not match the expectation exactly — flagging that rather than tuning the finding away. Dropped as linter work per the ground rules: the single-space class indentation (line 10), unused `exc` (linter F841), and the unclosed cursor (refcount-collected; `SIM115`). If you want the control to grade a clean 100, the `max_attempts < 1` guard is the one line to add.