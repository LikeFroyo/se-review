Reviewing your clamp fixture against its constraints.
Found C1/C2 gaps on first pass — now checking the run directory for full context.
Confirmed the suspected totality failure — now verifying the edge cases.
Review: `suppression_blind_unargued_clamp.py:1-20` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md:1-6`

* `suppression_blind_unargued_clamp.py:3`: wrong pointer — `CLAMP_CONSTRAINTS.md` ≠ actual `suppression_blind_unargued_clamp_CONSTRAINTS.md`.
* C1 (total: returns number for every venue input) — FAIL:
  * `suppression_blind_unargued_clamp.py:7-13` `normalise_ask`: total — `None->0.0`, `ask<=0->0.0` — passes.
  * `suppression_blind_unargued_clamp.py:16-20` `mark_ratio`: not total. Verified: `{'last':10,'close':None}` → `TypeError`, `{'last':10,'close':0}` → `ZeroDivisionError`.
* C2 (clamp must state at site what makes value correct for venue) — FAIL:
  * `suppression_blind_unargued_clamp.py:8-9`: negative→`0.0` has venue reason (`tick grid forbids it`) — passes.
  * `suppression_blind_unargued_clamp.py:11-12`: `None->0.0` has no venue reason — fails.
  * `suppression_blind_unargued_clamp.py:17-18`: `last is None->0.0` has no venue reason — fails, blind default suppresses absence.