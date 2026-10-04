# Anti-pattern gate — what a finding may propose

Load before grading, on every run, unconditionally.

Some conclusions are wrong often enough that proposing them costs more than the finding is
worth. But observe this carefully: every one of them constrains **what a finding may propose**,
not **what an agent may observe**. That asymmetry is why this gate needs no stored list of past
mistakes — it is a lint over proposals, run fresh each time.

The safety property: **this pass never removes a finding whose defect claim is supported.** It
reclassifies, forces sourcing, deletes a *proposal*, or redirects an *attribution*. Observations
survive it untouched, which is why it can run on every run with zero state.

## The seven

| # | If the finding proposes… | Then |
|---|---|---|
| **L1** | removing one of two implementations, **without** naming a rule both must satisfy | Ask what rule each encodes. If they encode *different* rules this is not redundancy → reclassify as an Info observation. |
| **L2** | deleting a value because it is always the same constant | Ask whether that constant is *correct* for the case it covers. Correct-but-degenerate is a representation choice → Info. |
| **L3** | supplying a derivation for a value that has none | **Delete the proposal.** Re-file as `unmeasured`. A guess that acquires a derivation is undetectable afterwards. |
| **L4** | asserting that an externally-sourced constant or limit is wrong | Requires a **primary source**, not recollection. Without one → drop. With one it is a sourced finding, and never a "correction": a correction rewrites every record already produced. |
| **L5** | generalising from a single observed run, or averaging over a truncated statistic | Ask what bounds the number. Truncated by the very thing being judged → the finding is about the **method**, not the value. |
| **L6** | adding a check, rule, branch, or threshold where a symptom surfaces | Require the root cause. If none can be named, the check becomes a **proposal**, not a fix. |
| **L7** | regenerating a derived artefact — output, recorded value, digest, snapshot — that no longer matches | **Attribute the behaviour change first.** A moved digest is a behaviour change; regeneration is never the first move. |

## Why a procedure beats a stored list

A list of past mistakes contains only the mistakes someone remembered to write down. This gate
is generated from the shape of the proposal, so it also catches the sibling nobody thought to
record — which is the whole point of hunting a defect class rather than an instance.

Where a project *has* recorded its own conclusions, they arrive as project-authored evidence:
rank 5, capped at Low confidence, re-verified at the current tree, and disagreement reported as
drift. They inform the probe in `shared/deliberate.md`; they never decide it.

## Scope

This gate governs **this skill's own output**. A constraint on how findings are *proposed* is
the skill's business, not the project's. It never suppresses an observation and never grades —
`shared/deliberate.md` does the grading, and it does so after.

## Neutrality

Names used here: none. The gate is a lint over the shape of a written proposal, so it needs no
technology to evaluate. "A primary source" is required without naming a class of source,
registry, or publication — what counts as primary is the project's domain, not this skill's.