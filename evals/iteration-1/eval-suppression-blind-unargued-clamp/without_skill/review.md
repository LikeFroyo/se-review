Reviewing your clamp fixture against its constraints — reading files now.
Found two totality and justification gaps — verifying behavior with execution.
Review: `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md` — non-compliant.

* `suppression_blind_unargued_clamp.py:16-20` violates C2: `mark_ratio` clamps absent `last` to `0.0` with no site justification for why `0.0` is correct for this venue.
* `suppression_blind_unargued_clamp.py:11-12` violates C2: `None -> 0.0` is blind. Site doc `suppression_blind_unargued_clamp.py:8-9` only argues `negative -> 0` (tick grid / wire fault), says nothing about absent.
* `suppression_blind_unargued_clamp.py:19` violates C1 (totality): verified crash on deliverable inputs — `{'last':105,'close':None}` raises `TypeError`, `{'last':105,'close':0}` raises `ZeroDivisionError`, instead of returning a number.

`normalise_ask` negative-branch is the only argued clamp; both `None`-branches are suppression blind/unargued.