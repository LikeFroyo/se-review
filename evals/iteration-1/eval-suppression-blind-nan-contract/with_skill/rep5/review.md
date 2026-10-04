Fixing your blind NaN check — reviewing the fixture against its constraints.
Found a C1 violation — checking the run layout to confirm scope.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md`:

* `suppression_blind_nan_contract.py:9-10` compliant with C1: `commodity`/`open_interest` returns `{"absent_by_design": True}`, not NaN/0.
* `suppression_blind_nan_contract.py:11-12` compliant: unsupported `role` returns `NaN`.
* `suppression_blind_nan_contract.py:13-14` violates C1 (binding): `None`/`""` `last` returns `0.0`. Uncomputable quantity must be `NaN`, never `0`. Per constraints, `0` is a legal price and indistinguishable from a real observation.

Verdict: non-compliant. Fix: return `float("nan")` on line 14.