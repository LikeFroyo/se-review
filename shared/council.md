# The council — an orchestrator's only peer reviewer

Load only when the `--council` flag is on **and** a trigger below has fired. With the flag off,
none of this exists and the orchestrator decides alone, as it always has.

## Why this exists, narrowly

The orchestrator is the only participant in a review that has read every package. Every other agent
sees one slice and has peers; the orchestrator sees everything and has none. Its judgement calls —
how to cut the work, whether a contradiction is real, what the intent actually is when two sources
disagree, whether a finding is a defect or a design choice — are therefore the least checked
decisions in the whole system, and they are the ones everything else inherits.

A council is **not** a second review pass. It never reviews product code; the fan-out does that, and
duplicating it would spend calls to re-read what has already been read. The council reviews
**the orchestrator's own unverified judgements**, and nothing else.

## When to convene

Convene on a trigger, not on a feeling. Each is observable.

| # | Trigger |
|---|---|
| **T1** | The orchestrator must decide something, and the answer is not readable from the tree. |
| **T2** | The orchestrator caught itself hedging — "probably", "it seems", "likely", "I would assume". |
| **T3** | Two subagents returned conflicting verdicts and reading the code did not resolve it. |
| **T4** | A recommendation is destructive or irreversible: deleting code, changing an access-control or cryptographic posture, disabling a check. |
| **T5** | A Critical exists and the orchestrator is not certain it is real. |
| **T6** | Something the rest of the run depends on is Low confidence. |
| **T7** | The question cannot be answered from the repository at all. |

## When not to convene

The flag is on. These still do not trigger it, and saying so out loud is part of the rule.

- **The code answers it.** If evidence settles the question, evidence wins and no council is spent.
- **The skill already specifies it.** A rule in this repository is not a judgement call.
- **Style, formatting, taste.** Not this skill's business.
- **A settled decision.** Re-litigating a decision already made with evidence is noise.
- **Routine adjudication.** T3 only. Resolving a disagreement *from the code* is the orchestrator's
  job and needs no council.

Cost is the reason for the whole non-list. A council on every decision costs several times the
review it is attached to, and buys nothing when the answer was already evident.

## How to convene

1. **Frame the question precisely.** One question, answerable, with the evidence attached.
2. **Withhold the orchestrator's conclusion.** Members receive the question, the evidence, and the
   constraints. They do **not** receive the proposed answer, the severity, or any argument for it.
   A member that reads the conclusion first confirms rather than reviews — the same contamination
   `project-tree/shared/deliberate.md` forbids in the other direction.
3. **Prefer different models.** Identical models share blind spots, and correlated errors read as
   agreement. If the harness offers several, use several. If it offers one, say so in the record
   rather than implying independence you did not have.
4. **Three to five members.** Below three there is no majority; above five the cost outruns the
   value and members start restating each other.
5. **One round.** Re-convene only when new evidence appears, not because the first answer was
   unsatisfying.

## How to decide

**The council is not a vote.** Counting raised hands converts disagreement into false confidence,
which is the failure this mechanism exists to prevent. Three rules, in order:

1. **A fatal flaw blocks.** If any member identifies a way the decision causes the outcome it is
   meant to prevent, the orchestrator must either refute it with evidence or downgrade the
   decision to `unverified` and report the cap. Silence is not available; neither is proceeding
   while the flaw stands unexplained.
2. **Agreement raises the bar, it does not decide.** If members converge, the orchestrator still has
   to show its work. Convergence is a reason to proceed, never a substitute for evidence — and three
   members agreeing with each other is weaker evidence than one member disagreeing for a stated
   reason.
3. **The orchestrator does not get a weighted vote.** Its own answer is one position. Where members
   converge against it, that is information about the orchestrator, not about the code.

**On deadlock.** Unresolved disagreement is a reportable result, not something to split. State the
disagreement in one line, take the branch that damages less if it is wrong, and cap the decision at
Info with the conflict named. "Two members read it the other way" is a more useful output than a
majority.

## What a council returns

Positions, not a score. Each with the evidence it rests on, and each reachable by someone else.

```
council: <question> · <n> members · <n> distinct models · converged: yes|no
- <member> — <position> — <evidence>
- <member> — <fatal flaw identified> — <evidence> — BLOCKS unless refuted
- <member> — could not determine — <what would settle it>
```

Record the model count. **"4 members, 1 model" is a different claim from "4 members, 4 models"** and
must not be reported as the same evidence.

## Recording in the report

One line under the run header, plus the block above when a council ran. When the flag is on and no
trigger fired, one line saying so — a flag that is silently never used is indistinguishable from a
flag that does nothing.

```
Council: enabled · convened <n>× · converged <n> · blocked <n> · members 4 across 4 models
```

## Limits

- **The council is not independent of what it is shown.** It reviews the orchestrator's judgement
  with the orchestrator's evidence. It catches a bad inference; it cannot catch a frame that never
  occurred to either.
- **It does not scale the fan-out.** Cutting work is still the orchestrator's call; a council may
  review that cut, not perform it.
- **It cannot restore what the flag was off for.** With `--council` unset, every T1–T7 decision
  above stands on the orchestrator alone. That is the default, and it is deliberate.