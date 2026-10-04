# Phase 3 — Intent and behaviour

Establish what the project is meant to do, prove that intent independently of the code
that implements it, and dispatch verification of each claim against the code.

Load `shared/intent-contract.md` for step 3, `shared/fanout.md` for steps 4 through 6,
`shared/identification.md` for steps 1 and 2, and `shared/report-format.md` for step 7.

**This phase does not review code quality.** It answers one question — is the project doing
what it was meant to do — and a contradiction it surfaces is a hand-off note, not a graded
finding. See `shared/adherence.md` § Hand-off.

## Step 1 — Map the structure

Reconstruct how the project is woven before asking what any part of it should do.

1. Locate every entry point: routes, command definitions, handlers, schedulers, consumers,
   subscriptions, and published interfaces.
2. Group into modules by **responsibility**, not by directory. A directory is a filing
   convention; a module is a thing that can change for one reason.
3. For each module, record what it owns, what it depends on, and what depends on it.
4. Trace the **flow** — how a request, message, or job becomes work and where it ends.
   Record the seams it crosses: process, service, store, queue, file, trust boundary.
5. Record the boundary used from `shared/identification.md`, unchanged from Phase 1.
6. State explicitly where the structure could not be resolved, and what that costs. A
   partially-resolved map is a reportable result; a confidently wrong one is not.

## Step 2 — Build the capability map

Turn the structure into the units of work.

1. For each entry point, walk into the project-authored code that realises it. That closure
   is a **capability**.
2. Name each capability by what it does. A folder name is not a capability.
3. Record, per capability: entry point, owning module, the seams it crosses, and the
   project-authored files that realise it.
4. Name the capabilities that are entry points for nothing — dead seams, unreachable
   handlers, orphaned consumers. Record them; do not route them onward yet.

## Step 3 — Establish intent

Per `shared/intent-contract.md`.

1. Build claims from the **evidence precedence**, highest first. Start from the project's
   own tests and public contracts; treat prose as a hypothesis.
2. Apply the **relevance gate** to any project-authored prose you find. Most of it fails.
3. Ask the user **once** about the survivors, batched, naming each and what adopting it
   would change. Proceed on self-discovery if they decline or do not answer — this phase
   never blocks on a human.
4. Derive **silence claims**: what the structure assumes and nothing establishes. These are
   the highest-yield claims in the phase.
5. Work the **intent agenda** below across steps 1 to 3. Each item yields claims with evidence
   class, confidence, and falsifying technique; an item that yields nothing is recorded as
   assessed-and-clear, not dropped.
6. Audit the tests before any claim inherits a rank — see *Step 3.5* below.

### Intent agenda

Fixed, for the reason Phase 1 states: so two runs produce comparable results and a re-run can tell
what changed. Numbering continues Phase 1 (1–10) and Phase 2 (11–16), so claim provenance stays
globally unique.

| # | Question | What a good answer produces |
|---|---|---|
| 17 | What work can arrive here, and through which entry points? | Entry-point inventory, each with owning module, realised-by files, and whether it was found statically or dynamically |
| 18 | What does each module own, and what depends on it in each direction? | Ownership map naming what each module owns, depends on, and is depended on by |
| 19 | How does work flow from arrival to outcome, and which seams does it cross? | Per-capability flow trace naming every seam crossed to its endpoint |
| 20 | What does the publicly visible surface promise to its callers? | Contract claims with evidence class, confidence, and falsifying technique |
| 21 | What behaviour do the project's own checks require? | Stated-test claims (1a) — plus contradictions where a check disagrees with the code |
| 22 | What does the configuration assume of the code, and the code of the configuration? | Operational claims pairing each assumption with the site that must satisfy it |
| 23 | What is assumed but established nowhere? | Silence claims, each Low confidence, each with a silence-audit technique |
| 24 | What ordering, lifecycle, or shared-state assumption does correctness depend on? | Temporal claims spanning capabilities wherever the assumption does |
| 25 | What failure is expected here, and what must happen when it occurs? | Error claims stating the required outcome per failure, never naming a defect |
| 26 | What must never happen, and where is that enforced? | Prohibition claims, each paired with every site that enforces it |

**The cost is real:** ten questions are worked even on a trivial project, and most yield
assessed-and-clear. Pay it. One line of assessed-and-clear per empty item is what lets a re-run say
"nothing moved" in one line and stop, and silent divergence is cheapest to prevent and most
damaging to find late.

### Step 3.5 — Audit the tests before trusting them

A claim's confidence is capped by the quality of its weakest check cited, so this runs **once**,
before any claim inherits a rank.

| # | Check | Fails when |
|---|---|---|
| 1 | **Provenance** | Nothing distinguishes stated from recorded. Unmarked checks are 1b. |
| 2 | **Mutation sensitivity** | Altering the asserted value, or the branch under it, leaves the check green. |
| 3 | **Mirror detection** | The assertion recomputes what the implementation computes, in the check file, from the same helpers. |
| 4 | **Real-path execution** | The logic under test is replaced by a substitute, so no production path runs. |
| 5 | **Edge reachability** | No input exercises absent, empty, zero, negative, oversized, malformed, concurrent, or second-actor cases. |
| 6 | **Error-path presence** | Nothing enters a failure branch. Absence of error checks is a **silence claim**, not evidence of absence of errors. |
| 7 | **Suite-as-argument** | A claim's justification is "the suite is green". Green plus 1b plus unmarked failures is no evidence at all. |
| 8 | **Overruled expectations** | A failing or disabled check is a recorded expectation somebody overruled — a contradiction candidate, never noise. |
| 9 | **Coverage-as-evidence** | A line-coverage figure is offered as proof a behaviour is correct. Coverage counts lines executed, never lines checked. |

Record the census in one line — `checks examined · 1a · 1b · indeterminate` — by the same discipline
as verification coverage: it measures the audit, not the project.
5. Reconcile conflicts between classes. A test contradicting the implementation is a
   result in its own right, recorded as a contradiction and routed — never resolved by
   quietly preferring the implementation.
6. Give every claim an id, its evidence, a confidence, and the technique that would falsify
   it. A claim that cannot be falsified is deleted, not softened.

## Step 4 — Cut work packages

Cut the three axes defined in `shared/fanout.md` — vertical per capability, horizontal per
systemic concern, boundary per seam — using its rules for where a capability splits further.

Run the dispatch preflight in `shared/fanout.md` before dispatching anything. A brief that
names a defect inside a claim is rewritten before it is sent.

## Step 5 — Dispatch

Dispatch with the fixed brief from `shared/fanout.md`. Each agent returns a verdict per
claim, the evidence, the technique it used, and what it could not check.

Subagents return findings. They do not grade them, fix them, or expand scope. An agent that
returns a defect it discovered outside its slice reports it as out-of-scope so the
orchestrator can route it.

## Step 6 — Adjudicate and synthesize

Work the orchestrator duties in `shared/fanout.md` in order. They are the single source for
this step: adjudication, evidence enforcement, root-cause collapsing, the
contradicted-versus-unverified split, routing, and the report cap.

Two consequences are worth stating here because they are where this phase is most likely to
misreport itself: a claim an agent marked verified without a concrete trace is downgraded to
unverified however confidently it was reported, and **contradicted is never merged with
unverified into a single rate** — one is a result about the project, the other is a gap in
the audit, and averaging them produces a number that means nothing.

## Step 7 — Write the intent section

Write the run's intent section into the run report, using the sections in
`intent/README.md`: shape, contract, verification, contradictions, coverage, hand-off.

**Write no file.** The contract is handed forward inside this run — to every verifying package
and to the receiving review — and dies with the run. There is no index, because an index of
capabilities is a list somebody has to keep current, and a capability missing from that list is
one whose claims are never re-verified while coverage still reads high. See the two ground rules
in `SKILL.md`: persist only what a script can invalidate, and never transcribe what a machine
already holds.

What makes the phase worth running is not the artifact — it is that the receiving review no
longer has to infer what was supposed to happen.

## Verification coverage, not a quality score

**The denominator is entry points, never claims.** Coverage over claims is self-certifying: the
denominator is the number of claims the run itself derived, so a run that derives few claims
reports high coverage for having looked at little. A run that maps nothing must be able to say so
in one line.

```
<capabilities> · <claims> claims · verified:<n> contradicted:<n> unverified:<n>
· claimed:<v+c> of <ep> entry points <p>% · unmapped:<n> · uncovered:<n> · packages <n>
```

- **numerator** — verified + contradicted: claims that reached a verdict.
- **denominator** — entry points from the step 1 map, dynamic registrations included.
- **`unmapped`** — entry points the mapping method could not see, with the reason. This is the
  blind spot made visible, and the only number that can grow while coverage does not.
- **`uncovered`** — entry points found but holding no verified or contradicted claim. Each one's
  claims are listed `unverified` with a reason in the detail, so nothing hides behind a percentage.

Never present this as a quality score, never let it stand in for one, and **never average
contradicted with unverified** — one is a result about the project, the other a gap in the audit.

**When intent cannot be established** — no stated checks, no public contracts, no prose — the
honest report is `claimed:0 of <ep> entry points 0% · uncovered:<ep>` plus the reason. That is a
useful result: it tells the receiving review that no independent evidence existed, which is exactly
what it must know before trusting any claim built from structure alone. It is never a pass.

## Prerequisite

Phase 1 and Phase 2 profiles are strongly preferred: verifying intent against a technology
whose semantics are unresolved is guesswork. This is a soft gate, not a hard one.

Where a claim's truth depends on a behaviour a technology defines and no profile resolves,
record it as **unverifiable — no ruleset** rather than guessing. Proceed on everything else,
and list the gap in the report's `Unknown` section.