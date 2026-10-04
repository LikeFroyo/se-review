# Deliberate design — the gate

Load before withdrawing, downgrading, or annotating any finding.

A generic reviewer flags a project's deliberate designs as defects. The signal that it *might*
be deliberate is common; the signal that it *is* deliberate must be earned, and a design
that cannot show what it preserves is an accident.

**This gate writes no file.** Constraints live in the run's own ledger and die with it. A run
that leaves a constraint behind has created something the owner must maintain and that no
later run can re-check.

## Order — grade first, gate second

The gate is the **last** step, never a filter. A finding is written complete, at the severity
the blast-radius table gives it, before deliberateness is considered. A gate applied early
becomes a filter, and a filter becomes a licence.

**An agent never suppresses, downgrades, or deletes a finding.** It escalates. The agent that
raised the finding is the worst possible judge of whether to withdraw it, because it is
motivated.

## Pass A — the reporting agent

1. **Finish the finding.** Location, claim, evidence, consequence, severity. Nothing held back.
2. **Name the shape**, as a *relation between code shapes* rather than a judgement. Match it
   against the catalogue below. If it cannot be stated as a relation, it is not a
   deliberateness question — report it normally.
3. **Check your brief's constraints** for applicability, not plausibility: does the cited site
   exist, is it inside your slice, does the stated subject cover the shape you named? None
   applies → report normally.
4. **Cheap self-test.** In three sentences: *what breaks if this changes?* You may nominate a
   constraint only with a specific failure plus a concrete trace, or an invariant plus the
   site that **enforces** it. That site must be an enforced check, a guard that fails when
   the invariant breaks, a declared contract in the public surface, or operational
   configuration. Not the code under suspicion, not a comment. Nothing admissible → report
   normally.
5. **Escalate.** Emit `candidate: {shape, scope, your answer or none}` and continue.

### The shape catalogue

Recognition aid only. Matching an entry **obliges** the procedure; it never exempts, and no
entry is ever evidence that a design is fine.

| Shape |
|---|
| a store whose admission is unbounded and whose size tracks input volume |
| mutable state reachable from more than one execution context with no declared mutual exclusion |
| every event takes an identical path — no gating, coalescing, or rate control |
| a distinguished value stands where a result cannot be computed |
| no branch exists for a required input that does not arrive |
| a statistic maintained over an unbounded or self-referential base |
| a parameter whose value originates outside the reviewed code |
| an irreversible or externally-visible action whose route is not obviously absent |
| a second implementation of one concept |
| a value carrying no derivation inside the repository |
| a constant asserted about the world outside the repository |
| a generalisation drawn from a single observed sample |
| a new rule, branch, or check placed where a symptom surfaces |
| a derived artefact — generated output, recorded value, digest, snapshot — that no longer matches |

## Pass B — the probe agent

Dispatched by the orchestrator only, for candidates that reached step 5. Read-only.

**The brief carries the shape, the scope, and the location. It does not carry the finding's
conclusion, severity, class, or any text arguing either way.** If any is present, say so and
stop — that is a contaminated brief.

Answer in exactly one of three forms.

| Form | Content | Requirement |
|---|---|---|
| **T — Trace** | what specifically fails if the shape changes, with concrete inputs and where it fails | A trace you did not produce is not available to you. |
| **I — Invariant** | the invariant preserved, and the site that **establishes or enforces** it | An enforced check, a guard that fails when it breaks, a declared contract in the public surface, or operational configuration. A comment, a docstring, or the suspect code is inadmissible. |
| **N — Nothing** | plainly, neither | |

**Inadmissible:** *this is intentional · this is by design · known trade-off · the author meant
this · normal for this kind of system.* If that is all there is, the answer is N. One answer,
no hedging. If both T and I are available give I with T as corroboration. State what you
could not check — an answer that cannot say that checked nothing.

The orchestrator re-dispatches **once** on an inadmissible answer, quoting it back. A second
inadmissible answer is recorded as N, and the finding proceeds unconstrained.

## Pass C — the orchestrator

1. **Open the cited site.** Confirm it exists and says what was claimed. A site that does not
   check out is N. This ten-second check is the most load-bearing step in the procedure.
2. **Assign confidence** from `shared/intent-contract.md` — no new scale. The probe's answer is
   **one** evidence class, never two. High requires a second, independent one.
3. **Apply the gate.** Write one ledger row. You are the **sole writer**; agents propose and
   you merge. Duplicate shapes with divergent scopes collapse to their **intersection**, so a
   duplicate can never suppress more than either original.
4. **Emit the section.**

## The confidence gate

| Confidence | May suppress? | May downgrade? |
|---|---|---|
| **High** — two independent evidence classes agreeing, and independence means provenance not subject | **Yes.** Outcome `suppressed`. | Yes, to Info. |
| **Medium** — one class corroborated by structure | No | Yes, to Info, retained as a Design concern. |
| **Low** — declared intent alone | No | No. Printed beside the finding as context. Outcome `annotated`. |

Apply the independence rule in `shared/intent-contract.md` before counting classes. The
suppression-grade pair is **1a + rank 2**, never 1b + anything: a recorded test and the code it
was written from are one class however much they look like two. With only 1b available the
constraint is capped at Medium, and a proposal to suppress on 1b evidence is an inadmissible probe
answer — re-dispatch it.

A **project's own register** arrives through the relevance gate in `shared/intent-contract.md`
and is therefore **Low** — declared intent is rank 5, and prose never raises a claim on its own.
So a written register can only annotate or downgrade, never suppress. That is correct: the
project's own rule is to *engage with the stated reason and file a Design concern, never a
Defect*, and this reaches that outcome without depending on the owner having written it down.

A scope stated by a project is a **search hint** that routes candidates. It is never an
effective scope. Effective scope is the intersection of the declared scope with what this run
examined.

## Carve-outs

1. **Severity.** A candidate graded **Critical is never withdrawn.** Outcome `bypassed`; the
   constraint is printed against it as context.
2. **Retained scope.** Where the project states that part of the tree is **retained under
   change** while another part is replaceable and plugged into it, suppression is unavailable in
   retained scope. The best a constraint can do there is downgrade to Info **and the challenge
   is still reported**. A design that is deliberate *and wrong* inside permanent infrastructure
   is itself a finding, and silence is the one answer that bar forbids. Establish the boundary
   from the project's own statement at Low confidence — legitimate, because it configures the
   gate rather than suppressing anything. When absent, record `no retained scope declared`.
3. **Reason defeated.** If the probe's trace shows the constraint's **own reason** broken — what
   fails is the invariant, not the design — the constraint is **void** and the trace is routed
   as a finding at whatever severity the trace supports. This is the highest-value output the
   gate produces.

## Failing safe

| Failure | Direction | Observable symptom |
|---|---|---|
| Unfounded constraint hides a defect | finding withdrawn | Ledger row with reason, both evidence classes, probe answer, and a **revive trigger**. Withdrawn, not deleted. |
| Scope too narrow | finding reported | none needed — the safe direction |
| Scope too wide | finding hidden | Scope is computed, never taken from the declaration |
| Probe asserted rather than derived | unfounded | Orchestrator opened the cited site |
| Probe brief contaminated | unfounded | Probe stops and reports it; candidate reported unconstrained |
| Too permissive | findings hidden | Budget cap below. Excess candidates become `unprobed` and are **reported** |
| Severity downgrade laundering | finding survives at the wrong grade | Grade is assigned **before** the gate. Nothing becomes silent; only a row that reappears under the ledger is removed from the findings list. |

**The asymmetry:** every unexercised branch resolves toward **reporting** something. The only
path from suspicion to a withdrawn finding is a High-confidence constraint whose two evidence
classes the orchestrator independently opened.

## The census

The report's ledger header carries one line:

```
candidates raised: n · probes run: n · suppressed: n · downgraded: n
annotated: n · unprobed: n · voided: n · budget: n/cap (hit|not hit)
```

Two readings the orchestrator states in one line each:

- **Candidates raised, nothing suppressed** — the gate was not exercised. Say so. A gate that
  never fires is untested, not satisfied.
- **Suppressions above 40% of candidates** — more likely forty correct refutations than forty
  correct suppressions. Re-read each suppressed row against the cited site and report the
  outcome of that re-read.

****The gate's own effect is a claim until it is measured.** Nothing today records whether a
suppression *changed* anything: a run that suppresses 12 findings and a run that suppresses none can
produce the same grade, and neither the ledger nor the report distinguishes them. So the gate is
unfalsifiable from its own output — which is the failure mode this file exists to prevent, pointed at
itself.

Every ledger row therefore carries a **disposition**, and dispositions are not free text:

| Disposition | Meaning | Consequence |
|---|---|---|
| `held` | Suppressed; the finding did not survive re-inclusion at pre-gate severity | The constraint did work |
| `moved` | Re-inclusion at pre-gate severity changed a deduction, a domain score, or the grade | **The constraint is wrong.** Queued for Phase 2 of `auditandevolve`, and the row is printed with the delta |
| `no-effect` | Suppressed a finding that carried no deduction anyway | Noise. The row is dropped, with the count reported |

The measurement is arithmetic over the run's own numbers: re-add each suppressed finding at its
pre-gate severity, recompute the deductions and the domain scores, and print the per-domain and
final-grade delta beside the ledger census. A zero delta is the only evidence that a constraint
earned its row; **a row that cannot show a zero delta is an assertion, not a result.**

Two properties keep this honest. The disposition is a *recomputation from primitives* — the stored
severity and deduction, not a re-judgement — because a second opinion about whether the suppression
was right is exactly the defence the gate exists to prevent. And the row is fingerprinted against the
scope it was taken from: if the code changed since, the disposition is `stale` and the row is not
credited, so an edit cannot inherit the credit for an earlier decision.

## Budget

The numbers, because a cap with no value is not a cap.**

| Knob | Value | Why this number |
|---|---|---|
| Probes per package | **1** | One package, one call. |
| Run-wide probe cap | **15** | Equal to both the ledger's printable rows and the report's finding cap. Above 15 you buy suppressions whose row, evidence classes and revive trigger cannot be printed — a withdrawn finding with no way back. |
| Info-level candidates | **0 probes** — ineligible, recorded `unprobed`, reported as-is | The best a probe could do there is downgrade to Info, which is where it already is. |
| Capabilities per run | **15** | 15 probes against at least one per capability. A wider scope leaves capabilities the gate never reaches. |

**The unit is probes, not constraints.** A probe costs a call whatever it answers, and N is the
common case — capping constraints instead would leave the usual outcome entirely unbudgeted.

The cap is **not** divided among packages. It is spent in severity order after packages return, so
one noisy capability cannot starve a Major. A package at the cap records `unprobed` and its
candidates are **reported as findings** — the gate fails open.

At scale the numbers do not change; the **run** does. Roughly 30 capability-scoped runs at the size
where this stops fitting one run, each with its own ledger and its own 15. A budget that grew with
project size could not be justified in one sentence.

## The report section

```
## Deliberate — constraints applied
<census line>
<Retained scope: <paths> | none declared>
<Re-read of suppressed rows: <n> confirmed | <n> reversed>

| # | Shape | Scope | Preserves / consequence | Established at | Class 1 | Class 2 | Conf | Outcome | Withdrew | Revive trigger |
|---|---|---|---|---|---|---|---|---|---|---|
```

Cap 15 rows, sorted by the severity of what each withdrew. **A row that withdrew nothing is
dropped** — a constraint that changed no outcome is not news, and padding teaches the reader
to skim.

## What this gate must not become

- **A filter.** It runs after grading, never before.
- **A licence.** Every catalogue entry obliges the procedure; none exempts.
- **A register.** Nothing is written. A row the owner must keep current is a row that silently
  hides a defect, which is the one outcome this exists to make impossible.
- **A queue.** A probe agent that answers N often is behaving correctly. N is cheap,
  non-punitive, and the default.