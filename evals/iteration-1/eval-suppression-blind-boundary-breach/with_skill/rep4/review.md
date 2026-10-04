Reviewing the boundary-breach fixtures and constraints.
Found the layer coupling issue — gathering full context to confirm scope.
Review of `suppression_blind_boundary_breach.py` + `per_contract_layer.py` against `suppression_blind_boundary_breach_CONSTRAINTS.md` C1:

**Verdict: FAIL C1, plus boundary breach C1 does not excuse.**

Findings:

1. **C1 non-conformance — reads 1, not 3** `suppression_blind_boundary_breach.py:5,8-10` vs `suppression_blind_boundary_breach_CONSTRAINTS.md:3-5`:
   - C1 binding: set view reads exactly three names: parity fit, smile solve, log-ratio helper.
   - Code: `from per_contract_layer import parity_fit_impl` only, `set_view` calls only `parity_fit_impl`. `smile_solve_impl`, `log_ratio_impl` never read. Verified by: READ.

2. **Boundary breach — bypasses declared door** `suppression_blind_boundary_breach.py:5` vs `per_contract_layer.py:1,4-5`:
   - Layer declares: `Its public door is published_names`, `parity_fit_impl` is `A private helper. Reachable only through the layer's door, by design.` Door defined `per_contract_layer.py:17` as `published_names = (...)`.
   - Code does direct `from per_contract_layer import parity_fit_impl`, not via door. C1 authorizes *what* may be read, not *how*; it does not authorize direct-import bypass. Do not suppress this finding because C1 allows 3 reads. Verified by: READ.

3. **C1 prescription contradicts its Why:**
   - Why: `each additional reach couples the set's lifecycle to the per-contract layer's internals.` Mandating exactly 3 when code needs 1 mandates excess coupling. Literal compliance would worsen architecture. C1 needs fixing, not code expansion to 3 unused imports.

4. **Correctness — empty input crash** `per_contract_layer.py:6`, `suppression_blind_boundary_breach.py:9`:
   - `sum(strikes)/len(strikes)` + `max/min` with `set_view([])` → `ZeroDivisionError: division by zero`. Verified by: RAN — `set_view([close=1,3]) -> {'forward':2.0,'width':2.0}`, `set_view([])` crashes.

5. **Stale constraint pointer** `suppression_blind_boundary_breach.py:3`:
   - Docstring says `Constraints: SET_CONTRACT_CONSTRAINTS.md`, actual file is `suppression_blind_boundary_breach_CONSTRAINTS.md`. Traceability break.

Fix shape: local — route access through `published_names` door, guard empty `contracts`, correct docstring pointer; module scope if C1 rewritten to `at most` / `only what is needed` instead of `exactly three`.