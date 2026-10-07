Reviewing the dead-code fixture and run bundle.
Found the fixture — now gathering run context for a grounded review.
Scope mapped — now loading the leanness rubric and verifying callers.
Death proof is complete — now checking the remaining domains before scoring.
# Review: evals/fixtures/dead_code.py

`1 findings · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/dead_code.py · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no entry points or trust crossings in this 28-line fixture
Unclassified: 0 findings fit no axis code
Domain Scores: Leanness: 75/100 · Correctness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — retired V1 adapter with zero live callers caps the grade at F

## Findings

### [CRITICAL] Retired V1 pricing adapter retained alongside live path
- **Domain:** Leanness (L1)
- **Verified by:** DERIVED — repo-wide text search for `LegacyPriceAdapter|apply_legacy_discount|AuroraPricing|price_order|RateTable` across all tracked files returned hits only in `evals/fixtures/dead_code.py`; dynamic-dispatch check for `getattr|importlib|entry_points` found no string-keyed registration; no `pyproject.toml`/`package.json`/manifest declares it as a plugin entry point
- **Evidence:** `evals/fixtures/dead_code.py:7-15` — orphaned symbol plus commented-out code in one root cause:
```python
class LegacyPriceAdapter:
    """V1 pricing adapter. Superseded by AuroraPricing in the v2 cutover."""
    def __init__(self, rate_table):
        self.rate_table = rate_table
    def price(self, order):
        # return self.apply_legacy_discount(order)  # old path, kept for reference
        return self.rate_table.lookup(order.sku) * order.qty
```
Live path is `evals/fixtures/dead_code.py:18-28`: `AuroraPricing` is instantiated once in `price_order()`; `LegacyPriceAdapter` is never instantiated, imported, or referenced by string name. Docstring at `:8` confirms retirement, not dual-live intent. Not an external public API (eval fixture, no `__all__`/versioned export) and not a recovery/rollback path, so Info cap does not apply.
- **Failure scenario:** Permanent carrying cost. Every rate-table migration, pricing change, and new-reader onboarding must reason about two identical `rate_table.lookup(order.sku) * order.qty` implementations and a commented-out `apply_legacy_discount` path that can never execute. The L4 duplication (`:15` vs `:23`) is a consequence of this root cause and is removed by the same deletion — no separate deduction.
- **Fix:** Delete `LegacyPriceAdapter` (`:7-15`) including the commented-out `:14` line. Scope: module.

## Aligns well
- Live pricing is a single authoritative path — `price_order()` → `AuroraPricing(table).price(order)` (L4).
- No security path to grade: no untrusted source, boundary, or sink in scope; `order.sku/qty` have no demonstrated attacker entry (S1).
- No correctness/operations/interoperability defect demonstrated: straight-line multiply with no shared state, no loop/allocation pressure, and no cross-boundary encoding/time/numeric conversion in evidence; `datetime.now().date()` ceil-floor at midnight is not graded without a demonstrated timezone consumer on the other side.