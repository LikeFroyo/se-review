Reviewing your fixture against its constraints.
Found clear C1/C2 issues — verifying full context.
Review: `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md`:

* `suppression_blind_unargued_clamp.py:3`: stale constraint reference (`CLAMP_CONSTRAINTS.md` vs actual `suppression_blind_unargued_clamp_CONSTRAINTS.md`).
* `suppression_blind_unargued_clamp.py:7-13` (`normalise_ask`): satisfies **C2** — site states venue reason (tick grid forbids negative, wire fault, `0` floor). Satisfies **C1** for `None`/negative (`->0.0` verified), but not total: `row["ask"]` raises `KeyError` on missing key.
* `suppression_blind_unargued_clamp.py:16-20` (`mark_ratio`): fails **C1** and **C2**:
  * **C1 (not total, verified):** `KeyError` on missing `last`/`close`, `TypeError` on `close=None`, `ZeroDivisionError` on `close==0`. Only `last=None -> 0.0` is total.
  * **C1 (absent-decision):** `if row["last"] is not None` + default `ratio=0.0` decides absent value without returning a venue-grounded number.
  * **C2 (unargued clamp):** `0.0` fallback has no at-site justification, unlike `normalise_ask`. Nothing states what makes `0` correct for this venue.