Grading your blind-clamp probe — checking fixture against constraints.
Found the clamp and its two binding constraints — now gathering probe context for the verdict.
Confirmed the failure modes by execution — now formatting the final review.
# Correctness Review: `suppression_blind_unargued_clamp.py` vs `suppression_blind_unargued_clamp_CONSTRAINTS.md`

`3 findings · C:0 M:2 m:1 i:0 · Domain Score: 77/100 (Grade C)`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_blind_unargued_clamp.py` + `CONSTRAINTS.md` · Not examined: 0 — none
Unclassified: 0 findings fit no axis code
Ruling: `CONSTRAINTS.md` is intent; code is graded against it.

## Findings

### [MAJOR] `mark_ratio` blind 0 suppresses absent `last`
- **Domain:** Correctness (A8)
- **Verified by:** `RAN` — imported module, called `mark_ratio({'last':None,'close':50})` → `0.0`, indistinguishable from genuine `last==0`.
- **Evidence:** `suppression_blind_unargued_clamp.py:16-20` — `ratio = 0.0` / `if row["last"] is not None:` with no site comment stating what makes `0.0` correct for this venue.
- **Constraint:** Violates **C2 (binding)** — clamp exists, no venue reason at the site.
- **Failure scenario:** Missing print becomes valid `0.0` ratio; downstream P&L/risk cannot distinguish missing from worthless.
- **Fix:** Local scope — require explicit absent-handling per venue contract (propagate `None`/raise) or add site justification why `0.0` is the venue-correct value.
- **Trade-off:** Caller must now branch on absent; one extra check per call, no latency change.

### [MAJOR] `mark_ratio` non-total on `close` — crashes instead of returning a number
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — `mark_ratio({'last':100,'close':None})` → `TypeError`; `{'last':100,'close':0}` → `ZeroDivisionError`.
- **Evidence:** `suppression_blind_unargued_clamp.py:19` — `ratio = row["last"] / row["close"]`, no guard on `close`.
- **Constraint:** Violates **C1 (binding)** — reduction must return a number for every input the venue can deliver.
- **Failure scenario:** Any `None`/`0` close aborts the reduction batch with an exception.
- **Fix:** Local scope — guard denominator per venue contract (total fallback or explicit error signal consistent with C1).
- **Trade-off:** One branch per call; must agree with venue on what `close==0/None` means, otherwise the guard just moves the C2 burden.

### [MINOR] `normalise_ask` `None → 0.0` has no venue justification
- **Domain:** Correctness (A8)
- **Verified by:** `RAN` — `normalise_ask({'ask':None})` → `0.0`; docstring at `suppression_blind_unargued_clamp.py:8-9` justifies only the negative→0 clamp (tick grid forbids negative, wire fault).
- **Evidence:** `suppression_blind_unargued_clamp.py:11-12` — `if ask is None: return 0.0`, bare, no at-site reason why absent is `0.0` for this venue.
- **Constraint:** Partial **C2** gap — negative clamp is argued, absent clamp is not; missing and zero asks become indistinguishable.
- **Fix:** Local scope — add at-site venue reason for absent→0, or separate absent signal from price `0.0`.

## Aligns well
- `normalise_ask:13` (A1): negative→`0.0` clamp states venue reason at site (tick grid, wire fault, `0` as only defensible floor) — satisfies C2; total over `None`/negative/positive — satisfies C1.