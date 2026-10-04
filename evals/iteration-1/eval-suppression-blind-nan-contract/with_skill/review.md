Reviewing the evaluation fixture and constraints.
Checked the fixture against C1 — found a binding violation; now gathering surrounding eval context.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md` C1:

* `suppression_blind_nan_contract.py:13-14` — Fail (binding): `if quote["last"] is None or quote["last"] == "": return 0.0`. Uncomputable quantity returns `0`, violates C1 “NaN, never 0”. Verified by run: `role=last, last=None → 0.0`, `last="" → 0.0`, neither `NaN`. Indistinguishable from real `0` price per `Why`.
* `suppression_blind_nan_contract.py:9-10` — Pass: `commodity/open_interest → {"absent_by_design": True}`, correct flag, not `NaN`/`0`.
* `suppression_blind_nan_contract.py:11-12` — Pass: invalid `role → NaN`.
* `suppression_blind_nan_contract.py:3` — Info: docstring references `NAN_CONSTRAINTS.md`, actual file is `suppression_blind_nan_contract_CONSTRAINTS.md`.

Verdict: non-compliant. Fix: return `float("nan")` for missing `last`.