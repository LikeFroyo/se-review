Fixing your clamp review — inspecting the fixture and constraints.
Got the fixture — now gathering the eval context.
I've mapped the constraints — now loading the review standards to grade against them.
I've got the full picture — now verifying the failure modes before finalizing.
# Review: `suppression_blind_unargued_clamp.py` against `suppression_blind_unargued_clamp_CONSTRAINTS.md`

`2 findings · C:0 M:2 m:0 i:1 · Mean 90/100 · Final Grade C`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_blind_unargued_clamp.py` + `suppression_blind_unargued_clamp_CONSTRAINTS.md` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry points in 20-line pure-function module
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 80/100 · Maintainability: 100/100
Gated by: `weakest domain: Correctness (C)` — **always printed.**

Binding constraints applied (repo's own standards, judged against rather than imported opinions):

> **C1 (binding).** Nothing decides too-old/too-absent. Every reduction is total: returns a number for every input the venue can deliver.
> **C2 (binding).** Where a clamp exists it must state, at the site, what makes the clamped value correct for this venue.

## Findings

### [MAJOR] `mark_ratio` blind suppression of absent `last` — unargued 0.0 clamp violates C2
- **Domain:** Correctness (A8)
- **Verified by:** `RAN` — imported module, `mark_ratio({"last":None,"close":50}) -> 0.0` with no comment/justification at site.
- **Evidence:** `suppression_blind_unargued_clamp.py:16-20` — `ratio = 0.0; if row["last"] is not None: ratio = row["last"]/row["close"]; return ratio`
- **Failure scenario:** Missing `last` returns `0.0`, indistinguishable from a genuine flat/zero mark. Downstream depth reduction consumes it as a valid number, silently mis-pricing that contract. This is the `suppression_blind_unargued` shape: absence decided as zero with no venue reason stated.
- **Fix:** Scope: local. Either propagate absence explicitly per C1 intent (raise/return sentinel the caller handles) or, if `0.0` is venue-correct, add C2 site argument stating why 0 is correct for this venue — same standard `normalise_ask` meets. Do not keep silent `0.0`.
- **Trade-off:** Local branch + comment: +2 lines, no latency/memory cost; cost is deciding the contract (sentinel vs justified zero) and updating callers if sentinel chosen.

### [MAJOR] `mark_ratio` non-total on venue-deliverable `close` — violates C1 totality
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — `{"last":100,"close":0}` raises `ZeroDivisionError`; `{"last":100,"close":None}` raises `TypeError`; `{"last":100}` (missing `close`) raises `KeyError`. No number returned.
- **Evidence:** `suppression_blind_unargued_clamp.py:16-20` — unguarded `row["last"]/row["close"]`
- **Failure scenario:** Any deliverable zero/None/missing `close` with present `last` crashes this reduction instead of returning a number, breaking C1's explicit `returns a number for every input the venue can deliver`. One bad contract aborts its reduction path.
- **Fix:** Scope: module. Define total behaviour for `close` in {0, None, missing} with C2 site argument, consistent with whatever C1 totality requires here.
- **Trade-off:** Guard + documented fallback: +3-5 lines, negligible cost; cost is choosing the venue-correct total value, not the branch itself.

### [INFO] `normalise_ask` ruling: compliant — not flagged
- **Domain:** Correctness (A8)
- **Verified by:** `READ`
- **Evidence:** `suppression_blind_unargued_clamp.py:7-13` — `"""A price cannot be negative on this venue; the tick grid forbids it, so a negative wire value is a wire fault and 0 is the only defensible floor."""` + `if ask is None: return 0.0` / `return ask if ask > 0 else 0.0`
- **Ruling:** C2 satisfied at the site with venue-specific reason (tick grid, wire fault, floor); total (number for None/negative/positive). Deliberately no finding here — distinguishing argued clamp from blind clamp is the point of this fixture.

## Aligns well
- `normalise_ask:7-13` states venue reason at clamp site (A8): tick-grid argument for 0-floor.