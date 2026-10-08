Reviewing the fixture and run directory.
Found the classic string-truthiness traps. Checking the eval setup and skill definition.
Scoping the review across all domains — loading the scoring rules.
I've mapped the defects to the rubric — now verifying each one executes as suspected.
# Review: `evals/fixtures/string_truthiness.py`

`5 findings · C:2 M:1 m:2 i:0 · Mean 89/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/string_truthiness.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry points in scope; `account` dicts are internal call args with no network/auth boundary shown
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 34/100 · Security: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — string-truthiness inversion in `should_rate_limit` (any Critical caps at F; weakest domain Correctness F also binds)

## Findings

### [CRITICAL] `RATE_LIMIT_ENABLED="false"` is truthy — rate limiting stuck on
- **Domain:** Correctness (A1)
- **Verified by:** RAN — imported module with env unset, `RATE_LIMIT_ENABLED='false'` → `should_rate_limit()` returned `True`, expected `False`
- **Evidence:** `string_truthiness.py:5,11-19` — `RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "false")` then `if RATE_LIMIT_ENABLED: return True`. Docstring states production sets `RATE_LIMIT_ENABLED=false` to work around a metrics regression.
- **Failure scenario:** Production sets `false` intending to disable rate limiting; every non-empty string is truthy, so the disable branch never fires. Notifications are throttled when they must not be — the exact inversion the comment warns about.
- **Fix:** Parse explicitly at the boundary, scope local: `RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "false").strip().lower() in ("1","true","yes","on")`, then `return RATE_LIMIT_ENABLED`.
- **Trade-off:** Cost is one normalization helper at module scope; behavior change is intentional — any caller relying on the always-on accident breaks, which is the bug being removed.

### [CRITICAL] `MAINTENANCE_MODE="0"` is truthy — service stuck in maintenance
- **Domain:** Correctness (A1)
- **Verified by:** RAN — default `MAINTENANCE_MODE='0'` → `is_maintenance()` returned `True`, expected `False`
- **Evidence:** `string_truthiness.py:6,22-26` — `MAINTENANCE_MODE = os.environ.get("MAINTENANCE_MODE", "0")` then `if MAINTENANCE_MODE: return True`.
- **Failure scenario:** Default deploy with no env override reports maintenance mode. Any gate on `is_maintenance()` blocks normal traffic on a fresh install.
- **Fix:** Same explicit parse as above, scope local. Fail-closed vs fail-open default must be chosen deliberately, not inherited from string truthiness.
- **Trade-off:** Same as above — one parsing helper; only cost is deciding the correct default (`"0"` suggests intended-default-off, so parsed default must be `False`).

### [MAJOR] Zip code coerced through `int()` — truncation and crash
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `zip_for({"zip":"02139"})` → `'2139'` (expected `'02139'`); `zip_for({})` → `'0'` (expected `'00000'`); `zip_for({"zip":"abc"})` → `ValueError`
- **Evidence:** `string_truthiness.py:38-41` — `zip_code = account.get("zip") or ACCOUNT_ZIP_FALLBACK; return str(int(zip_code))`.
- **Failure scenario:** Every leading-zero ZIP (all of New England, NJ, PR, military `09xxx`) is silently rewritten to a different/longer-invalid ZIP (`02139` → `2139`); fallback `00000` becomes `0`; any alphanumeric input crashes the notification path instead of rejecting the record.
- **Fix:** Keep ZIPs as strings, scope module: validate `^\d{5}(-\d{4})?$`, preserve leading zeros, reject non-numeric with a typed error instead of `int()` coercion.
- **Trade-off:** Adds a validation branch and an error path callers must handle; avoids silent misdelivery at the cost ofsurfacing bad data that currently crashes or corrupts.

### [MINOR] Empty string conflated with absent in `recipient_for`
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `recipient_for({"email":"","phone":"x"})` → `'x'`; supplied-but-empty email silently falls through to phone/default
- **Evidence:** `string_truthiness.py:29-35` — `if account.get("email"): return ...; if account.get("phone"): return ...`.
- **Fix:** Distinguish absent (`is None` / key missing) from empty: check `if account.get("email") is not None` and validate, or reject `""` explicitly.

### [MINOR] Unknown `status` silently falls through to `bronze`
- **Domain:** Correctness (A1)
- **Verified by:** RAN — `tier_for({"status":"Gold"})` → `'bronze'` instead of rejection
- **Evidence:** `string_truthiness.py:44-51` — `status = account["status"]`; only `"gold"`/`"silver"` matched; everything else returns `"bronze"`, including typos, wrong case, and empty strings.
- **Fix:** Reject unrecognized values (`raise ValueError` / return explicit `unknown`) instead of defaulting to a paying tier.

## Aligns well
- Small single-purpose resolvers with docstrings; failure surface is narrow and testable (A1)
- No trust-boundary crossings, secrets, or concurrency in scope — nothing to grade for S2/S3/S4, A2 (no code)