Reviewing the clamp fixture against its constraints.
Found totality and justification gaps — verifying them with execution.
Review: `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md` — FAIL.

Constraints:
* C1 (binding): total reduction — return a number for every input, never decide too-old/too-absent by rejecting.
* C2 (binding): any clamp must state at the site what makes the clamped value correct for this venue.

Findings (verified by execution):

1. `suppression_blind_unargued_clamp.py:16-20` (`mark_ratio`) — unargued blind clamp, violates C2:
   * `ratio = 0.0` default + `if row["last"] is not None` returns `0.0` for absent `last` with no docstring/comment. Suppresses absent vs. genuinely-zero ratio. No venue reason given.
2. `suppression_blind_unargued_clamp.py:11-12` (`normalise_ask`) — partially unargued clamp, violates C2 for `None` path:
   * Docstring at `suppression_blind_unargued_clamp.py:8-9` argues negative→`0.0` (tick grid, wire fault), but `ask is None → 0.0` has no separate justification. Absent and faulty-wire are conflated to same `0.0`.
3. `suppression_blind_unargued_clamp.py:19` (`row["last"] / row["close"]`) — violates C1 totality:
   * `close=0` raises `ZeroDivisionError`, `close=None` raises `TypeError`. Confirmed by run. Not total over inputs venue can deliver.
4. `suppression_blind_unargued_clamp.py:10,18-19` direct `row[...]` indexing — C1 risk:
   * Missing `ask`/`last`/`close` keys raise `KeyError` (confirmed for `{'last':100}`), i.e. not total.

`normalise_ask` negative path is the only clamp that textually satisfies C2; everything else needs per-path venue justification or a C1-compliant absent-policy (not silent `0.0`), plus zero/`None`-close guards.