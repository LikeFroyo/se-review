Reviewing your suppression ledger fixture against its constraints.
Found the constraint violation — a duplicate sizing path that drops the sign. Now running the full review.
# Review: `evals/fixtures/suppression_ledger_unprovable_site.py` with `suppression_ledger_unprovable_site_CONSTRAINTS.md`

`1 findings · C:1 M:0 m:0 i:0 · Mean 95.8/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_ledger_unprovable_site.py` + `suppression_ledger_unprovable_site_CONSTRAINTS.md` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust-boundary crossings in single-file sizing module
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F

## Findings

### [CRITICAL] Duplicate sizing path drops sign — `legacy` handler disagrees with `size_order` on SELL
- **Domain:** Correctness (A1) — cross-refs Leanness (L4)
- **Verified by:** `RAN` — executed `size_order` vs `legacy` handler on `{'side':'BUY','quantity':100}` and `{'side':'SELL','quantity':100}`; `BUY` agrees (100==100), `SELL` disagrees (-100 vs 100).
- **Evidence:** `suppression_ledger_unprovable_site.py:21-27` — symbol `size_order` / `register("legacy", ...)`:
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
  Constraint `suppression_ledger_unprovable_site_CONSTRAINTS.md:3` (C1, binding): “Position sizing has **one** implementation, `size_order`” and “every order, regardless of the path that reached it, is sized by the same function.”
- **Failure scenario:** Any SELL order dispatched through `HANDLERS["legacy"]` is sized `+quantity` instead of `-quantity` — a short is booked as a long of the same magnitude. The constraint states why this is unrecoverable: two signed-quantity implementations can disagree and the disagreement is undetectable after the fact. Ruling: code comment admits the second path (“without applying the sign”); documented is not resolved. Reachability does not require a call-site in this file — `HANDLERS` is a live registry, `register` is module-public, and the entry remains callable by name. No suppression applies.
- **Fix:** Delete the duplicate path at module scope (scope: local, deletion): remove `register("legacy", lambda order: order["quantity"])` and route the legacy entry point through `size_order`. No separate Leanness deduction taken — owner stands per dedup rule; L4 recorded as cross-reference only.
- **Trade-off:** Deletion only — no runtime cost. Migration cost: any caller relying on unsigned `legacy` behaviour must be moved to `size_order`; if such a caller depended on the bug, its sizing flips sign on SELL, which is the intended correction but requires position reconciliation.

## Aligns well
- `signed_quantity` / `size_order` separation is a single authoritative signed-quantity computation (A1).
- No other domain defects observed in 27-line scope; security/operations/interoperability surfaces not exercised.

## Cut policy
Cut by 15-cap: 0 findings (C:0 M:0 m:0 i:0). No stubs. Shown + stubbed + dropped == raised (1 == 1).