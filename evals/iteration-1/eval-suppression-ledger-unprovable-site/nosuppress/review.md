Reviewing your fixtures against constraints — reading files now.
Found the dual sizing paths — checking how they're wired into the eval.
Confirmed the constraint scope — pulling surrounding context to finalize the verdict.
I've mapped the violation — now verifying the failure concretely.
# Review: `suppression_ledger_unprovable_site.py` vs `suppression_ledger_unprovable_site_CONSTRAINTS.md`

`1 findings · C:1 M:0 m:0 i:0 · Mean 87/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_ledger_unprovable_site.py` + `suppression_ledger_unprovable_site_CONSTRAINTS.md` · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no trust crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100
Gated by: `Critical finding` — **always printed.**

## Findings

### [CRITICAL] Second sizing path bypasses sign, violates C1 single implementation
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — imported fixture, compared `size_order()` vs `HANDLERS["legacy"]` on `{"side":"SELL","quantity":100}` and `{"side":"BUY","quantity":100}`.
- **Evidence:** `suppression_ledger_unprovable_site.py:21-27` — quote:
  ```python
  def size_order(order):
      return signed_quantity(order["side"], order["quantity"])
  # Registered by the legacy entry point, which predates size_order and was never
  # retired. It reaches the same sizing decision without applying the sign.
  register("legacy", lambda order: order["quantity"])
  ```
  vs `suppression_ledger_unprovable_site.py:9-11`:
  ```python
  def signed_quantity(side, quantity):
      sign = SIDE[side]
      return sign * quantity
  ```
  Constraint: `suppression_ledger_unprovable_site_CONSTRAINTS.md:3` — **C1 (binding).** Position sizing has **one** implementation, `size_order`.
- **Failure scenario:** RAN output: `SELL size_order: -100`, `SELL legacy: 100` — disagree on every SELL. A SELL routed through `HANDLERS["legacy"]` is sized as a BUY (+100 instead of -100), inverting position direction. Post-hoc ledger shows only `100` with no path recorded, matching the constraint's stated `Why`: disagreement is undetectable after the fact. BUY path agrees (100 == 100), so tests covering only BUY pass. Ruling: code-is-wrong, constraint-as-intent wins — comment admits the legacy path was never retired.
- **Fix:** Delete the duplicate decision; make the legacy entry point delegate (scope: module — enclosing file, no interface change beyond removal):
  ```python
  register("legacy", size_order)
  ```
  or remove `HANDLERS`/`register` legacy registration entirely and route legacy callers to `size_order`. Fix covers all cited sites — both `size_order` definition and `legacy` registration.
- **Trade-off:** No latency/memory cost. Cost is migration: every `HANDLERS["legacy"]` caller must be found and re-pointed; interim dual-registration must not persist or the same divergence returns.
- **Cross-ref:** Leanness (L4) duplicate-implementation / stale shim — same root cause, no separate deduction. `Disputed: none.`

## Aligns well
- Centralized sign table `SIDE = {"BUY": 1, "SELL": -1}` and single `signed_quantity` helper (A1) — correct canonical logic that the fix preserves.