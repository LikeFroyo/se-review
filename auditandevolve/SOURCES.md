# Upstream sources for the evolution path

This file is the evolution path's citation list, and it is the only place in this repository where an
**instruction file** names an upstream source. (Two non-instruction files also contain such names, by
necessity: the validator's blocklist and its test, because a blocklist has to spell out what it
forbids.) Guidelines state the check and its threshold; the citation is how the finding was justified
at research time, not something a reviewer needs at review time.

## Why a source list exists here at all

Every other surface in this tree is vendor-free, and that is a rule about *instruction* files: a check
that names a tool teaches the reader that the tool is the subject. This file is not an instruction
file — it is provenance for the evolution path's design, which is the one part of the tree whose
correctness is an empirical question rather than a judgement one. A reviewer grading product code
never reads it. Removing it would not change a single finding this skill produces.

`scripts/validate_skill.py` enforces the boundary: a vendor token is excused **only** when it falls
inside the characters of a URL beginning with a declared prefix in `REFERENCE_URL_PREFIXES`. The same
word in the same file, one sentence away, is still an error. So the links live here and the prose does
not.

## Guidance followed

### Evaluation design and hillclimbing

- `https://claude.dev/blog/automating-eval-design-and-hillclimbing/`
- `https://github.com/anthropics/skills/tree/main/skills/claude-api`

The keep/revert rule, the noise-before-round-one gate, one change per round, the train/test split,
the stall-and-bucket step, and the prohibition on pasting failure content into a patch are all taken
from here. `hillclimb.md` is the translation; the translation is stack-blind and the source is not,
which is the whole reason the translation exists.

Load-bearing details this tree adopted, each with the failure mode it prevents:

| Adopted | Prevents |
|---|---|
| Headroom must exist at the frontier | A saturated eval cannot show any change |
| Rejects must be written as checkable claims, never a 1-to-5 scale | An unverifiable grader |
| Judge must not be the model under test | Grading one's own homework |
| Adversarial sampling: a case is included because a human judged it hard | The corpus becomes one model's failure fingerprint |
| Noise floor compared against the smallest actionable gain before round one | Adopting a delta that is chance |
| Never paste failure content into the patch | Fixing the instance instead of the cause |

### Skill authoring

- `https://github.com/anthropics/skills/tree/main/skills/skill-creator`

Progressive disclosure and token budgets. The reason this path loads one phase file at a time rather
than all five is here.

### Platform guidance

- `https://platform.claude.com/docs/en/about-claude/use-case-guides/overview`

Use-case guides. Their value to this path was mostly negative and worth recording: graded risk rather
than a binary verdict, guardrails checked **both when a change is staged and again when it is applied**,
and approval authority deliberately held outside the conversation being judged.

## Research this path is built against

- `https://arxiv.org/abs/2609.26457`

On recursive self-improvement: when an agent's own code is the object of optimisation, each accepted
rewrite becomes the agent the next round edits. Three results from it shaped `SKILL.md`'s measurement
boundary, and they are the reason that boundary is stated as a prohibition rather than a preference:

1. **The loop selects on hidden evaluations.** Improvement is measured on a set the loop does not
   train against, so a change that merely fits the visible set does not survive selection.
2. **Generalisation is the finding, not the score.** The gains transferred to held-out task families,
   including ones out of distribution from what the loop optimised.
3. **The loop drifted less reward-hacking without being asked to.** Reward hacking fell during a run
   that never optimised for it. A self-improving loop's *unrequested* properties are therefore worth
   measuring, and an unmeasured one may be moving the wrong way.

The second point is the direct cause of the whole-corpus check in `hillclimb.md`: a split that rises
while the rest of the corpus is untested is the shape of an overfit gain.

## Source classes this path admits

`research-sources.md` defines the admission gate and disposition vocabulary for the **published
engineering research** class — the material catalogued in the three sections above. Two things
worth recording about how it was admitted:

- **No change to the reference-prefix list was needed.** The frontier material in this tree's
  citations sits under prefixes already declared, so admitting a new source class was not blocked
  on editing the validator. Had it been, that edit would be a human step by design — the boundary
  makes a change to the instrument a finding, not a task — and a recurring human step is visible
  where a recurring one hidden behind a script is not.
- **No score.** The class emits a disposition from a closed set and no number, because no
  instrument here can produce one and a number in a column headed `value` would be cited as though
  something had been measured. The report line says so every pass.
