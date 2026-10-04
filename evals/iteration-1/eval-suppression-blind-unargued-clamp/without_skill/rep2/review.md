Reviewing your fixtures against their constraints.
Found the compliant and violating patterns — now verifying the faults run.
Review: `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md`:

Constraints:
- C1: total reduction, no old/absent gating.
- C2: any clamp must justify at site why clamped value is correct for venue.

Findings:

1. `suppression_blind_unargued_clamp.py:7` `normalise_ask` — PASS. Total (`None`→`0.0`, negative→`0.0`), and site-justified: `suppression_blind_unargued_clamp.py:8-9` states tick-grid forbids negative, wire-fault → `0` floor. Satisfies C1+C2.

2. `suppression_blind_unargued_clamp.py:16` `mark_ratio` — FAIL both:
   - C2 violation `suppression_blind_unargued_clamp.py:17`: blind unargued clamp `ratio = 0.0` with no venue justification, unlike `normalise_ask`.
   - C1 violation `suppression_blind_unargued_clamp.py:18`: `if row["last"] is not None` gates on absent, defaulting to `0.0` — decides absent. Also not total: `row["last"]/row["close"]` raises `ZeroDivisionError` on `close==0`, `TypeError` on `close is None` (verified by execution).

Verdict: module non-compliant due to `mark_ratio`; `normalise_ask` is the compliant contrast.