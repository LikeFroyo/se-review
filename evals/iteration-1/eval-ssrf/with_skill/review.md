Reviewing your SSRF webhook fixture — reading the script and run directory.
Found the SSRF sink — now gathering eval context to complete the review.
Small single-file scope — running a full multi-domain review serially.
# Review: `evals/fixtures/ssrf_webhook.py`

`3 findings · C:1 M:1 m:1 i:0 · Mean 94/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/ssrf_webhook.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — no unclassified crossings
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100 · Correctness: 97/100 · Operations: 90/100 · Maintainability: 100/100 · Leanness: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — **always printed.**

Serial review. No fan-out (1 file, 21 lines).

## Findings

### [CRITICAL] Unvalidated webhook URL enables SSRF and forwards bearer token to attacker
- **Domain:** Security (S1)
- **Verified by:** DERIVED — `dispatch_event(webhook_url)` at `ssrf_webhook.py:8` flows unsanitized to `requests.post(webhook_url, ...)` at `ssrf_webhook.py:16-20` with `Authorization: Bearer <auth_token>` attached.
- **Evidence:** `ssrf_webhook.py:8-20` — class `WebhookService.dispatch_event`:
```python
def dispatch_event(self, webhook_url: str, payload: dict) -> dict:
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Authorization": f"Bearer {self.auth_token}"}
    )
```
No scheme check, no allowlist, no DNS/IP resolution guard, no private-link/metadata-IP block.
- **Path:** Source: `webhook_url: str` attacker-controlled → Boundary: none (no validation at trust crossing) → Sink: `requests.post()` server-side fetch + secret-bearing header.
- **Failure scenario:** Attacker registers `http://169.254.169.254/latest/meta-data/iam/security-credentials/` or `http://10.0.0.1:8080/admin` as webhook URL. Server fetches it, returning cloud IAM credentials/internal admin response in `response.text`, and simultaneously leaks the service `auth_token` to the attacker host via the `Authorization` header. The inline comment at `ssrf_webhook.py:11-14` documents this as known-vulnerable.
- **Fix:** Validate before fetch, scope: boundary. Enforce `https` only, DNS-resolve and reject private/loopback/link-local/multicast/reserved ranges (with TOCTOU-safe connect guard or egress proxy), enforce customer allowlist, and never send `Authorization` to a non-allowlisted host (strip or per-host credentials).
- **Trade-off:** Adds DNS-resolution + IP-check latency per dispatch (one lookup, microsecond IP-range check) and complexity of maintaining allowlist/egress policy; per-host credential mapping adds module-level config surface.

### [MAJOR] No timeout on outbound webhook POST allows hung worker
- **Domain:** Operations (C3)
- **Verified by:** READ
- **Evidence:** `ssrf_webhook.py:16-20` — `requests.post(webhook_url, json=payload, headers=...)` with no `timeout=` argument in `WebhookService.dispatch_event`.
- **Failure scenario:** Slow or non-responsive customer endpoint (or attacker-controlled SSRF target that tarpits) blocks the calling thread indefinitely, exhausting workers/threads under load and causing cascading dispatch backlog.
- **Fix:** Add explicit `timeout=(connect, read)` e.g. `(3, 10)`, scope: local. Add bounded retry with backoff/jitter at caller if at-least-once delivery is required.
- **Trade-off:** Timeouts add spurious-failure rate on tail-latency endpoints; must tune values and add retry budget to avoid turning slowness into loss.

### [MINOR] Unhandled transport errors propagate as uncaught exceptions
- **Domain:** Correctness (A1)
- **Verified by:** READ
- **Evidence:** `ssrf_webhook.py:16-21` — `requests.post(...)` return of `response.status_code/text` with no `try/except requests.RequestException` and no status handling in `dispatch_event`.
- **Fix:** Catch `requests.RequestException`, return typed error result or raise domain exception; decide non-2xx policy explicitly.

## Aligns well
- Minimal, single-purpose dispatcher — no dead code, no speculative generality (L1-L4 clean).
- Low cyclomatic/cognitive complexity, clear naming, stateless dispatch apart from token holder (B1 clean).
- `json=payload` preserves encoding across the wire boundary; no manual serialization/money/time conversion (D4 clean).