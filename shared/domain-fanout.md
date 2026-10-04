# Domain fan-out — dividing a defect review

Load from Phase 2 when scope exceeds the serial ceiling below. Below it, stay
serial: one agent holding thirty files keeps a fraction of the picture, and the
cost of a fan-out is real.

## The serial ceiling

**Fan out when scope exceeds 30 files or 5,000 lines of project-authored code.**
Those numbers come from the same reasoning `project-tree/shared/fanout.md` states
for capability slicing: a reader holding three files keeps the invariant in mind
and notices the transition that does not exist; handed thirty, they keep a
fraction, and a missing edge is invisible to them.

Below the ceiling, serial is *better*, not merely cheaper. One context sees the
cross-file interactions that no slice does, and the run costs one agent instead
of five. Do not fan out a small review to look thorough.

State in the report which mode ran. A reader cannot otherwise tell a five-agent
review of a small tree from a serial one.

## Discovery fans out. Severity never does.

**Agents return findings with evidence and a proposed severity. The orchestrator
assigns every severity itself, serially, in Phase 3.**

This is the load-bearing decision, and it is the one place this design departs
from the obvious fan-out. Five reviewers calibrating severity independently
would produce five different meanings of Major, and the scoring synthesis is
arithmetic — a mean of incomparable numbers, and caps applied to units nobody
defined. That risk is not mitigated here; it is made impossible by removing
severity from the agents' authority entirely.

A proposed severity is a *claim about blast radius* and is treated as evidence,
never as a decision. The orchestrator may accept it, overrule it, or split the
difference, and Phase 3 runs on the orchestrator's own reading regardless.

The work that parallelises is the expensive part: reading code. The work that
must not parallelise is the judgement that decides what reading is *worth*.

## Axes

Intent's axes are capability, systemic concern, and boundary. Defect review needs
different ones, because a domain is already a rubric, a slice, and a score.

| Axis | Assignment | Why |
|---|---|---|
| **1 — Per active domain** | One agent per discovered domain: correctness, maintainability, operations, interoperability, leanness | Each is a natural slice that already carries its own `leaf.md`, sub-domains, axis codes, and deduction table. No new partition is invented. |
| **2 — Interaction** | Retained by the orchestrator | Phase 2 already requires checking that files which are each correct alone are broken together. That is a whole-tree property and no per-domain agent sees it. |
| **3 — Domain boundary** | One agent where two domains share a file or symbol | The expensive defects live where two individually-reviewed domains meet, and each has a structural reason not to look: it is not that domain's concern. |

Axis 2 is why this is never a single-axis fan-out. A per-domain partition that
omits interaction checking reads as thorough and misses the class it looked most
hard for.

**The gate runs first and alone.** If leanness proves dead or unearned code, that
is an immediate Critical blocker — record it before spending on the pillars. A
fan-out that opens all five domains at once has spent four agents' budget before
learning the run is already gated.

## The subagent brief

Same fixed shape as `project-tree/shared/fanout.md`, with the intent-specific
fields replaced. A brief missing any section produces a return the orchestrator
cannot use.

```
SLICE:        <domain> · <exact paths, by symbol where possible>
NOT YOURS:    <the paths and domains explicitly excluded — name them>
GUIDELINES:   <the sub-domain files to apply, by name> — apply these, not your priors
BOUNDARIES:   <for a security slice: the crossings inside it, as
              `entry: untrusted|trusted → what is validated there`. Omit for a
              non-security slice. A security brief without this cannot be graded:
              a rule referring to a boundary nobody located cannot be applied.>
ADVERSE:      <catalogue shapes this domain's code is shaped like>
PROPOSE:      shape · scope · site:line · evidence · consequence · proposed severity.
              Severity is a proposal. The orchestrator assigns the real one.
RETURN:       per finding, plus `aligned: <what you checked and found correct>`,
              plus `considered: <n> · <classes, or none>` — see the gap pass below —
              an agent that reports only defects has not shown where it looked.
LIMIT:        anything you could not verify, and why
```

Four clauses are non-negotiable and go in every brief:

- **Do not read this skill, its sibling files, or the evaluation corpus.** Those
  contain worked examples of these defect classes. An agent that reads them
  reviews from the answer key, and the result is worthless. A recursive search
  that reaches them is a contaminated run: discard it and re-dispatch.
- **Never receive a defence.** An agent that reads *why* a design is intentional
  and then reviews that design is confirming, not finding. Justification never
  crosses into a brief.
- **Do not report style, formatting, or preference.** Grade against a cited
  guideline or return nothing.
- **A brief carries what to read, never what has already been said about it.**
  Paths and short excerpts are the whole payload. A summary of what a previous
  run concluded, or a prior verdict's reasoning, is how a defence or an answer
  key crosses into a slice — and an agent handed the conclusion is confirming,
  not finding.
- **Do not fix anything, and do not assign severity.** You propose it. The
  orchestrator decides it.

## Dispatch preflight

Check mechanically, before anything is dispatched:

- [ ] Scope actually exceeds the ceiling, or the fan-out is not running at all.
- [ ] The gate domain has already run alone.
- [ ] No two domain agents claim the same path, except a named boundary agent
      citing both sides.
- [ ] No brief carries a conclusion, severity, class, or justification for any
      candidate — a proposed severity is a claim, and a brief asserting one is a
      conclusion.
- [ ] Every `GUIDELINES` row cites a sub-domain file that exists.
- [ ] Every brief names what it excludes.
- [ ] The interaction agent's paths are the union of the domain agents' paths.
- [ ] No brief names another agent's findings, or the count of findings expected.
- [ ] Every security brief carries a `BOUNDARIES` block naming each crossing in its slice, and no
      other brief does. A security slice dispatched without one is measuring a shape rather than a
      path, which is the failure this domain exists to prevent.
- [ ] No brief states whether a crossing is safe. `untrusted` and what is validated are the whole
      payload; a brief that says "this boundary is fine" is handing over a conclusion.

## Orchestrator duties

With `--council` set, triggers T1, T3 and T6 of `council.md` apply to duties 2, 3
and 5. With the flag off — the default — every call here stands alone.

1. **Assign every severity.** Phase 3 runs on your own reading. A returned
   severity is input, never a decision, and two agents' proposals for one root
   cause do not average — they collapse in Phase 5 under the owner rule.
2. **Run the interaction pass yourself.** This is the axis no agent was given.
3. **Collapse root causes.** One broken rule found from four domains is one
   finding with an occurrence count, not four findings.
4. **Enforce evidence.** A finding returned without a cited site is downgraded to
   Info and reported as unverified, whatever the agent proposed.

   **Every agent returns one terminal exit token, from a closed set, and the set
   includes the negative results.** An agent that returns prose cannot be told apart
   from one that ran out of steam, so its contract ends in a single word:

   | token | meaning |
   |---|---|
   | `assessed` | the surface was covered and findings (possibly none) are attached |
   | `fits-no-axis` | defects found that match no registered code — the G9 population, made countable |
   | `could-not-assess` | coverage was not established; **not** a clean result |
   | `out-of-scope` | the boundary inventory placed this surface elsewhere |

   `could-not-assess` and `assessed` with no findings are the pair that must never
   render alike: one is a pass and the other is an unexercised check. An agent that
   returns `could-not-assess` has cap-limited everything it would otherwise have
   reported, and the reason travels with it. `fits-no-axis` exists so the
   no-axis population is a count rather than a silence — a reserved code with no
   periodic review is a defect nobody can size, and it cannot be sized if nothing
   records its occurrences.

   **Periodic review of the no-axis population.** The count is only worth keeping if
   something reads it, so the reading is specified here rather than left to whoever
   notices a number nobody has looked at.

   *When.* Before any round of quality hillclimbing, and after any change to
   `shared/axis-codes.md`. A code added to the registry absorbs findings that were
   previously uncoded, so the population is not stable across a registry edit and a
   reading taken before one does not describe the corpus after it.

   *What counts.* Findings whose reported `fits-no-axis` is non-zero, grouped by the
   emitting domain. A domain emitting uncoded findings is not necessarily wrong — it may
   have a real defect the registry does not yet name.

   *Two dispositions, and only these two.* **Promote** — a recurring shape that belongs
   in the registry, added with a domain and a severity default, then the population
   re-read to confirm it fell. **Widen an existing code** — the shape was covered but a
   boundary was drawn too narrowly, so the boundary moves rather than the registry
   growing. A shape fitting neither is not promoted for appearing often; frequency is
   not evidence that a code is missing.

   *What must never happen.* Recording the count without reading it. A population
   measured every round and acted on never is worse than one never measured, because it
   looks maintained.

   **One gap pass, and only where there is a gap to reason about.** If you are about to return
   `assessed` with no findings and no `fits-no-axis`, you have returned *nothing* — and nothing is
   indistinguishable between a clean slice and a recogniser that never fired. So before you return,
   reason **once** about this axis from what you know of it beyond the guidelines named above, and
   return `considered: <n>` carrying the defect classes you weighed, or `none`.

   Three properties are what make this safe where free-form recall would not be:

   - **A class is not a finding.** No site, no severity, no deduction. It enters no term of the
     grade and cannot trip the Critical cap. A class becomes a finding only by naming a `file:line`
     and a failure scenario — and then it is graded on its evidence like anything else.
   - **It is conditional, so it costs nothing where there is nothing to find.** It fires on the
     silent case only, which is precisely the case where the guidelines demonstrably did not fire.
     Cost scales with the gap, not with the corpus.
   - **`none` is the expected answer, and it is a result.** Printed at every value including zero,
     because a field printed only when it binds teaches the reader that nothing means nothing.

   Each class you weighed and could not ground is also a `fits-no-axis` observation, so this pass
   feeds the one countable population rather than opening a second one.
5. **Own the score.** Agents return findings; you compute the deduction, the
   domain score, the mean, and both caps. No agent returns a score.
6. **Own the boundary inventory.** The inventory is one artefact with one owner, produced once by
   the trust-boundaries slice and consumed by the other three. Two agents each deriving their own
   boundaries produce two incompatible maps and every downstream finding becomes arguable. When the
   inventory is incomplete, `unmapped` is what carries that — never a silent pass.
7. **Report coverage honestly.** `Covered:` in the header names the denominator
   and the mode. A fan-out that returned five partial answers has not covered the
   tree, and the header must not read as though it did.

## Anti-patterns

- **The calibrated army.** Severity proposals arriving on a suspiciously tidy
  scale across five agents usually mean the agents copied a convention rather
  than judged a blast radius. Overrule and re-derive one yourself.
- **The army confirms.** If most findings are Minor and every agent reports the
  same category, suspect the briefs supplied the categories. Re-derive one
  finding yourself from the guidelines alone.
- **Uniform verdicts across domains.** Real systems are uneven. Five domains
  returning the same severity distribution is a sign the agents are restating an
  expectation.
- **The army reports nothing.** An empty return usually means the slice was cut
  too large, not that the domain is clean.
- **The boundary was assumed.** A security finding whose source, boundary, and sink cannot all be
  named in one line is a lead. Grading it as a vulnerability because the shape looked right is how a
  review reports a class of defect that does not exist.
- **Interaction dropped.** The most common way this fails while looking thorough.
  If no interaction pass ran, the run is not whole-tree regardless of agent count.

**Each `fits-no-axis` return increments the orchestrator's `Unclassified:` header count.** That is
the only thing the token is for: it is not a note to a reader, it is a number the orchestrator adds
up, so the uncoded population becomes a count rather than a silence. `eval_diagnostics.py` reads
that header across every stored review body, and reports *stated*, *absent* and *ungraded* as three
different states — because a review that recorded `0` and a review that recorded nothing are not the
same fact, and a total over the second would claim a measurement that never happened.