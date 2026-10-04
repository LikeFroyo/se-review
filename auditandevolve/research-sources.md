# Source class — published engineering research

Read this file **only** when Phase 1 selects this source class. It is the class's admission gate,
disposition vocabulary and report line; `deep-research.md` holds the pass structure and points here.

## What this class is

Authoritative research on how to build, grade, sample and hold out an evaluation, published by
parties that run their own systems at scale. The materials that motivated it are catalogued in
`SOURCES.md` as URLs.

This is a **source class**, not a phase. Phase 1 already surveys authoritative sources, records a
source per finding, converts research into checks, grades, and caps. The only new thing here is
*what kind of source is worth the phase's budget when a source class's whole output is unmeasured*.

## Four predicates. All four, or the item does not advance.

**A1 · Grounded, and the obligation is the source's.**
The item's obligation strength is stated by the source, and the source is not your own knowledge.
`../project-tree/shared/source-resolution.md` T5: *"your own prior knowledge → **Never a basis for a
finding.** Use it to find a source, then go to the source."* A source that **asserts** where it
needed to **require** admits at most an Info note. *Fails → `ungrounded`.*

**A2 · Not already covered, shown by a receipt you can replay.**
`Already covered: no` is not admissible on its own — the `yes` branch has an anchor and the `no`
branch had nothing, so asserting absence was free. Every item instead carries the search that
established it:

```
**Receipt:** `<glob>::<regex>` → <n> hits · <anchor, or none>
```

`scripts/research_ledger.py` re-runs the receipt against the tree and **refuses any row whose
receipt does not reproduce**. That is the difference between a gate and a prompt, and it costs no
model calls.

The receipt is evaluated by the script itself and shells out to nothing. That was not the first
design: the first version shelled out to a search tool, and its first test run failed because that
tool was not installed. A gate that inherits a dependency from the environment is a gate whose
behaviour depends on where it runs, and a replay that sometimes cannot run is not a replay.

A receipt whose terms come from your own paraphrase is void —
`../shared/severity-and-rules.md § Ground rules`: *"map the claim's terms onto identifiers that
surface itself uses. If no such term exists, say the corpus has no relevant vocabulary and stop."*
A zero-hit receipt is recorded, and the pass prints how many advancing rows rest on one: a search
that matched nothing is consistent both with absence and with a pattern that cannot fire.

*Fails with n > 0 → `covered`, and the receipt must show those hits. Zero hits → advances, tagged
`zero-hit`. **Both contradictions are refused:** `covered` with a zero-hit receipt, and `advances`
with a receipt that finds something.*

**A3 · It changes a judgement, not a class.**
**This is the admission criterion that matters, and it was derived from this tree's own
measurement rather than invented.** An independent blind re-measurement found a competent fresh
reviewer, given **half** the corpus, detects **23 of 24 defects (95.8%)** unaided against 24/24
with the skill — **+4.2 points**. Severity correctness is where the guidelines earn their keep:
**+33.3 points**. So a source item that adds a defect class the reviewer already detects unaided is
**not a coverage gain. It is carrying cost.**

Therefore the question is not *"is this new?"* It is:

> **Does this change a severity judgement, a threshold, or a boundary?**

- sharpens a threshold — when this becomes Critical rather than Major → `advances`
- changes what counts as the same defect — a scope or boundary condition → `advances`, and it is a
  **check-touching** change, which `hillclimb.md` grades against the whole corpus rather than a
  split. That corpus does not exist at the needed scale, so such an item is **deferred with a named
  blocker**, not advanced.
- adds a defect class → `known`, and the action is `delete-candidate`

*Fails → `known`.*

**A4 · Stack-blind by substitution.**
Replace every proper noun, product, protocol and version with a class word. If a trigger a reader
could evaluate survives, it passes. If it survives only as *"check their practice"*, it is
`out-of-scope` — it names a subject rather than a trigger.

**Methodology is not a check.** Material about *how to build or grade an evaluation* is not a
defect class and never becomes a guideline. It has two destinations: it changes `auditandevolve`'s
own procedure — where the gate is Phase 3 and **a human lands it** — or it is an Info note.

## The disposition vocabulary

Closed, unordered, seven tokens. No number is attached to any of them, and no number may be.

A disposition states **what happened to this item in this tree**, not how good it was. That
distinction is the whole design: this tree refuses any objective with no metric
(`hillclimb.md § What each objective can actually be measured by`), and a relevance score would be
a number whose only producer is a feeling, sitting in a column headed `value` that every later
reader cites as though something had been measured.

| token | meaning | advances? | requires |
|---|---|---|---|
| `advances` | check-shaped, grounded, not covered, judgement-changing | yes, to Phase 2 | receipt (0 hits) |
| `covered` | the tree already states it at a named line | no | receipt (n>0) + `file:line` + **an action** |
| `known` | real, but the model already has it | no — `delete-candidate` | receipt + action |
| `ungrounded` | asserts rather than requires, or rests on prior knowledge | no | basis |
| `not-checkable` | cannot become a reviewer check | no | — |
| `out-of-scope` | fails the substitution test | no | — |
| `could-not-fetch` | the source was unreachable | no | basis |

**`could-not-fetch` is a token in this table, not an absence from it.** If an unreachable source
were recorded as a rejection, the ledger would be biased toward whatever the fetch layer failed on
and it would look like a measured judgement. `could-not-fetch` and "found nothing useful" must never
render alike — the same pair as `assessed` with no findings and `could-not-assess` in
`../shared/domain-fanout.md`.

## Every `covered` row carries an action, and the default is deletion

`covered` means an independent authority now states what a guideline states. That is evidence the
model already has it, and `skill-adherence.md` item 6 — *"omits what the model already knows"* —
makes deletion the correct action. So a `covered` row is a **deletion candidate pointed at a line**,
and the ledger refuses a `covered` row that carries no action.

**The default is deletion and retention must name what the model would get wrong.** This is
deliberately tilted, and it is deliberately not absolute: a brake that only ratchets one way deletes
the rubric until nothing is left, and `../shared/severity-and-rules.md § Leanness override` already
grades an unearned capability **CRITICAL**. The obligation is to **decide**, with the tilt. An
instruction file that fires rarely is **not** dead.

## Rejecting a source before any item is read

| reject | reason |
|---|---|
| `unreachable` | recorded as `could-not-fetch`, never as unhelpful. See `source-resolution.md`: *"Where sources cannot be reached, record the gap as unknown, never as compliant."* |
| `secondary` | a summary of a primary artefact. The tree would admit the misreport. |
| `discharged` | the tree already states its content at a named line |
| `no-date` | no publication or version date, so it cannot be re-evaluated later — *"a conformance baseline without a date cannot be re-evaluated later, because the rules move underneath it"* |

## Never read the answer key

A research pass asks "what does this rubric lack", and the corpus is a labelled inventory of what it
has — `../../evals/README.md` names, per guideline, the exact planted defect and the observed number.
That is the key in prose.

**Do not read `evals/evals.json`, `evals/iteration-*/`, or the per-guideline fixture tables in
`evals/README.md`.** Coverage counts come from the gap register — `../../docs/named-gaps.md` G1–G3
carry exactly those numbers and carry no key. That is the `source-resolution.md` move applied to the
corpus: **count it from the register, never open the key.**

Coverage therefore means *a guideline states it*, searched over `domains/**/guidelines/*.md`,
`../shared/axis-codes.md` and the `sub-leaf.md` tables. A class the corpus tests but no guideline
states is a genuine gap and is what this pass is for.

## The report line

```
## Research pass
sources examined: <n> · receipts replayed: <n>/<n> reproduced · anchors resolved: <n>/<n>
dispositions: advances <n> · covered <n> · known <n> · ungrounded <n> ·
 not-checkable <n> · out-of-scope <n> · could-not-fetch <n>
reconciled: yes · zero-hit receipts among advances: <n> · deletion candidates: <n>

value verdict: NOT MEASURED. No instrument in this tree scores source relevance
(`evals/README.md`: 12 of 99 fixtures measurable; gap register G2: noise floor zero).
The numbers above describe this pass, not the sources' worth.
```

**A disposition count is not a score, and neither is a rate.** The one derived figure is printed
with its denominator every time: *discharge rate* = `covered / (covered + advances)`, used only to
decide whether this source class is exhausted. It is a property of **this tree at this commit** and
is not comparable across trees — a tree that has grown will always discharge more.