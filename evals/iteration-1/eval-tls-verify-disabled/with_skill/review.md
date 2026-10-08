Reviewing the file and run directory now.
Found the TLS flaw — no verification on either request. I'm gathering the surrounding context to complete the security review.
I've confirmed this is a critical S4 vulnerability. Now I'll verify the other domains to finalize the scores.
# Review: `evals/fixtures/tls_verify_disabled.py`

`2 findings · C:1 M:1 m:0 i:0 · Mean 94/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/tls_verify_disabled.py` · Not examined: 0 — none
Paths: 1 resolved open · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100 · Operations: 90/100 · Correctness: 100/100 · Maintainability: 100/100 · Interoperability: 100/100 · Leanness: 100/100
Gated by: `Critical finding` — serial mode (1 file, below fan-out ceiling)

## Findings

### [CRITICAL] TLS certificate validation disabled on partner billing API
- **Domain:** Security (S4)
- **Verified by:** DERIVED — `LedgerClient.__init__` stores `api_key` → `post_charge`/`get_invoice` attach it as `Authorization: Bearer` header → `requests.post/get(..., verify=False)` skips chain validation → attacker on network path presents self-signed cert, reads key and forges responses.
- **Evidence:** `tls_verify_disabled.py:21-26` — `response = requests.post(f"{PARTNER_API}/charges", json=charge, headers={"Authorization": f"Bearer {self.api_key}"}, verify=False)`; repeat at `tls_verify_disabled.py:30-34` (`requests.get`, same `verify=False`). One root cause, two sites.
- **Failure scenario:** Source: network-path attacker (public Wi-Fi, compromised proxy, DNS hijack) → Boundary: TLS hostname/chain check that should reject the forged cert (disabled) → Sink: `Authorization` header carrying the live billing API key plus charge/invoice bodies, and the trusted `response.status_code/text` return. Attacker captures the key and can serve a forged "charge accepted" body that the caller treats as authoritative.
- **Fix:** Delete `verify=False` on both calls (restores default `True`); if the partner uses a private CA, pass `verify=<ca-bundle-path>` instead. Scope: local.
- **Trade-off:** Re-enabling validation costs one failure mode: endpoints with self-signed/expired/privately-rooted certs will now fail closed until the correct CA bundle is provisioned. No latency or complexity cost.

### [MAJOR] Outbound partner calls have no timeout
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — `post_charge` and `get_invoice` issue blocking `requests.post/get` with no `timeout=` → a stalled `billing.partner.example.com` holds the calling thread indefinitely.
- **Evidence:** `tls_verify_disabled.py:21-26`, `tls_verify_disabled.py:30-34` — neither call passes `timeout`.
- **Failure scenario:** Partner slowness or a hung connection exhausts worker threads / request deadlines; billing path stalls with no fail-fast, cascading into caller queue backup.
- **Fix:** Add an explicit timeout, e.g. `timeout=(3.05, 10)`, and handle `requests.Timeout` at the caller. Scope: local (both call sites).
- **Trade-off:** Slow-but-valid partner responses now raise instead of hanging; the caller must implement retry/timeout handling (for non-idempotent `post_charge`, only retry with an idempotency key).

## Aligns well
- Minimal, single-purpose client with caller-supplied credentials (no hardcoded secret); auth header construction is correct per call.