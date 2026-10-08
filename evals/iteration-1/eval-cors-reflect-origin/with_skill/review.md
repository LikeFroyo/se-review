Reviewing target fixture and run bundle.
Found the reflected-origin flaw — now mapping the full evaluation context.
Scope confirmed to a single fixture — now loading the review domains and scoring rules.
The flaw matches the cross-origin trust guideline — now verifying it with a quick reproduction.
# Review: `evals/fixtures/cors_reflect_origin.py`

`1 findings · C:1 M:0 m:0 i:1 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/cors_reflect_origin.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100 · Correctness: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F

## Findings

### [CRITICAL] Reflected request Origin with Allow-Credentials true
- **Domain:** Security (S3)
- **Verified by:** RAN — imported fixture and called `build_cors_headers('https://evil.attacker.test')` → returned `Allow-Origin: https://evil.attacker.test` with `Allow-Credentials: true`; called with `None` → `Allow-Origin: *` with `Allow-Credentials: true`
- **Evidence:** `cors_reflect_origin.py:17-18` — `build_cors_headers`, quote:
  `"Access-Control-Allow-Origin": request_origin or "*", "Access-Control-Allow-Credentials": "true",`
  `ALLOWED_ORIGINS` (`cors_reflect_origin.py:4`) and `origin_is_known()` (`cors_reflect_origin.py:25-26`) exist but are never consulted by the builder.
- **Failure scenario:** Source: attacker-controlled `Origin` request header → Boundary: CORS check that should validate against `ALLOWED_ORIGINS` but echoes instead → Sink: `Access-Control-Allow-Origin` + `Allow-Credentials: true` on a session-cookie-authenticated JSON API. Victim visits attacker page; attacker page issues credentialed `fetch`, browser attaches session cookie, response is readable cross-origin → session data exfiltration. Single root cause covers both the arbitrary-origin echo and the `None → *` + credentials combination.
- **Fix:** Validate before emitting, scope: local. Echo only when `origin_is_known(request_origin)`; otherwise omit both `Allow-Origin` and `Allow-Credentials` (or return no CORS headers). Never emit `*` alongside `Allow-Credentials: true`.
- **Trade-off:** Cost is one set-membership check per request (negligible latency/memory); strictness breaks any currently-relying non-allowlisted origin, which is the intended revocation.

### [INFO / SUGGESTION] Allowlist helper is defined but unwired
- **Domain:** Maintainability (B5)
- **Verified by:** READ
- **Evidence:** `cors_reflect_origin.py:4,25-26` — `ALLOWED_ORIGINS = {"https://app.acme.example"}` and `origin_is_known()` have no callers in this file.
- **Fix:** Wire `origin_is_known()` into `build_cors_headers()` per the Critical fix above rather than deleting it; it is the intended contract.

## Aligns well
- Fixture documents the vulnerability explicitly in the docstring (`cors_reflect_origin.py:10-15`) instead of leaving intent ambiguous.
- Centralized single builder for CORS headers (rather than per-route inline header construction), so the fix has one site.