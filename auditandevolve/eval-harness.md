# Phase 4 — Eval Harness

Prove each upserted guideline with evals and report before/after. Read this file only during Phase 4.

## Input

- Phase 2 edits that passed Phase 3.

## Procedure

1. **Add a fixture per upserted guideline.** Plant the defect the guideline catches in `../evals/fixtures/<name>.py` (or `.json` for manifests). Keep fixtures minimal: the defect plus just enough surrounding code to review. Add a clean control only when the guideline risks false positives.

   **Admit the fixture on an observation, not on an assertion.** Before the eval entry exists,
   show the fixture two ways *by running it*, not by reading it: the unmutated file passes the
   structural gate clean, and the planted defect demonstrably changes what the file does.
   Record both results beside the eval.

   A fixture that fails the first has a second reason to fail, so no miss can be attributed to
   the guideline. A fixture that fails the second does not exhibit its defect, so its assertions
   are claims about nothing. `evals/README.md` records three first attempts that were corrected
   rather than shipped for exactly this reason — a tax calculation that was already correct, and
   a counter that lost no updates at any setting tried. That practice is real; it is stated here
   because **Phase 4 never loads `evals/README.md`**, and a rule in a file the phase does not
   read is not a rule the phase follows.

   The demonstration is what makes a fixture admissible; it does not make the fixture evidence.
   Nothing downstream substitutes for it.
2. **Append the eval entry** to `../evals/evals.json` following the existing schema: next sequential `id`, `prompt` (`Review evals/fixtures/<name>.py`), `files`, `expected_output` (finding count, severity, axis, fix, header pattern), and atomic binary `assertions` (single pass/fail condition each, mirroring the style and count of neighboring entries).
3. **Run before.** Review the fixture with the guideline change reverted (stash the Phase 2 edit) and grade against the new assertions. Record `passed/total`. A graded run writes `review.md`, `events.jsonl`, `grading.json` with per-assertion evidence, and `timing.json` (`duration_ms`, `output_chars`). A run the plumbing gate rejects writes `review.md` and `plumbing.json` only — no verdict, no timing — so a denied tool can never surface as a slow but legitimate review.
4. **Run after.** Restore the edit, review again, grade against the same assertions. Record `passed/total`.
5. **Grade with evidence, then aggregate.** Grade per `../evals/README.md`: PASS requires quoted evidence, not intent. Run `python ../scripts/grade_evals.py` for the with/without delta plus timing means, and `python ../scripts/eval_diagnostics.py --determinism N` for the flip rate. A run without a review body writes `plumbing.json` and is excluded, never graded as zero.
6. **Analyze patterns.** Remove assertions that pass in both arms (no signal); fix tasks that fail in both (broken task or grader, never a skill edit); study skill-only passes for the rule that made the difference. Before tightening an instruction on the strength of one disagreement, check it is a real signal and not the run-to-run noise `eval-design.md` warns about — this harness runs each eval once per arm, so a single flip proves nothing.
7. **Human review.** Read the before and after reviews and record per-eval `feedback.json` — specific, actionable complaints, or `{}` when clean. Reserve assertions for checkable claims; style and point-missing go in feedback. This file is written by hand and **no script reads or validates it**, so it is advice, not a gate: a missing or empty `feedback.json` is not a failure, and nothing downstream changes because of its contents.
8. **Update the suite.** Extend the `../evals/README.md` matrix row and totals, then run `python ../scripts/validate_skill.py` and `python ../scripts/grade_evals.py` from the skill root. Both must pass.

## Delta report

Three states, and the third is the one this tree is most likely to need and least likely to write.

```markdown
## Eval delta
- Fixture: `evals/fixtures/<name>.py` → eval <id> (<n> assertions)
- Before: <passed>/<total> (guideline absent — defect missed)
- After: <passed>/<total> (guideline present — defect caught at <severity>/<axis>)
- Suite: <old total> → <new total> assertions · validator PASS · grader PASS
- Diagnostics: headroom <rate>% · trigger <rate>% · flip <n>/<m> · timing <ms mean>
```

A zero or negative delta sends the guideline back to Phase 2, and the two causes are not
interchangeable, so decide which one you are looking at before touching anything:

- **The guideline does not catch the defect.** The measurement is sound and the rubric is
  incomplete. Fix the guideline, in `domains/`. This is the work Phase 2 exists to do.
- **The fixture does not exhibit the defect.** The measurement is invalid, and *editing the
  fixture is not the repair* — `SKILL.md § The measurement boundary` puts fixtures and
  assertions off limits precisely because a fixture adjusted until the run passes asserts a
  false claim and spends a run doing it. Demonstrate the defect by running the unmutated
  fixture first (step 1). If it will not exhibit, **write a new fixture that does**, or drop
  the finding. Do not adjust the existing one.

Two auditors found this paragraph contradicting the boundary: it said "fix one of the two"
while the boundary forbade one of the two, and left the loop to decide which rule governs.

### When the delta was not produced

The block above assumes a delta exists. With the corpus at 12 of 99 measurable it frequently does
not, and the report has exactly one honest rendering for that:

```markdown
## Eval delta
- NOT MEASURED — <reason: no capacity | no baseline | stale assertions | no replicate>
- Guideline landed: no. Unmeasured, per `SKILL.md § The regression gate`
```

**Never print `+0` for a delta that was not computed.** `+0` is a claim: measured, and nothing
changed. The report schema's Phase 4 slot previously had no rendering for "not measured", so the
cheapest path through the loop's own rules was to land a guideline, skip Phase 4 on a closed
quota, and print `+0` — a number indistinguishable from a result. An oracle reviewing this design
found that path and it is now closed: the slot is `delta`, `not-measured`, or `skipped`, and
`+0` means what it says.

A guideline whose delta was not produced has not been shown to help and has not been shown to
hurt. Those are different states and the report has to be able to tell them, because a reader
who sees `+0` will conclude the first thing that is true and stop reading.