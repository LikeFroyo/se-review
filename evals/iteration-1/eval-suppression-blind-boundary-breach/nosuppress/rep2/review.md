Reviewing your boundary files against constraints — checking for breaches.
Found a direct import that bypasses the layer door — now mapping the full scope.
Review: `suppression_blind_boundary_breach.py` + `per_contract_layer.py` vs `suppression_blind_boundary_breach_CONSTRAINTS.md`:

* FAIL — boundary breach: `suppression_blind_boundary_breach.py:5` `from per_contract_layer import parity_fit_impl` bypasses declared door. `per_contract_layer.py:1` states public door is `published_names`; `per_contract_layer.py:4-5` states `parity_fit_impl` is private, reachable only through door by design. Direct `*_impl` import couples to internals.
* FAIL — C1 binding: `suppression_blind_boundary_breach_CONSTRAINTS.md:3-5` requires set view reads exactly three names: parity fit, smile solve, log-ratio. `suppression_blind_boundary_breach.py:5,8` reads/uses only one (`parity_fit_impl`). Missing `smile_solve_impl`, `log_ratio_impl`.
* Traceability defect: `suppression_blind_boundary_breach.py:3` cites `SET_CONTRACT_CONSTRAINTS.md`, not applicable `suppression_blind_boundary_breach_CONSTRAINTS.md`.
* Lower layer compliant on publication set: `per_contract_layer.py:17` publishes exactly the three C1 names, matching constraints.