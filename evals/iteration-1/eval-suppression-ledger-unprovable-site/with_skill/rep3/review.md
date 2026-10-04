Reviewing your suppression ledger fixture against its constraints — checking the implementation now.
Found the constraint violation — a duplicate sizing path that disagrees on sells. Now I'll run the full multi-domain review.
I've mapped the relevant audit domains — now verifying the behavioral divergence before finalizing the report.
# Review: `evals/fixtures/suppression_ledger_unprovable_site.py` vs `suppression_ledger_unprovable_site_CONSTRAINTS.md` (C1)

`1 findings · C:1 M:0 m:0 i:0 · Mean 96/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_ledger_unprovable_site.py` (+ constraints as intent) · Not examined: 0 — none
Paths: 0 open · Unmapped: 0 — no crossings nothing could reach or classify
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 75/100 · Leanness: 100/100 · Maintainability: 100/100 · Security: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — serial mode (1 file, below fan-out ceiling)

Ruling: repo intent (`*_CONSTRAINTS.md:3-7`, C1 binding: one implementation, `size_order`) governs over the module docstring claim of "one implementation reached two ways". Code-is-right does not apply; there are two implementations and they disagree.

## Findings

### [CRITICAL] Duplicate sizing implementation inverts SELL via `legacy` path
- **Domain:** Correctness (A1). Cross-refs Leanness (L4) — no separate deduction per single-root-cause rule.
- **Verified by:** `RAN` — imported fixture, called `size_order({"side":"SELL","quantity":10})` → `-10` vs `HANDLERS["legacy"](same)` → `+10`; `BUY` agrees at `+10`.
- **Evidence:** `suppression_ledger_unprovable_site.py:21-27` — `size_order`, `def size_order(order): return signed_quantity(order["side"], order["quantity"])`, vs `register("legacy", lambda order: order["quantity"])` with comment admitting the second path "reaches the same sizing decision without applying the sign".
- **Failure scenario:** Any `SELL` order dispatched through `HANDLERS["legacy"]` is sized `+q` instead of `-q` — 20-unit divergence on `q=10`, long recorded instead of short. Position/state corruption and inverted exposure; undetectable after the fact per C1's own rationale. `HANDLERS` string-keyed registry is a caller-hiding mechanism per dead-code proof procedure, so absence of an in-file caller does not prove death — the entry point is live by construction.
- **Fix:** Deletion, scope: module. Delete `register("legacy", ...)` at line 27 and reroute any `HANDLERS["legacy"]` dispatcher to `size_order`. No second implementation retained.

## Aligns well
- Centralized sign table `SIDE` + `signed_quantity` (A1): single sign rule, correct on its own path.
- Intent stated as binding constraint with rationale (C1), making the violation decidable without inferring intent.