Fixing your suppression contract — checking implementation against its constraints.
Found a constraint violation — verifying the behavior before I report it.
Review: `suppression_blind_nan_contract.py` vs `suppression_blind_nan_contract_CONSTRAINTS.md` C1:

**Fail — binding violation at `suppression_blind_nan_contract.py:13-14`:**

```python
if quote["last"] is None or quote["last"] == "":
    return 0.0
```

* C1: uncomputable quantity is `NaN`, never `0`. Missing/empty `last` is uncomputable, not `0`.
* Violates stated rationale: `0` is a legal price, so this substitution is indistinguishable from a real observation.
* Verified: `{'space':'equity','role':'last','last':None}` → `0.0`, `last:''` → `0.0`.

**Correct parts:**
* `suppression_blind_nan_contract.py:9-10` commodity/`open_interest` → `{"absent_by_design": True}`: correct flag, not NaN/0, and correctly checked before NaN branch.
* `suppression_blind_nan_contract.py:11-12` unknown role → `NaN`: correct.

**Fix:** return `float("nan")` for `None`/`""` case.