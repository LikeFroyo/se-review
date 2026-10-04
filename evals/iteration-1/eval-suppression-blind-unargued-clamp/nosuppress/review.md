Reviewing fixture against its constraints — reading both files.
Found the two defects — gathering eval context to confirm scope.
Review: `suppression_blind_unargued_clamp.py` fails `suppression_blind_unargued_clamp_CONSTRAINTS.md` (C1+C2 binding).

* `suppression_blind_unargued_clamp.py:7-13` `normalise_ask`:
  * C1 violation: `if ask is None: return 0.0` decides absent -> present (0.0). C1 forbids absent-decision; no totality exception allowed.
  * C2 violation (partial): `None -> 0.0` has no site justification. Docstring only argues negative -> 0 (`tick grid forbids it`), not absent -> 0.
* `suppression_blind_unargued_clamp.py:16-20` `mark_ratio`:
  * C1 violation: `if row["last"] is not None` decides absent, defaults to `0.0` blind.
  * C1 violation: not total — `row["last"]/row["close"]` raises on `close=None/0`, `last=None` unchecked beyond first branch, `KeyError` on missing keys.
  * C2 violation: `0.0` fallback has no site statement of why `0.0` is correct for this venue. No docstring/comment at all.
* Minor: `suppression_blind_unargued_clamp.py:3` references `CLAMP_CONSTRAINTS.md`, actual file is `suppression_blind_unargued_clamp_CONSTRAINTS.md`.

Fix: remove silent `None/<=0 -> 0.0` coercions; either propagate `None`/raise, or add per-site venue rule proving `0.0` correct. Same for `mark_ratio` fallback and zero/None `close`.