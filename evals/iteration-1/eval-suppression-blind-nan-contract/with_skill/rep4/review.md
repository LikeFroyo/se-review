Reviewing your blind NaN suppression contract and constraints.
Checked the fixture against its constraints — now mapping the eval harness for full context.
Review: `suppression_blind_nan_contract.py:13-14` violates `C1`:

* `suppression_blind_nan_contract.py:9-10` correct: `commodity/open_interest` → `{"absent_by_design": True}`, not NaN/0.
* `suppression_blind_nan_contract.py:11-12` correct: wrong `role` → `float("nan")`.
* `suppression_blind_nan_contract.py:13-14` FAIL: `last is None/""` → `0.0`. Missing/uncomputable price must be `NaN` per C1 — `0 is a legal price`, so this is indistinguishable from real observation.

Fix: `return float("nan")` on line 14.