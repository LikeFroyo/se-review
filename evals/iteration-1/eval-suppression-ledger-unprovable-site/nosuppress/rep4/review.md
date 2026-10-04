Reviewing your fixtures against their constraints — reading files now.
Found a single-implementation constraint with a duplicate path — mapping the full scope.
This looks like a C1 single-implementation violation — I'll run the full review protocol to grade it.
Confirmed the sign divergence on SELL orders — checking the grading rubric to finalize severity.
# Review: `suppression_ledger_unprovable_site.py` with `suppression_ledger_unprovable_site_CONSTRAINTS.md`

`1 findings · C:1 M:0 m:0 i:0 · Mean 95.83/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_ledger_unprovable_site.py` (constraints file as intent context) · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no trust-boundary crossings in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100 · Security: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — sign-dropping second sizing path violates binding single-implementation constraint

Ruling: constraints govern over code. `suppression_ledger_unprovable_site_CONSTRAINTS.md:C1` states sizing has **one** implementation (`size_order`); the in-code comment admitting the legacy path ("never retired") is a description of history, not an authorising utterance, so it is graded as a defect per the override-tracing rule.

## Findings

### [CRITICAL] Second sizing implementation drops sign — SELL sized as BUY
- **Domain:** Correctness (A1) — cross-references Leanness (L4); single root cause reported once, no separate Leanness deduction.
- **Verified by:** `RAN` — imported module via `importlib`, called `size_order` vs `HANDLERS["legacy"]` on `{"side": "SELL", "quantity": 100}` and `{"side": "BUY", "quantity": 100}`.
- **Evidence:** `suppression_ledger_unprovable_site.py:21-27` — function `size_order` and handler registration `legacy`:
  > `def size_order(order): return signed_quantity(order["side"], order["quantity"])`
  > `register("legacy", lambda order: order["quantity"])`
  with `signed_quantity` at `:9-11` (`SIDE = {"BUY": 1, "SELL": -1}`; `sign * quantity`). Observed: `size_order(SELL,100) = -100`, `legacy(SELL,100) = +100` (divergence 200); `BUY` agrees at `+100`. Reachable via live registry `HANDLERS = {}` at `:14` / `register` at `:17-18`; `handlers: ['legacy']` confirmed at runtime.
- **Failure scenario:** Any order routed through `HANDLERS["legacy"]` records a SELL as `+quantity` instead of `-quantity`. Per constraints C1-Why, the disagreement is undetectable after the fact — the ledger holds a direction-inverted position with no marker of which path sized it. Concrete outcome: short exposure booked as long; downstream netting/risk is corrupt on arrival.
- **Fix:** Deletion, scope: local — delete line 27 `register("legacy", ...)` (and `HANDLERS`/`register` at `:14-18` if no other registrant remains); route every order through `size_order`. Covers all cited sites, not just the primary.
- **Trade-off:** Not required for deletions. Interim cost is caller migration only: any caller of `HANDLERS["legacy"]` must call `size_order`.

## Aligns well
- Centralised sign table `SIDE` + `signed_quantity` (A1): single place encoding BUY/SELL polarity.
- `size_order` itself is correct on both sides (A1, verified `RAN`).

Serial mode ran (1 file, well below the 30-file / 5,000-line fan-out ceiling); no fan-out. No permissions or coverage limits; no `Evolution candidates` (no rubric gap — L4/A1 already cover this class).