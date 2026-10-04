Reviewing your clamp fixture and constraints.
Found the two-function fixture — now mapping the review criteria.
I've mapped the scoring rubric — now digging into the defect specifics.
# Review: `evals/fixtures/suppression_blind_unargued_clamp.py` against `suppression_blind_unargued_clamp_CONSTRAINTS.md`

`2 findings · C:0 M:2 m:0 i:0 · Mean 97/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/suppression_blind_unargued_clamp.py` (contract: `suppression_blind_unargued_clamp_CONSTRAINTS.md`) · Not examined: 0 — none
Paths: 0 resolved open · Unmapped: 0 — no trust crossing located; single-process dict-in/float-out
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 80/100 · Security: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: `weakest domain: Correctness (B)` — mean band A capped by weakest pillar; no Critical, so no F-cap.

Ruling: constraints are authoritative over code — C1 (total reduction) and C2 (argued clamp at site) win where code disagrees.

## Findings

### [MAJOR] Unargued suppression: absent `last` returns `0.0` with no site justification
- **Domain:** Correctness (A8)
- **Verified by:** `RAN` — executed `mark_ratio({"last": None, "close": 100})` → `0.0`; executed `mark_ratio({"last": 0, "close": 100})` → `0.0`; both return identically.
- **Evidence:** `suppression_blind_unargued_clamp.py:16-20` in `mark_ratio(row)` — quote:
  ```
  ratio = 0.0
  if row["last"] is not None:
      ratio = row["last"] / row["close"]
  return ratio
  ```
  No comment, docstring, or venue argument at the site for why `0.0` is correct. Contrast `normalise_ask` (lines 7–9), which does argue its clamp. Violates contract C2: "Where a clamp exists it must state, at the site, what makes the clamped value correct for this venue."
- **Failure scenario:** Venue delivers a row with no trade yet (`last=None`, e.g. halted / pre-open symbol). Reduction emits `0.0`, bit-identical to a genuine −100% mark (`last=0`). A consumer cannot distinguish "absent" from "worthless" — false flat-mark feeds a limit, alert, or liquidation decision with no plausibility band at consumption. This is the guideline case "default that masks a missing required value" (`domains/correctness/type-and-contracts/guidelines/type-and-contract-assertions.md:16`).
- **Fix:** Module scope. Either reject absence (raise / return sentinel / `Optional[float]`) and let the caller decide, or keep totality with an argued, distinguishable value (e.g. documented fallback + provenance flag) stated at the site per C2. Fix must touch both the return and every consumer that currently assumes `float`.
- **Trade-off:** Rejecting absence adds caller complexity (every call site handles `None`/exception); keeping an argued fallback adds a branch plus documentation burden and risks callers ignoring the flag. Either is cheaper than silent misclassification on a money path.

### [MAJOR] Non-total reduction: `mark_ratio` raises on venue-deliverable `close`
- **Domain:** Correctness (A1)
- **Verified by:** `RAN` — executed `mark_ratio({"last": 110, "close": 0})` → `ZeroDivisionError: division by zero`; `mark_ratio({"last": 110, "close": None})` → `TypeError: unsupported operand ... 'int' and 'NoneType'`.
- **Evidence:** `suppression_blind_unargued_clamp.py:19` — `ratio = row["last"] / row["close"]` with no guard on `close`. Violates contract C1: "Every reduction is total: it returns a number for every input the venue can deliver." A zero or missing reference close is venue-deliverable. Guideline: "ratio over a derived denominator … that approaches zero, with no guard" (`domains/correctness/logic/guidelines/numeric-plausibility.md:9`).
- **Failure scenario:** One contract's reference feed delivers `close=0` (or drops the field as `None`). The per-contract reduction raises instead of returning a number, aborting the batch / depth loop or forcing a broad catch upstream that hides the cause. Single bad reference poisons an otherwise healthy reduction.
- **Fix:** Local scope. Guard the denominator at the site (e.g. `if close in (None, 0): <argued fallback or raise with context>`), with the chosen value justified per C2. Do not add a bare `try/except: return 0.0` — that converts this finding into the one above.
- **Trade-off:** A guard adds one branch and forces the C2 argument (what a zero-close mark *means* on this venue); a raise adds caller error-path work. Latency cost is one comparison; complexity cost is the venue semantic that must be written down.

## Aligns well

- `normalise_ask(row)` (`suppression_blind_unargued_clamp.py:7-13`) is the in-file positive control for C2 (A8): the `None → 0.0` and `ask <= 0 → 0.0` clamps carry the venue argument at the site ("price cannot be negative … tick grid forbids it … negative wire value is a wire fault"). Verified by `RAN` over `None / -5 / 0 / 10.5`.
- No leanness, security-path, operations, or crossing defect raised: whole-tree text search finds only the two definitions (no proved dead code per the dead-code proof rule — fixture harness is the external caller, so absence of in-tree callers is not death); no attacker-controlled source → boundary → sink is demonstrable, so no above-Info security finding per the path rule.