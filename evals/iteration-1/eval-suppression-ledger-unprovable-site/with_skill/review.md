Grading the unprovable-site fixture against its constraints — inspecting the run.
Found a legacy bypass alongside the sizing rule — now mapping the full eval setup.
Scope is clear — now loading the review domains to grade the violation.
# Review: `evals/fixtures/suppression_ledger_unprovable_site.py` with `suppression_ledger_unprovable_site_CONSTRAINTS.md`

`1 findings · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_ledger_unprovable_site.py` with `suppression_ledger_unprovable_site_CONSTRAINTS.md` as intent · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust-boundary crossings in single-file sizing module
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps the grade at F

## Findings

### [CRITICAL] Second sizing implementation violates binding C1 and inverts SELL quantity
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — imported fixture module and executed both paths on `BUY`/`SELL` orders with `quantity=100`
- **Evidence:** `suppression_ledger_unprovable_site.py:21-27` — function `size_order` vs registry entry:
  `def size_order(order): return signed_quantity(order["side"], order["quantity"])`
  `register("legacy", lambda order: order["quantity"])`
  with comment at `:25-26` admitting it "reaches the same sizing decision without applying the sign."
  Intent: `suppression_ledger_unprovable_site_CONSTRAINTS.md:3` — **C1 (binding).** "Position sizing has **one** implementation, `size_order`."
- **Failure scenario:** `DERIVED` chain `HANDLERS["legacy"]({"side":"SELL","quantity":100}) → 100` vs `size_order(...) → -100` (confirmed by `RAN`: `BUY` agrees `100==100`, `SELL` diverges `-100` vs `100`). Any SELL order routed through the legacy path is booked long instead of short — position/state corruption, and per C1's own rationale the disagreement is "undetectable after the fact." Absence of an in-file caller of `HANDLERS["legacy"]` does not mitigate: the registry is module-global and populated at import time, and C1 bans the second implementation's existence, not only its observed invocation. No suppression ledger entry can waive a binding constraint without an authorising utterance; none is present. Ruling: code-is-wrong, doc-as-intent wins.
- **Fix:** Delete the legacy registration at `:27` (scope: local, one line); route every order through `size_order`. If `HANDLERS`/`register` has no other legitimate consumer, delete that infrastructure as a follow-up module-scope cleanup.
- **Trade-off:** No latency/memory cost; complexity decreases by removing one code path and one mutable-global dispatch.
- **Cross-ref:** Leanness (L4 redundancy / duplicate implementations) describes the same root cause and takes no separate deduction per owner-stands rule — owner here is Correctness via demonstrated sign-inversion scenario.

## Aligns well
- `size_order` (A1) correctly delegates to `signed_quantity` with explicit `SIDE` sign map — the intended single implementation.