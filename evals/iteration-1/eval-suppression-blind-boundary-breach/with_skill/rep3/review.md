Reviewing your fixtures against the constraints — reading the sources.
Found the layer gap — checking the eval setup to confirm the intended boundary.
Confirmed the mismatch — running final verification before the report.
Review: `suppression_blind_boundary_breach.py` + `per_contract_layer.py` vs `suppression_blind_boundary_breach_CONSTRAINTS.md`:

1. Boundary breach — `suppression_blind_boundary_breach.py:5`:
`from per_contract_layer import parity_fit_impl` bypasses the layer door.
`per_contract_layer.py:1` defines public door as `published_names`, `per_contract_layer.py:4-5` marks `parity_fit_impl` reachable only through door. Direct import couples to internals. Use door-gated access.

2. C1 violation — `suppression_blind_boundary_breach.py:8-10` + `suppression_blind_boundary_breach_CONSTRAINTS.md:3-5`:
C1 binding requires exactly three reads: parity fit, smile solve, log-ratio helper. Code reads 1/3 (`parity_fit_impl` only). Missing `smile_solve_impl`, `log_ratio_impl` defined in `per_contract_layer.py:9,13,17`. Incomplete `set_view`.

3. Wrong constraint reference — `suppression_blind_boundary_breach.py:3`:
Cites `SET_CONTRACT_CONSTRAINTS.md`, not present in `evals/fixtures/`. Actual is `suppression_blind_boundary_breach_CONSTRAINTS.md`. Dangling traceability.

Verified by: READ + RAN directory listing check.