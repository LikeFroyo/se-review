Reviewing the breaking schema fixture — reading the file and run directory.
Found the breaking contract fixture — now gathering review context.
This is a se-review request — loading scoring rules and discovering domains.
The defect maps to API contracts and wire formats — checking those guidelines.
Confirmed the breaking changes map to the guidelines — now verifying remaining domains for full coverage.
# Review: `evals/fixtures/breaking_schema.py`

`3 findings · C:1 M:0 m:1 i:1 · Mean 95/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/breaking_schema.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 100/100 · Security: 100/100 · Correctness: 72/100 · Maintainability: 100/100 · Interoperability: 100/100 · Operations: 100/100
Gated by: `Critical finding` — **always printed.**

Serial mode: 1 file in scope, cross-file fan-out not triggered.

## Findings

### [CRITICAL] Unversioned breaking serializer: field rename + type mutation
- **Domain:** Correctness (A4)
- **Verified by:** DERIVED — trace: `serialize_customer_v1()` return dict `evals/fixtures/breaking_schema.py:11-15` → public API consumers / SDKs parsing `customer_id: int`
- **Evidence:** `evals/fixtures/breaking_schema.py:11-13` in `serialize_customer_v1` — quote offending lines:
```python
"id": customer_record["customer_id"],     # Breaking rename from customer_id
"tier_code": str(customer_record["tier"]), # Breaking type mutation from int to str
```
Docstring `breaking_schema.py:6-9` admits both breaks with no deprecation window or alias.
- **Failure scenario:** Existing client on `v1` does `payload["customer_id"]` → `KeyError`; typed SDK expecting `tier_code: int` receives `"1"` / `"GOLD"` string → parse crash / validation reject on rollout. Unversioned endpoint, no dual-read, total consumer outage.
- **Fix:** Boundary scope. Keep `customer_id` and int `tier_code` on `v1`; ship new shape as `v2` or additive: emit both `customer_id` and `id`, accept both on read, emit int + string enum during window with `Sunset` header, then remove old.
- **Trade-off:** Boundary version/alias adds mapping code and dual-field payload size; cost is temporary compat shim vs fleet-wide client break.

Cross-ref: Interoperability (D4) — same shape break at wire, owner stands here per `wire-formats/sub-leaf.md` scope boundary, no separate deduction.

### [MINOR] Unvalidated direct dict access raises KeyError
- **Domain:** Correctness (A8)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/breaking_schema.py:12-14` in `serialize_customer_v1` — `customer_record["customer_id"]`, `customer_record["tier"]`, `customer_record["email"]` with no presence/type check.
- **Fix:** Local scope. Validate required keys and types at boundary; raise explicit `ValueError` / 4xx or return typed DTO instead of bare `KeyError` → 500.

### [INFO / SUGGESTION] Adopt additive-only evolution with unknown-field tolerance
- **Domain:** Interoperability (D4)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/breaking_schema.py:11-15` — `serialize_customer_v1` rewrites wire shape in place, no version field checked.
- **Fix:** Recommendation: pin schema version in payload, validate on write and read, require consumers tolerate unknown fields so additive changes stay safe.

## Aligns well
- Small pure serializer with explicit docstring admitting break (A6) — intent is discoverable, not silent.
- No dead code, no supply-chain surface, no attacker path (L5, S1) in 15-line scope.