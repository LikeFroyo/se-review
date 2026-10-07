Reviewing the dead-code fixture and run directory.
Found the legacy adapter — now mapping the eval context.
Proof procedure requires a repo-wide caller check — running that now.
# Review: `evals/fixtures/dead_code.py`

`1 findings · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/dead_code.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust-boundary crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 75/100 · Correctness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain Leanness (C) would otherwise gate at C.

## Findings

### [CRITICAL] Retired `LegacyPriceAdapter` orphaned after v2 cutover
- **Domain:** Leanness (L1)
- **Verified by:** DERIVED — repo-wide text search + dynamic-dispatch / public-API checks, chain below.
- **Evidence:** `evals/fixtures/dead_code.py:7` — `class LegacyPriceAdapter:` with docstring `evals/fixtures/dead_code.py:8` `Superseded by AuroraPricing in the v2 cutover.` Only live entry `price_order` at `evals/fixtures/dead_code.py:26` constructs `AuroraPricing(table).price(order)` at `evals/fixtures/dead_code.py:28`. Supporting dead weight at `evals/fixtures/dead_code.py:14` — `# return self.apply_legacy_discount(order)  # old path, kept for reference`.
- **Proof of death:**
  1. Repository text search for `LegacyPriceAdapter` over `se-run-eval-dead-code-with_skill-r1-997f0b/` returns 1 match — the definition itself, zero callers.
  2. Dynamic dispatch: no `getattr`/`importlib`/DI-registry/plugin-manifest string reference; companion search for `AuroraPricing|price_order|apply_legacy_discount` finds only in-file definitions/uses.
  3. External public API: fixture under `evals/fixtures/`, not an exported library or versioned interface — Info-escalation does not apply.
  4. Live-reference check: sole match is the definition, not a caller; no backup/scratch caller to honor.
- **Failure scenario:** Permanent carrying cost — every reader, migration, and test sweep pays for two pricing paths where one is authoritative; identical bodies (`rate_table.lookup(order.sku) * order.qty` at `:15` vs `:23`) create L4 divergence risk if a future fix touches only `AuroraPricing`.
- **Fix:** Delete `LegacyPriceAdapter` (`:7-:15`), module scope. No behavior change; `AuroraPricing` + `price_order` unchanged.

## Aligns well
- `AuroraPricing` (L4): single authoritative pricing path — keep as-is.
- Correctness (A1), Security (S1), Operations (C1-C8), Interoperability: no logic error, no Source→Boundary→Sink path, no hot loop / retry / crossing defect in scope.