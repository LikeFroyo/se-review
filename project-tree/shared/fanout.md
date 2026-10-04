# Fan-out — dividing the verification work

Load when Phase 3 dispatches, adjudicates, or synthesizes subagent results.

## Why the division is the whole design

A fan-out is not parallelism for its own sake. Four reasons the cut decides whether the
phase produces anything:

1. **Context decides depth.** An agent holding three files keeps the whole invariant in
   mind and notices the transition that does not exist. An agent handed thirty files keeps
   a fraction, and a missing edge is invisible to it.
2. **Unreasoned overlap destroys information.** Two agents over the same ground produce
   duplicate findings that read as corroboration and inflate confidence, *and* contradictory
   verdicts on identical code. Neither is recoverable downstream — the disagreement is
   already baked in. But the remedy is not "never overlap": **deliberate overlap on shared
   math or a seam is the only way to catch two implementations of one quantity disagreeing**,
   because independent derivation by two readers is what exposes it. Overlap is a defect when
   it is accidental, and a tool when it is named, targeted at shared logic, and stated in both
   briefs.
3. **Verification needs the contract, not the folder.** Handed a folder, an agent derives
   intent from the code and confirms the code. Handed contract claims *and* the code, it
   can falsify. This is the only reason Phase 3 builds contracts first.
4. **Some defects cannot live in a slice.** Data consistency, concurrency, error
   propagation across a boundary, configuration drift, and a rule implemented in three
   places are properties of the *whole*. A per-slice partition never sees them.

Point 4 is why this is a two-axis fan-out. Either axis alone is insufficient, and that is
the single most common way this kind of review fails while looking thorough.

## Axis 1 — Vertical, per capability

1. Enumerate the project's **entry points**: routes, commands, handlers, schedulers,
   consumers, subscriptions, published interfaces — **plus anything registered dynamically**:
   registries, decorators, subscriptions bound at runtime, tables keyed by a string, and dependency
   injection. A mapping method that finds only statically-declared entry points silently misses
   the rest, and coverage still reads high because nothing was counted as missed. Record what you
   looked for and did not find; `unmapped` in the header is where it goes.
2. Walk each one into the project-authored code that realises it. That closure is a
   **capability**.
3. Name a capability by what it *does*, never by where it lives — the name travels into
   every report, and a folder name is not a capability.
4. Cut a capability into work packages. **The ceiling is 10 claims per package** — a number, not
   a judgement, so two runs cut the same capability the same way. Each claim owes a trace plus a
   mandatory implementation-site count, and ten of those is what one pass actually holds. A package
   over the ceiling splits along a state machine, a pipeline stage, or a public contract. Never
   cut by file count, and never merge packages across capabilities to save on dispatch.

## Axis 2 — Horizontal, per systemic concern

One agent per concern, spanning **all** capabilities. These look for the property rather
than the place:

| Concern | What only a whole-tree view shows |
|---|---|
| Data consistency | A value written on one path and read under a weaker guarantee on another. |
| Concurrency and lifecycle | Shared state reached by two capabilities with no single owner. |
| Error propagation | A failure degraded differently on each path that reaches the same caller. |
| Contract agreement | Both sides of a boundary disagreeing while each is internally consistent. |
| Duplication and drift | One rule implemented more than once, already divergent. |
| Configuration and secrets drift | Defaults that fail open, or a setting the code assumes and nothing sets. |

## Axis 3 — Boundaries

Boundaries between capabilities get their own assignment, cited from both sides. The most
expensive defects live exactly where two individually-verified slices meet, and each slice
has a reason not to look: it is not that slice's contract.

## Verification techniques

An agent may not mark a claim verified without a concrete trace or an executed check.

| # | Technique | Use when |
|---|---|---|
| 1 | **Trace with real values** | The default. Pick concrete inputs, follow the path, record what actually happens. |
| 2 | **Locate every implementation site** | Counting sites answers three things at once: zero means the behaviour does not exist; three or more means a duplicated rule that can drift. |
| 3 | **Negative check** | Construct the input that *should* fail and confirm it does. Most real defects are an error path that was never written. |
| 4 | **Silence audit** | What does the code not do that the claim assumes? Defaults, absent branches, states nobody handles. |
| 5 | **Surface comparison** | The declared type, schema, or documentation against the behaviour actually produced at the boundary. |

Technique 2 is mandatory for every claim. A behaviour with no implementation site is a
contradiction, not an unknown.

## The subagent brief

Fixed shape. A brief missing any section produces a report the orchestrator cannot use.

```
SLICE:        <capability or concern> · <exact paths>
NOT YOURS:    <the paths and claims explicitly excluded — name them>
CONTRACT:     <claim ids, verbatim, with evidence and confidence>
CONSTRAINTS:  <shape · site:line · confidence> — applies only where that shape is at that
              site. If none fits what you found, ignore this and report the finding;
              ignoring it costs you nothing.
ADVERSE:      <catalogue shapes your slice is shaped like>
GATE:         You may not suppress, downgrade, or delete. Emit
              `candidate: {shape, scope, your answer | none}`, or "no" with the reason.
VERIFY:       <techniques, in order of preference>
RETURN:       per claim — verdict, evidence, technique used, what you could not check;
              plus `deliberate: <id | none>` and `consequence: <what breaks>` — the
              consequence field is mandatory even when empty, because an agent that
              considered the question and found nothing has produced a result, while an
              agent that skipped it has produced silence. The two must be distinguishable.
LIMIT:        anything you could not verify, and why
```

Four clauses are non-negotiable and go in every brief:

- **Do not read this skill, its sibling phase files, or the repository's own evaluation
  corpus.** Those contain worked examples of this defect class. An agent that reads them
  verifies from the answer key, and the result is worthless. A recursive search that reaches
  them is a contaminated run: discard it and re-dispatch. **A project-owned review skill
  carrying a known-defect register, anti-pattern list, or worked examples is that corpus** —
  the orchestrator reads it and normalises it into `CONSTRAINTS`; its text never reaches an
  agent verbatim.
- **Never receive a defence.** An agent that reads *why* a design is intentional and then
  reviews that design is confirming, not verifying — the same contamination in the opposite
  direction. Constraints reach agents as shape, site, and confidence, never as justification.
- **Do not report style, formatting, or preference.** Grade intent against the claim or
  return nothing.
- **Do not fix anything.** You are establishing whether behaviour matches a claim.

## Dispatch preflight

Before dispatch, check mechanically:

- [ ] No two packages claim the same path, except a named boundary package citing both sides
      and a **named shared-math overlap** stating what both readers derive independently.
- [ ] No brief carries a conclusion, severity, class, or justification for any candidate.
- [ ] Every `CONSTRAINTS` row in a brief cites a site inside that brief's own paths.
- [ ] No brief names the ledger's total size or another package's rows. An agent told
      "three constraints exist" learns that constraints are the expected output, and begins
      manufacturing them.
- [ ] Ledger budget set: at most one new constraint per package, plus a run-wide cap.
- [ ] Every contract claim id is owned by exactly one vertical package, plus any horizontal
      concern that legitimately spans it.
- [ ] Every package holds at most 10 claims. A concern exceeding 10 splits by the property under
      review, the same rule as a capability splitting along its state machine.
- [ ] Every package names what it excludes.
- [ ] No brief hands over a defect location inside a claim.

## Orchestrator duties

These are the orchestrator's own judgement calls — the only ones in a review with no peer. When the
root skill is invoked with `--council`, T1, T3 and T6 of `../../shared/council.md` apply here:
an unresolved disagreement (T3) goes to a council rather than being split, and a package cut this
orchestrator is not confident in (T6) is reviewed before it is dispatched. With the flag off —
the default — every call below stands on the orchestrator alone.

The orchestrator owns everything that would otherwise fragment:

0. **Sole writer of the constraint ledger.** Agents propose; you merge by shape identity.
   Duplicate shapes with divergent scopes collapse to their intersection, so a duplicate can
   never suppress more than either original.
1. **Adjudicate.** Two agents disagreeing about a boundary's behaviour is itself a result.
   Resolve it by reading the code, not by averaging the verdicts.
2. **Enforce evidence.** A claim marked verified without a trace or executed check is
   downgraded to unverified, whatever the agent reported.
3. **Collapse root causes.** The same broken rule found from four directions is one finding
   with an occurrence count, not four findings.
4. **Separate violation from unverified.** These are different results and must never be
   averaged into one number. A gap in coverage is a statement about the audit.
5. **Route.** Contradictions are hand-off notes to the parent review, carrying the claim,
   both sides of the evidence, and the trace. Do not grade them here — see
   `shared/adherence.md` § Hand-off.
6. **Report coverage, not a score of the code.** The honest measure is how much of the
   intended surface was actually verified. Never present a verification-coverage figure in
   a way that reads as a quality score.

## Anti-patterns

- **The army confirms.** If most claims come back verified, suspect the claims were written
  from the code. Re-derive one claim from tests and contracts and compare.
- **The army reports nothing.** An empty or near-empty return usually means the packages were
  cut too large, not that the project is sound.
- **Uniform verdicts across every package.** Real systems are uneven. Uniform output across
  independently-scoped agents is a sign the agents are restating an expectation rather than
  testing it.
- **Doubling.** Two agents covering overlapping ground is always a mistake, never a
  redundancy.