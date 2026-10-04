Grading your blind-spot contract against its constraints — reading both now.
Found a C1 violation — checking for wider context before finalizing.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md` C1 — FAIL.

* `suppression_blind_nan_contract.py:9-10` — compliant: `commodity`+`open_interest` returns `{"absent_by_design": True}` — flag, not NaN/0, as C1 requires for absent-by-design.
* `suppression_blind_nan_contract.py:11-12` — compliant in isolation: uncomputable role -> `float("nan")`.
* `suppression_blind_nan_contract.py:13-14` — violates binding C1: `if quote["last"] is None or quote["last"] == "": return 0.0`. Missing/uncomputable quantity must be NaN, never 0. `0` is a legal price per constraints, so this is indistinguishable from a real observation.

Fix: return `float("nan")` on line 14.