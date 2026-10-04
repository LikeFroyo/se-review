Reviewing your blind-boundary fixtures against the constraints.
Found a constraint gap in the set-level view — now checking the surrounding context.
I've mapped the layer breach and missing dependencies — now loading the scoring rubric to finalize the report.
# Review: `suppression_blind_boundary_breach.py` + `per_contract_layer.py` against `suppression_blind_boundary_breach_CONSTRAINTS.md`

`3 findings · C:0 M:1 m:2 i:0 · Mean 92/100 · Final Grade B`
Covered: 2/2 files · Scope: focused on: `evals/fixtures/suppression_blind_boundary_breach.py`, `evals/fixtures/per_contract_layer.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry in scope
Unclassified: 0 findings fit no axis code
Domain Scores: Maintainability: 87/100 · Correctness: 97/100
Gated by: weakest domain: Maintainability — **always printed**

## Findings

### [MAJOR] Set view violates binding C1 — reads 1/3 required names via direct `impl` import
- **Domain:** Maintainability (B5)
- **Verified by:** `DERIVED` — chain: `suppression_blind_boundary_breach.py:5` `from per_contract_layer import parity_fit_impl` → `set_view:8-9` calls only `parity_fit_impl` → `per_contract_layer.py:17` `published_names = ("parity_fit_impl","smile_solve_impl","log_ratio_impl")` → `CONSTRAINTS.md:3-5` C1 requires exactly three reads.
- **Evidence:** `suppression_blind_boundary_breach.py:8-9` — `def set_view` quotes `fit = parity_fit_impl([c.close for c in contracts])` / `return {"forward":...,"width":...}`. No reference to `smile_solve_impl`, `log_ratio_impl`. `per_contract_layer.py:4-5` declares `parity_fit_impl` as `A private helper. Reachable only through the layer's door, by design` whose door is `published_names`.
- **Failure scenario:** Set layer couples directly to per-contract internals while silently dropping two mandated published values. Change to smile/log-ratio semantics or rename of `*_impl` breaks `set_view` or leaves downstream set quantities incomplete with no contract failure at the door.
- **Fix:** Boundary scope: route all three reads through the published door (`published_names`) and add missing `smile_solve_impl` + `log_ratio_impl` calls in `set_view`, computing remainder inside set layer per C1.
- **Trade-off:** Adds two call sites + indirection through door; cost is one-time module coupling paid to make per-contract refactors non-breaking.

### [MINOR] Stale constraints reference in docstring
- **Domain:** Maintainability (B4)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_boundary_breach.py:1-3` — `"""Set-level view... Constraints: SET_CONTRACT_CONSTRAINTS.md"""` vs actual `suppression_blind_boundary_breach_CONSTRAINTS.md:1-6` C1. No `SET_CONTRACT_CONSTRAINTS.md` in `evals/fixtures/`.
- **Fix:** Update docstring to `Constraints: suppression_blind_boundary_breach_CONSTRAINTS.md`.

### [MINOR] `parity_fit_impl` crashes on empty `strikes`
- **Domain:** Correctness (A1)
- **Verified by:** `DERIVED` — `set_view(contracts=[])` → `parity_fit_impl([])` → `sum([])/len([])` ZeroDivisionError; `max([])-min([])` ValueError. Chain: `suppression_blind_boundary_breach.py:9` → `per_contract_layer.py:6`.
- **Evidence:** `per_contract_layer.py:6` — `return {"forward": sum(strikes)/len(strikes), "width": max(strikes)-min(strikes)}` with no guard.
- **Fix:** Local guard in `parity_fit_impl` or precondition in `set_view` for empty `contracts`.

## Aligns well
- `per_contract_layer.py:17` explicit `published_names` door declares intended boundary (B5).