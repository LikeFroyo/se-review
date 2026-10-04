Reviewing your blind-unargued clamp fixture against its constraints.
Found the two-function fixture and its totality constraints — now gathering review context.
Review: `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md` (C1=total, C2=clamp must justify venue-correctness at site):

* `suppression_blind_unargued_clamp.py:7-13` `normalise_ask`: C1 pass — total (`None->0.0`, `ask<=0->0.0`). C2 pass for negative clamp — `suppression_blind_unargued_clamp.py:8-9` states venue reason (`tick grid forbids it`, `wire fault`, `0 is only defensible floor`). Gap: `suppression_blind_unargued_clamp.py:12-13` `None->0.0` has no venue-correctness argument; docstring only covers negative wire value, not absence.
* `suppression_blind_unargued_clamp.py:16-20` `mark_ratio`: C1 fail (binding) — not total. Verified: `{'last':10,'close':0}` raises `ZeroDivisionError`, `{'last':10,'close':None}` raises `TypeError`. No handling for `close` absent/zero.
* `suppression_blind_unargued_clamp.py:17-19` `mark_ratio`: C2 fail — silent clamp `last is None -> 0.0` with no site justification.

Verdict: `normalise_ask` largely compliant, `mark_ratio` violates C1 and C2.