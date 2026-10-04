I'll read the file first.
# Security Review: `evals/fixtures/cors_reflect_origin.py`

`1 finding · C:0 M:1 m:0 i:0 · Domain Score: 90/100 (Grade A)`

## Findings

### [MAJOR] Credentialed CORS reflects the request Origin, so every origin is trusted
- **Domain:** Correctness / Security (A5) — `guidelines/cross-origin-trust.md` § Reflected origin with credentials (OWASP A05, CWE-352)
- **Evidence:** `evals/fixtures/cors_reflect_origin.py:18-19` — `build_cors_headers` returns `"Access-Control-Allow-Origin": request_origin or "*"` immediately beside `"Access-Control-Allow-Credentials": "true"`. The pairing is what makes it exploitable: a bare `*` is rejected by browsers on credentialed requests, so the `or "*"` branch is not the safe fallback it looks like — the reflection branch is the one that runs.
- **Failure scenario:** The file already defines the correct policy (`ALLOWED_ORIGINS`, `origin_is_known`) but `build_cors_headers` never consults it. A victim with a live session visits `https://attacker.test`; that page issues `fetch("https://api.acme.example/me", {credentials: "include"})`. The browser attaches the session cookie and the response carries the attacker's own origin in `Access-Control-Allow-Origin`, so `response.json()` succeeds — the attacker reads the victim's authenticated data cross-origin. This applies to every endpoint the API exposes, not one route.
- **Fix:** Echo an origin only on exact set membership — `if origin_is_known(request_origin): headers["Access-Control-Allow-Origin"] = request_origin` — and omit `Access-Control-Allow-Origin` entirely otherwise (returning no CORS headers beats a wrong one; do not fall back to `*`, which is rejected on credentialed requests and would silently disable the policy for legitimate callers). Pair with `SameSite=Lax|Strict` cookies and a CSRF token on cookie-authenticated writes, since CORS does not block a cross-origin *write*, only cross-origin *reads*. Scope: **local** — the one function, plus the cookie/CSRF attributes at the response boundary.
- **Trade-off:** An exact-match set lookup per request is an O(1) hash hit on a module-level constant (nanoseconds, no I/O); the real cost is operational — every new frontend origin now requires an allowlist edit and a deploy, so keep `ALLOWED_ORIGINS` config-driven rather than a literal, and expect origin additions to become a release step.

## Aligns well
- `ALLOWED_ORIGINS` as an exact-match set, with `origin_is_known` doing plain membership (`cors_reflect_origin.py:25-26`) — the correct predicate, and notably exact-match rather than a prefix or suffix matcher, so a lookalike host like `evil-app.acme.example` cannot pass. The defect is that the caller skips it, not that the policy is wrong (A5).