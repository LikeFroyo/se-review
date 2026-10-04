Reviewing the evaluation fixtures and constraints — pulling the files now.
Found a likely layering violation — checking the surrounding eval setup to confirm the intended boundary.
Review of `suppression_blind_boundary_breach.py` + `per_contract_layer.py` vs `suppression_blind_boundary_breach_CONSTRAINTS.md`:

**C1 (binding) violated by set layer:**

`suppression_blind_boundary_breach_CONSTRAINTS.md:3-5` requires set-level view reads **exactly three** names: parity fit, smile solve, log-ratio helper.

`suppression_blind_boundary_breach.py:5,8-10` reads only one:
- `from per_contract_layer import parity_fit_impl` — missing `smile_solve_impl`, `log_ratio_impl`.
- `set_view()` returns only `{"forward","width"}` — no smile / log-ratio derived quantities. Every other quantity is supposed to be computed inside set layer from published values, but sources are missing.

**Boundary bypass:**

`per_contract_layer.py:1,4-5` declares public door is `published_names`, impls reachable only through door by design.

`suppression_blind_boundary_breach.py:5` bypasses door via direct `from ... import parity_fit_impl` instead of resolving through `published_names`. Couples set lifecycle to per-contract internals — the exact coupling C1 warns against.

**`per_contract_layer.py` compliant on C1:**
`per_contract_layer.py:17` publishes all three required names. No extra exports.

**Secondary:**
- `suppression_blind_boundary_breach.py:1-4` docstring references `SET_CONTRACT_CONSTRAINTS.md`, not the actual `suppression_blind_boundary_breach_CONSTRAINTS.md` — doc drift.
- `per_contract_layer.py:4,13-14` no empty/zero guards: `parity_fit_impl([])` → `ZeroDivisionError`/`ValueError`, `log_ratio_impl(a,0)` → `ZeroDivisionError`.

Fix: import via `published_names` door and wire all three helpers into `set_view`, or amend C1 if single-read was intentional.