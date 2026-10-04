Grading your suppression contract against its constraints.
Found a C1 violation — now mapping the surrounding eval context.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md` C1:

* `suppression_blind_nan_contract.py:7-10` — compliant: `commodity`/`open_interest` returns `{"absent_by_design": True}` flag, not NaN/0. Unsupported `role` returns `float("nan")`.
* `suppression_blind_nan_contract.py:13-14` — violation of binding C1: `if quote["last"] is None or quote["last"] == "": return 0.0`. Uncomputable quantity must be NaN, never 0. Fix: `return float("nan")`. Per constraints, `0` is a legal price/ratio and indistinguishable from a real observation.
* `suppression_blind_nan_contract.py:3` — traceability: docstring cites `NAN_CONSTRAINTS.md`, actual file is `suppression_blind_nan_contract_CONSTRAINTS.md`.

Verdict: fail C1, requires line 14 change.