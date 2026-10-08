Reviewing your fixture — inspecting code and run artifacts.
Found a live secret leaking into errors — gathering full context for the review.
Scope is a single focused file — loading the review domains to score it.
# Review: `evals/fixtures/credential_in_error.py`

`3 findings · C:1 M:1 m:1 i:0 · Mean 93/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/credential_in_error.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100 · Correctness: 97/100 · Interoperability: 90/100 · Operations: 100/100 · Maintainability: 100/100 · Leanness: 100/100
Gated by: `Critical finding` — **always printed.**

## Findings

### [CRITICAL] Live client secret interpolated into exception message
- **Domain:** Security (S4)
- **Verified by:** DERIVED — `CLIENT_SECRET` definition → `fetch_token` `except HTTPError` f-string → `RuntimeError` escaping to caller/log aggregator.
- **Evidence:** `evals/fixtures/credential_in_error.py:9,28-30` — quote:
  ```python
  CLIENT_SECRET = "sk_live_51H8xQ2eZvKYlo2C"
  raise RuntimeError(
      f"token request failed for {username} with secret {CLIENT_SECRET}: {detail}"
  ) from exc
  ```
  Same material is also hardcoded in source at `:9` and sent as `X-Client-Secret` header at `:19`, so rotation requires a release.
- **Failure scenario:** Upstream auth returns 4xx/5xx → `fetch_token` raises with secret in message. Uncaught exception is captured by error tracking / stderr / caller logs with wider readership than the secret store. Any log reader or error-dashboard viewer recovers `sk_live_*` verbatim. Compromise is permanent until code release rotates it. Source → Boundary → Sink: `Source: CLIENT_SECRET + username (caller-supplied, logged back)` → `Boundary: exception / process log boundary that should redact secrets` → `Sink: RuntimeError text persisted in logs / error aggregator`.
- **Fix:** Strip secret (and preferably `username`) from error; load secret from environment / secret manager, never hardcode. Scope: module (`fetch_token` + module constant → env lookup + redacted error type).
  ```python
  CLIENT_SECRET = os.environ["AUTH_CLIENT_SECRET"]
  raise RuntimeError(f"token request failed for {username}: {detail}") from exc
  ```
  Better: raise typed `AuthError(status, detail)` without secret.
- **Trade-off:** Cost is config plumbing (env/secret-manager wiring + deploy change) at module scope; no latency/memory cost. Benefit is log-safety and rotatability.

### [MAJOR] Form body built by f-string without percent-encoding
- **Domain:** Interoperability (D4)
- **Verified by:** DERIVED — `fetch_token(username, password)` → `body = f"...{username}...{password}"` → `urlopen(Request(..., data=body.encode()))` → `auth.internal` form parser splitting on `&`/`=`.
- **Evidence:** `evals/fixtures/credential_in_error.py:13,14-21` — quote:
  ```python
  body = f"grant_type=password&username={username}&password={password}"
  ```
  with `Content-Type: application/x-www-form-urlencoded`. Client side does no `urlencode`; server side must `split` on delimiters per form spec — the two sides disagree when credentials contain `&`, `=`, `+`, `%`, or non-ASCII.
- **Failure scenario:** Password `p@ss&foo=bar` or username with `+`/`%` corrupts fields: server sees extra field / truncated password → spurious auth failure, or wrong-user binding. Observable in production on first special-character credential; not covered by happy-path test.
- **Fix:** Use `urllib.parse.urlencode`. Scope: local (body construction lines).
  ```python
  from urllib.parse import urlencode
  body = urlencode({"grant_type": "password", "username": username, "password": password})
  ```
- **Trade-off:** One stdlib call at local scope; negligible latency, removes delimiter-escaping class entirely.

### [MINOR] HTTP status discarded behind generic RuntimeError
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — `except HTTPError as exc` → `detail = exc.read().decode(...)` → `raise RuntimeError(...)` drops `exc.code`/`exc.status`.
- **Evidence:** `evals/fixtures/credential_in_error.py:26-30`
- **Fix:** Raise typed error preserving `exc.code` and `detail`, or attach `status` attribute.

## Aligns well
- Correct `raise ... from exc` chaining preserves traceback (A1).
- Explicit `timeout=10` on `urlopen` avoids unbounded hang (C3).
- No dead code / unused surface in 30-line module (L1).

`Cut by 15-cap: 0 findings (C:0 M:0 m:0 i:0) on axes none.`