Reviewing the fixture inside its self-contained workspace.
Found the pickle injection — now loading the security criteria to grade it.
The vulnerability path is clear — now verifying exploitability to lock in the severity.
# Review: `evals/fixtures/unsafe_deserialization.py` — `restore_cache_entry`

`1 findings · C:1 M:0 m:0 i:0 · Mean 75/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/unsafe_deserialization.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — no other crossings in 22-line fixture
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100
Gated by: `Critical finding` — any Critical caps grade at F

## Findings

### [CRITICAL] Arbitrary code execution via `pickle.loads` on client-supplied blob
- **Domain:** Security (S3)
- **Verified by:** `RAN` — crafted `pickle.dumps` object with hostile `__reduce__` executed via `restore_cache_entry(blob)` in this workspace; `print` hook fired before return.
- **Evidence:** `evals/fixtures/unsafe_deserialization.py:8-17` — function `restore_cache_entry`:
  > `"""Cache service that restores entries from a client-supplied blob."""`
  > `def restore_cache_entry(blob: bytes) -> Any:`
  > `return pickle.loads(blob)`
  Docstring lines 9-15 explicitly states posted bytes go straight to `pickle.loads` invoking `__reduce__/__setstate__` as service account.
- **Source → Boundary → Sink:** Source: `blob: bytes` client-supplied posted payload → Boundary: none, no validation, allowlist, signature, or type check before line 17 → Sink: `pickle.loads(blob)` object reconstruction with code execution.
- **Failure scenario:** Attacker POSTs crafted pickle gadget chain; server unpickles on receipt and runs attacker code as service account — RCE, data theft, persistence — before any application logic. Matches `domains/security/injection-interpretation/guidelines/unsafe-parsing.md` § Deserialization: `pickle.loads` on request-derived value.
- **Fix:** Replace wire format with data-only parser — e.g. `json.loads(blob)` + schema validation. Reject unparseable input. If binary/typed objects required, use explicit allowlist decoder, never `pickle`. Scope: boundary — client/server serialization contract changes, callers must re-encode.
- **Trade-off:** Adds schema-maintenance complexity and rejects arbitrary Python objects (functionality loss by design); JSON decode latency comparable, payload size slightly larger. Eliminates entire gadget class.

## Aligns well
- None — documented vulnerability does not mitigate it per `Documented is not resolved`.

## Cut policy
Cut by 15-cap: 0 findings (C:0 M:0 m:0 i:0).