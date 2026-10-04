---
name: project-tree
description: Identifies a project's implementation language and technology stack from evidence in the repository, deep-researches the current authoritative specification, standard, and official guidance for each, and audits the project for conformance — then maintains a per-technology profile. A third phase establishes what the project is meant to do from evidence independent of its own code, and dispatches subagents to verify each intended behaviour against the implementation. Three phases — language, stack, intent. Use when asked which specifications apply to a project, whether it conforms to current standards, what is outdated or non-conformant, what a version upgrade would involve, what the project is meant to do, whether it actually does it, or to establish and maintain a conformance baseline. Not for reviewing product code for defects — that is the parent se-review skill.
license: MIT
metadata:
  version: "2.0-intent-orchestrator"
  type: standards-conformance-orchestrator
---

# project-tree

Establish what a project is built with, find the current authoritative rules for each thing it is built with, and check the project against them. Then establish what the project is meant to do, and verify that it does. Then keep both results current.

Three phases, in order. Phases 1 and 2 are **Identify → Research → Adhere**; Phase 3 is **Map → Establish intent → Fan out**.

Each writes a per-technology profile or a per-capability contract, but **a re-run starts from zero and re-establishes everything it needs.** It does not diff against what a previous run wrote, because that file was written by the same agent that would read it, and self-authored indexes rot silently — the failure this skill's own eval corpus documents at length. What survives a run is the report, because a human reads it and no tool is misled by its staleness.

- **Phase 1 — Language** (`phase1-language.md`): the implementation language(s).
- **Phase 2 — Stack** (`phase2-stack.md`): everything the language is assembled with.
- **Phase 3 — Intent and behaviour** (`phase3-intent.md`): what the project is meant to do, and whether it does it.

Phase 1 gates Phase 2. You cannot resolve a dependency graph, read a build file, or interpret a lockfile without knowing the ecosystem it belongs to, so the language determination is an input to the stack determination, not a parallel task.

Phase 3 prefers a resolved Phase 1 and Phase 2, because verifying intent against a technology whose semantics are unresolved is guesswork — but it proceeds anyway, marking what it cannot resolve rather than stalling.

**Called by the parent skill.** se-review dispatches here for conformance and currency questions — which specifications apply, whether the project conforms, what is outdated, what an upgrade costs — and for the question Phase 3 exists to answer: what is this project meant to do, and is it doing it. The parent skill owns defect review; this skill owns conformance and intent. Findings from both share one severity scale (`../shared/severity-and-rules.md`) so they can be counted and reported together, and each hands off what belongs to the other.

**Phase 3 is not a code review, and this is the hardest boundary in the skill.** Establishing intent means reading behaviour, and every contradiction it finds is a defect — so every contradiction is a hand-off note, never a graded finding here. What Phase 3 adds that a plain review cannot is the contract: intended behaviour settled independently of the code that implements it. Within a run that contract is handed forward in memory and makes the receiving review sharper, because the review never has to infer what was supposed to happen.

**Neutrality is a hard rule.** This skill names no language, framework, library, vendor, protocol, datastore, or platform anywhere. Every such name enters only from detection output, from a source the run fetches, or from a profile a previous run wrote. If you catch yourself about to write a technology name into this skill, you are describing a project's stack into a tool that must stay stack-blind — stop and put it in a profile instead.

## Non-goals

- Reviewing product code for defects, bugs, security holes, or design quality. Report those and hand off; do not grade them here. Phase 3 reads behaviour to establish intent, but a contradiction it finds is still a hand-off note.
- Style, formatting, naming conventions, or import order. A formatter owns those.
- Deciding what a project *should* be built with. Conformance is measured against the standard for what it *is*.
- Treating a project's own documentation as evidence of what it does. Prose is a claim about intent; only code establishes behaviour.
- Rewriting a profile that still matches its source. A re-run re-derives, then reports what moved against a report the user supplies.
- Deciding a project's deliberate design constraints are wrong without engaging the reason. That is a Design concern, routed outward, never a graded finding here — see `shared/deliberate.md`.

## Load discipline

Load only what the current step needs. Do not bulk-load the phase file and the shared files together:

| Step | Load |
|---|---|
| Any detection | `shared/identification.md` |
| Any research | `shared/source-resolution.md` |
| Any verdict | `shared/adherence.md` |
| Any output | `shared/report-format.md` |
| Phase 1 | `phase1-language.md` |
| Phase 2 | `phase2-stack.md` |
| Phase 3 | `phase3-intent.md` |
| Establishing or grading an intent claim | `shared/intent-contract.md` |
| Before withdrawing or downgrading a finding | `shared/deliberate.md` |
| Before grading any finding | `shared/anti-pattern-gate.md` |
| Dispatching or adjudicating subagents | `shared/fanout.md` |
| Writing a profile | `profiles/README.md` |
| Writing an intent artifact | `intent/README.md` |

## Workflow

### Phase 1 — Language

1. **Identify** the language(s) and the resolved version of each, from evidence in the repository, using `shared/identification.md`. Record the determination with its evidence citations and its confidence.
2. **Research** the current normative reference and official guidance for that language and version line, using `shared/source-resolution.md` and the fixed research agenda in `phase1-language.md`. Every rule carries a source, a tier, and its normative strength.
3. **Adhere** the project against that ruleset, using `shared/adherence.md`. Record what was examined and what was not.
4. **Write or update** the profile at `profiles/<language>.md`.

**Gate:** no language profile exists with a resolved version and a cited ruleset → do not start Phase 2.

### Phase 2 — Stack

1. **Identify** the stack components and each one's resolved version, using `shared/identification.md` and the component taxonomy in `phase2-stack.md`. Enumerate every category, not just the ones that look interesting.
2. **Research** each component the same way, and additionally resolve **cross-component version agreement** — whether the pinned client, peer, and server versions actually correspond.
3. **Adhere** the project against each ruleset, using `shared/adherence.md`.
4. **Write or update** one profile per component.

**Gate:** a component that is detected but has no profile and no cited ruleset is reported as *unaudited* — never silently skipped.

### Phase 3 — Intent and behaviour

1. **Map** the structure — entry points, modules by responsibility, dependencies, and the flow across every seam — then build the **capability map** from it. Use `shared/identification.md` for the boundary.
2. **Establish intent** as explicit claims, built from evidence ranked highest-first and independent of the implementation. Use `shared/intent-contract.md`. Prose is a hypothesis; only code establishes behaviour.
3. **Cut work packages** — vertical per capability, horizontal per systemic concern, plus the boundaries between capabilities. Run the dispatch preflight in `shared/fanout.md`.
4. **Dispatch** subagents with the fixed brief. Each returns a verdict per claim with a concrete trace, and states what it could not check.
5. **Adjudicate and synthesize** — resolve conflicting verdicts by reading the code, collapse root causes, keep contradicted separate from unverified, and route every contradiction as a hand-off note.
6. **Write** the run's intent section into the run report, per `intent/README.md`'s sections. Do not leave it behind for a later run to read.

**Gate:** report verification coverage — verified, contradicted, unverifiable — and never as a quality score. A project can be fully covered and badly broken.

## Re-runs

A re-run re-derives, then compares against the **previous report** if the user supplies one. Never against a file this skill wrote.

Re-detect, re-research, and re-establish intent from the tree as if nothing existed. Then, and only then, read the prior report and report what moved: a version that changed, a source whose currency window closed, a technology added or removed, an entry point that appeared, a contradiction resolved. A prior report is human-authored evidence about a past run — treat it at the confidence the evidence precedence assigns declared intent, re-verify it against the current tree, and report disagreement rather than adopting it.

When nothing moved, say so in one line and stop. A re-run that rewrites unchanged findings is noise.

## Ground rules

- **Evidence, not inference, decides identity.** A technology is audited because the repository asserts it, not because it is plausible. Unproven premises produce unproven findings.
- **Never review against a remembered version.** Read the resolved version, fetch the documentation for that line, and separately establish what the current published version is. Memory is not a source; it is a hypothesis.
- **Every rule cites a source.** A claim with no fetchable source is an Info note, not a finding.
- **A specification is not a preference.** A normative requirement and a recommended practice are graded differently, and a recommendation is never reported as a violation.
- **Recorded scope.** State the files examined and the files not examined. An unreported gap reads as a clean bill of health.
- **Unknown is a valid verdict.** If a rule could not be evaluated, say so and state the attribution impact. Do not guess conformance.
- **Intent must not be inferred from the code being judged.** The implementation cannot be the evidence for what it should do. Establish intent first, then verify against it — otherwise every self-consistent implementation passes, including the broken ones.
- **A claim never names a defect.** It states what must be true. A claim that hands the verifier the answer turns verification into confirmation, and a confirmatory phase is worse than no phase.
- **Profile is the deliverable.** A run that produces findings but no profile is unfinished. The profile is what a human reads next, not what the next run reads.
- **Persist only what a script can invalidate.** An artifact may outlive a run only when a script computes its validity binding in the same run, and binding failure discards **everything derived from it** — never a partial refresh, never a per-row repair. Otherwise it lives in the run and dies with it.
- **Never transcribe what a machine already holds.** Counts, index rows, "last run" dates, and hand-copied digests are the rot. Point at the machine-readable artifact; never restate its contents. Where no machine-readable artifact exists, do not create a file to hold the transcription — re-derive.
