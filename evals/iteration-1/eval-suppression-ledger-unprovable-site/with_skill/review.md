Reviewing the fixture against its constraints inside the workspace.
Found the constraint violation — now checking how the skill handles unprovable findings.
I see the pattern — now locating the exact pass criteria for this case.
# Review: `suppression_ledger_unprovable_site.py` with `suppression_ledger_unprovable_site_CONSTRAINTS.md`

`1 finding · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
`Covered: 1/1 files · Scope: focused on: evals/fixtures/suppression_ledger_unprovable_site.py + suppression_ledger_unprovable_site_CONSTRAINTS.md · Not examined: 0 — none`
`Paths: 0 · Unmapped: 0 — no entry points / sinks in scope`
`Unclassified: 0 findings fit no axis code`
`Domain Scores: Correctness: 100/100 · Leanness: 75/100 · Maintainability: 100/100 · Security: 100/100 · Interoperability: 100/100 · Operations: 100/100`
`Gated by: Critical finding — Final Grade F, weakest-domain cap would be C`

## Findings

### [CRITICAL] Second sizing implementation violates C1, diverges on SELL
- **Domain:** Leanness (L4)
- **Verified by:** `RAN` — imported module, called `size_order` vs `HANDLERS["legacy"]` on `{"side":"SELL","quantity":5}` and `{"side":"BUY","quantity":5}`
- **Evidence:** `suppression_ledger_unprovable_site.py:21-27` — `def size_order(order): return signed_quantity(order["side"], order["quantity"])` vs `register("legacy", lambda order: order["quantity"])`; constraint `suppression_ledger_unprovable_site_CONSTRAINTS.md:3-7` — `C1 (binding). Position sizing has one implementation, size_order.`
- **Failure scenario:** `size_order(SELL,5)=-5`, `legacy(SELL,5)=+5` — RAN confirmed; `BUY` agrees at `+5`. Two signed-quantity paths already disagree. Per C1 why-clause disagreement is undetectable after the fact. Permanent carrying cost: two implementations to keep in sync. Live production dispatch via `HANDLERS["legacy"]` not in scope — no lookup site in file — so proven-execution outage not claimed; Critical rests on L4 redundancy + carrying cost, not on proven dispatch.
- **Fix:** Delete second implementation: remove `suppression_ledger_unprovable_site.py:27` registration and `HANDLERS` legacy path; route all orders through `size_order`. Scope: module.
- **Trade-off:** Not required for deletions. No behavior to preserve — legacy path is the defect.

Deduplication note: Correctness live-mis-sizing is same root cause, owned here. Correctness takes no separate deduction. `Disputed: none.`

## Aligns well
- `suppression_ledger_unprovable_site.py:9-11` explicit sign table `SIDE={"BUY":1,"SELL":-1}` (D3).
- Docstring admits legacy origin, does not claim authorization — treated as context per documented-is-not-resolved.

## Deliberate — constraints applied
`candidates raised: 1 · probes run: 0 · suppressed: 0 · downgraded: 0 · annotated: 0 · unprobed: 0 · voided: 0 · budget: 0/cap (not hit)`
`Retained scope: none declared`
`Re-read of suppressed rows: 0 confirmed | 0 reversed`

Shape `a second implementation of one concept` matches catalogue. No suppression: C1 requires one implementation, so constraint argues for reporting, not withdrawing. Only admissible enforcement site would be an enforced check/guard/contract/config; comment on `suppression_ledger_unprovable_site.py:25-26` and suspect code are inadmissible per `deliberate.md` Pass A-4 / Pass B. Prose rank-5 alone is Low, cannot suppress. Unresolvable dynamic dispatch (`HANDLERS` with no caller in scope) is recorded as verification limit above, not as absence.