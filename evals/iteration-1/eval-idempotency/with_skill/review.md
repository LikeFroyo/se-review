Reviewing your non-idempotent payment fixture.
Confirmed the double-charge risk — now scoping the full review.
I've mapped the defect to the relevant domains — now checking the specific guidelines to finalize severity.
# Review: `evals/fixtures/non_idempotent_payment.py`

`2 findings · C:1 M:0 m:1 i:0 · Mean 95.3/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/non_idempotent_payment.py` · Not examined: 0 — none
Paths: 0 open · Unmapped: 0 — no untrusted entry point in scope; `process_charge` is an internal caller, `processor.post` is a downstream sink
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 100/100 · Security: 100/100 · Correctness: 100/100 · Operations: 72/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F

Mode: serial (1 file, 21 lines; below 30-file / 5,000-line fan-out ceiling).

## Findings

### [CRITICAL] Retry / redelivery double-charges customer — no Idempotency-Key
- **Domain:** Operations (C3)
- **Verified by:** DERIVED — trace: timeout between client and `/v1/charges` or webhook redelivery → caller retries `process_charge` → second `processor.post` with identical `account, amount` and no dedup check → processor creates second charge.
- **Evidence:** `non_idempotent_payment.py:8-20` — `def process_charge(self, account_id: str, amount_cents: int)` builds a fresh `self.processor.post("/v1/charges", {"account": ..., "amount": ..., "currency": "usd"})` with no key parameter, header, or dedup-table lookup. The file's own docstring admits it. `import uuid` at line 2 is unused — the key material was intended but never wired.
- **Failure scenario:** Network timeout after the processor commits the charge but before the response returns. Caller retries; customer is charged 2× `amount_cents`. Same on at-least-once webhook redelivery. Money movement duplicated with no conflicting-payload guard; reconciliation sees two live charges.
- **Fix:** Boundary scope — accept `idempotency_key: str` (caller-supplied, or deterministic per business operation using the already-imported `uuid`), transmit as `Idempotency-Key` header / payload field, persist key→result with 24–48h TTL, return prior result on same-key replay and 409/422 on same-key conflicting payload. Cross-references Correctness (A4); no separate Correctness deduction per single-root-cause rule.
- **Trade-off:** Adds key generation/propagation, a dedup store with TTL GC, and replay-vs-conflict logic. Cost at boundary: one store lookup per charge plus storage/ops for the key window; complexity in key lifetime and conflict handling.

### [MINOR] No explicit timeout / deadline on charge POST
- **Domain:** Operations (C3)
- **Verified by:** READ
- **Evidence:** `non_idempotent_payment.py:16-20` — `self.processor.post(...)` passes no `timeout`, deadline, or breaker context. Processor defaults unverified.
- **Fix:** Local scope — pass explicit `timeout=` and propagate caller deadline; let timeouts feed the breaker counted above.

## Aligns well
- Money passed as `amount_cents: int` with `"currency": "usd"`, not float money (D3).
- Narrow single-purpose gateway method; no dead code, no speculative surface (L1–L4 clean).
- No attacker-controlled source→boundary→sink demonstrated in scope; no security path graded.