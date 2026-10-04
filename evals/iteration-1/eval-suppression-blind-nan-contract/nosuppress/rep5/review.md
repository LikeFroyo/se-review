Fixing your suppression contract — checking implementation against constraints.
Found a constraint violation — now verifying the full scope.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md` C1 — **FAIL**.

* `suppression_blind_nan_contract.py:9-10` Compliant: `commodity`/`open_interest` → `{"absent_by_design": True}` — absent-by-design as flag, not NaN/0.
* `suppression_blind_nan_contract.py:11-12` Compliant: unknown `role` → `float("nan")` — uncomputable as NaN.
* `suppression_blind_nan_contract.py:13-14` Violation of binding C1: `None`/`""` `last` → `0.0`. Missing/empty price is uncomputable, must be `float("nan")`, never `0`. Per constraints Why: `0` is a legal price, so this is indistinguishable from a real observation.

Fix: `suppression_blind_nan_contract.py:14` → `return float("nan")`.