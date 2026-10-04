Reviewing your fixture and constraints.
Found a legacy path bypassing the single sizing rule — checking the full scope.
I've mapped the violation — now loading the scoring rules to finalize the review.
Execution confirms the sign error — now determining the final severity.
# Review: suppression_ledger_unprovable_site.py with SIZING_CONSTRAINTS.md

`1 findings · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/suppression_ledger_unprovable_site.py + suppression_ledger_unprovable_site_CONSTRAINTS.md · Not examined: 0 — none
Paths: 0 open · Unmapped: 0 — no trust-boundary crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100 · Maintainability: 100/100 · Security: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — always printed.

## Findings

### [CRITICAL] Second sizing implementation via `HANDLERS["legacy"]` violates C1 single-implementation rule and inverts SELL sign
- **Domain:** Correctness (A1). Cross-refs Leanness (L4 redundancy / stale shim) — no separate deduction per dedup owner rule.
- **Verified by:** `RAN` — imported fixture and executed both paths:
  - `size_order({"side":"BUY","quantity":10})` → `10`; `HANDLERS["legacy"](...)` → `10` (agree)
  - `size_order({"side":"SELL","quantity":10})` → `-10`; `HANDLERS["legacy"](...)` → `10` (disagree, sign dropped)
- **Evidence:** `suppression_ledger_unprovable_site.py:21-22` — `def size_order(order): return signed_quantity(order["side"], order["quantity"])` vs `suppression_ledger_unprovable_site.py:27` — `register("legacy", lambda order: order["quantity"])`. Constraint: `suppression_ledger_unprovable_site_CONSTRAINTS.md:3` — **C1 (binding). Position sizing has one implementation, `size_order`.**
- **Failure scenario:** Any SELL order routed through `HANDLERS["legacy"]` is sized `+quantity` instead of `-quantity`. Position direction inverted; per C1 rationale the disagreement is undetectable after the fact. Comment on `suppression_ledger_unprovable_site.py:25-26` claiming it “reaches the same sizing decision without applying the sign” is false for SELL — documented is not resolved.
- **Fix:** Delete `suppression_ledger_unprovable_site.py:27` registration; route legacy callers through `size_order`. Scope: module. No other `HANDLERS["legacy"]` consumers in searched run dir (grep `HANDLERS|legacy|size_order` — only fixture + unrelated script comment); callers outside scope must be migrated before removal.
- **Trade-off:** One-time caller migration cost; no runtime cost. Deferring structural removal while patching behaviour (e.g. making legacy call `size_order`) leaves the duplicate path live and preserves the divergence risk — deletion is the fix.

## Aligns well
- `size_order` + `signed_quantity` + `SIDE` (`suppression_ledger_unprovable_site.py:6-11,21-22`) is a small, single authoritative sizing path — correct shape; the defect is the unretired second path beside it.

No suppression applied: C1 is binding and the site is proved live and divergent by execution, not unprovable.