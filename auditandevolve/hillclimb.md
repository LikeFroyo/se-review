# Phase 5 — Hillclimb

Improve the skill against a validated eval, one change at a time, behind a held-out
split. Read this file only during Phase 5.

**This file is your gate and you may not edit it while Phase 5 runs.** `python3
../scripts/pass_freeze.py begin 5` on entry and `verify` on exit hold it by content hash, so the
keep/revert table below cannot be rewritten by the round it judges. The general rule is that a
pass may not edit any file it read.

This is not a replacement for Phase 4. Phase 4 proves a specific guideline landed; this
improves the whole surface against a corpus that already satisfies `eval-design.md`.

## Preconditions

- Diagnostics pass: the corpus is not saturated, the trigger rate is measured, and
  grader determinism is known. **If the corpus is saturated, quality hillclimbing
  cannot run and this path does not start** — see *What each objective can actually be
  measured by* for what may be optimised instead, and for why cost is not among them.
- One objective, stated, that names the surface permitted to change. It is detection
  quality or latency. Anything else is refused until a metric for it exists.
- Cases split at random into **train** and **test**, **never by baseline score**, and
  stratified so both splits carry the same mix of case kinds. Selecting the low scorers
  into train guarantees the loop sees only the tail, and picking cases *because* they
  scored low buys regression to the mean — the split then reports a gain that is the
  selection unwinding. **Before round one, confirm the two splits' baseline means agree
  within noise.** If they do not, re-draw. A split whose halves differ is not a control.
- Train transcripts may be read. Test is never read by the hillclimber and never informs
  a patch.

## Choosing the surface

- **Cheap to iterate.** Prompts, skill descriptions, and instruction files change and
  revert in seconds. Open-ended harness changes do not. Hillclimb text.
- **Attributable.** The metric must be directly coupled to the surface being edited.
  Trigger rate is coupled to the skill description; detection rate is coupled to the
  guidelines. If a change cannot move the metric it is being aimed at, do not make it.
- **Well-scoped.** A saturated eval makes quality optimization impossible. That is a
  stop, not a redirect: the next section says which objectives remain measurable, and a
  saturated corpus is not permission to pick a different one.

## What each objective can actually be measured by

An objective with no metric is not an objective, it is a direction. Check the metric exists **before**
committing the loop to it, and refuse the objective if it does not.

| Objective | Measured by | Usable? |
|---|---|---|
| Detection quality | assertion pass rate on a split | yes, subject to the noise floor above |
| Latency | `duration_ms` in `timing.json` | yes, with a caveat — it includes harness overhead, so a small delta is not a latency delta |
| Cost | **nothing in this harness** | **no** |

Cost is the interesting one, and the reason is a deliberate decision elsewhere in the tree. A portable
cost metric needs token usage, and token usage comes from whichever session runner is configured. This
harness takes its runner from the environment rather than naming one, and records a configuration
digest rather than the identity of what ran — which is the right call for neutrality and
reproducibility, and it is also what makes a true cost figure unobtainable here.

So: **do not optimise cost in this path.** Two proxies are available and neither is cost. `duration_ms`
is wall-clock including harness overhead, so it moves when the harness moves. `output_chars` is a length,
not a price, and it rewards terseness regardless of whether the terseness is correct — optimise it and
you are optimising the thing `eval-design.md` warns about, in a new place. Refuse the cost objective
and say why. A loop handed an unmeasurable objective will report movement in a proxy and call it a win.

If a cost figure is genuinely required, that is a finding about the harness, and it is raised rather
than worked around.

## Noise floor, before round one

Compare the eval's noise — score movement from chance alone, which includes the grader's
flip rate — against the smallest improvement you would actually act on. If the noise is
larger than that improvement, stop editing and add cases or repetitions. Reporting a gain
that sits inside the noise is the failure mode this step exists to prevent.

The number comes from `python scripts/eval_diagnostics.py` under `REPLICATE SPREAD`. An eval
with one replicate has no spread, and an eval with no spread has no noise floor — so **re-run it
with `--reps N` before this step can be completed**, not after. An eval with no replicate count
is a precondition you have not met.

## Each round

1. Read the previous round's **train** transcripts.
2. Propose exactly one change, as a patch. Aim at a root cause: rewrite the section that
   causes the failure, or add the missing rule. Do not reword a line. If the expected
   effect is smaller than the noise floor, propose nothing this round.

   **Offer the patch to the ledger and let it refuse:**
   `python3 ../scripts/attempts_ledger.py propose --surface <path> --patch <file> --base-commit <sha>`
   A patch already tried and reverted is refused, with the round and the numbers that
   rejected it. **Matching is by content digest, never by prose** — a re-proposal is
   written from the same transcripts and will usually be worded differently, so a
   description-match would miss it and the judgement would sit with the one party that
   wants the change.
3. **Read the patch as an attack on the tree's own checks.** Before scoring it, ask what the
   patch did to the thing doing the scoring. A patch that lowers a threshold, drops a
   required element, widens an allowance, softens a trigger, or rewords a rule so an existing
   finding stops matching it has not improved the skill — it has improved its report of the
   skill. Continue to the next step only if the patch leaves every check stricter or unchanged.
4. Run the eval with the patch applied.
5. Decide, and commit to it:
   - train ↑ and test ↑ → **keep**
   - train ↑ and test flat → **revert**; this is overfitting
   - either score ↓ → **revert**
6. Never paste failure content into the patch. Never make the answers reachable by the
   model under test.
7. **Record the round** — `python3 ../scripts/attempts_ledger.py record --round <n> ...`.
   Reverts included. The script refuses to record round *n* while round *n−1* is missing, so a
   pass cannot skip the write and go on to the next round; that ordering is the whole enforcement.
   Every row carries `base_commit`, the state it was measured against: a row from round 1 does
   not get to refuse round 3's patch after round 2 moved the surface, and the script reports such a
   row as stale rather than applying it.

## The split does not protect the rubric

Step 5 keeps a patch when train and test both rise, and reverts one that lifts only train. That
protects against fitting the visible cases. **It does not protect against relaxing the thing the
cases are scored by**, because a relaxed rubric lifts train *and* test together and reads as a clean
win.

This is not hypothetical. In the upstream guidance behind `SOURCES.md`, adding a category definition
flipped a verdict that had passed — the category did not find a new defect, it widened what counted
as one. Applied here: a guideline edit that changes which findings an assertion accepts raises the
score for the same underlying review quality, and every gate above will keep it.

So the rubric is held separate from the split. A patch touching a **check** — an assertion, an
expected-output block, a threshold, an axis definition, a severity rule — is graded against the
whole corpus, not a split, and a corpus-wide rise caused by a relaxed check is a **revert**, not a
keep. The two are told apart by step 3: a patch that only adds detection is judged on the split; a
patch that changes what counts as detection is judged on everything, because only everything shows
what it now counts.

## After the loop touches the rubric: the cheap check

A rubric change can be tested far more cheaply than a rubric-neutral one, because it does not need a
new review to exist. The review already happened; only the scoring changed.

**Re-grade the stored reviews against the current assertions.** For each `review.md` already on disk,
run the grader over the same text with the new assertion set. That costs one grader call per stored
review and **zero review-generation calls** — the expensive half of a rollout is skipped entirely —
and it is exact for what it covers: if the review text is unchanged, every delta it shows is caused by
the rubric, which is precisely the thing under test.

State the boundary of what it proves, because it is narrow and the reader must not over-read it:

- **It detects** rubric and assertion drift, and any regression the edit caused in verdicts that
  already exist.
- **It cannot detect** anything requiring a fresh review — a guideline edit that changes what the
  reviewer *would have said* is invisible here, because no new review is produced. That half still
  needs a real run, and with the corpus this tree cannot afford, it stays unproven.

Report the re-graded count and the number of deltas. A re-grade that changes nothing is a result —
it means the rubric edit was inert on everything already observed, which is worth knowing before
spending a rollout on it.

## When it stalls

After two or three rounds with no movement above noise, make **no edit**. Read every
remaining train failure and bucket them by cause, then report the buckets. Usually:

- **Content present, prior shape winning.** The rule exists but the model writes what it
  was trained to write. Fix with a table or example near the top steering from the
  remembered form to the current one.
- **Never improves despite an obvious content gap.** The task or its grader is wrong.
  Fix the task, per `eval-design.md`. Do not keep editing the skill for a broken fixture.
- **Harness error**, or genuine run-to-run variance.
- **A limit the surface cannot reach.** Some constraints are not tunable by instruction at all — a
  capability boundary, an environment fact, a rate limit. The upstream guidance behind `SOURCES.md`
  records one: a moderation behaviour that holds *regardless of the prompt used*, which is a
  guardrail that cannot be relaxed by editing text. When a bucket is one of these, **stop retrying it**.
  Report it as a fixed constraint on the surface, name what would have to change for it to move, and
  spend the remaining rounds on the buckets that are reachable. Retrying an untunable failure spends
  rounds and manufactures the appearance of progress.

Only legitimate failures return to hillclimbing, and a failure in an untunable bucket never does.

## Reporting

Report the test score against the baseline, with confidence intervals. If the gain is
within noise, say so plainly and recommend against adopting. Leave the skill at the
version that scored best on the **test** split, never the best train score.