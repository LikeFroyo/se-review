Reviewing your suppression fixture and constraints.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md` C1 — **FAIL**.

C1: uncomputable → `NaN`, never `0`; absent-by-design → flag, never `NaN`/`0`.

* Compliant:
  * `suppression_blind_nan_contract.py:9-10` commodity/`open_interest` → `{"absent_by_design": True}` — correct flag.
  * `suppression_blind_nan_contract.py:11-12` role not in `("last","quote")` → `float("nan")` — correct.
* Violation:
  * `suppression_blind_nan_contract.py:13-14` `if quote["last"] is None or quote["last"] == "": return 0.0` — direct C1 violation. Missing/uncomputable quantity substituted with `0`. Per constraints `Why`: `0` is legal price/ratio, indistinguishable from real observation. Must be `float("nan")`.

Minor doc nit: `suppression_blind_nan_contract.py:3` references `NAN_CONSTRAINTS.md`, actual file is `suppression_blind_nan_contract_CONSTRAINTS.md`.