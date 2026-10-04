---
name: se-review
description: Software-engineering review orchestrator. Evaluates code quality, correctness, security, concurrency, performance, architecture and maintainability across dynamically discovered domains, and dispatches conformance, version-currency and intended-behaviour audits to its project-tree sub-skill. Use when the user asks for code review, PR review, diff analysis, security audit, architecture inspection, bug finding, review of a named file or path, flag-scoped review with --focus or --diff-only, checks for dead code, leaks or races, standards conformance, version currency and upgrade impact, or what a project is for and whether it does it. Not for writing features, implementing fixes, mechanical edits (formatting, linting, import sorting, comment rewrites), or a document's style and heading consistency. Machine-consumed text stays in scope: a schema or workflow file is graded for behaviour. Computes domain health scores (0-100) and actionable findings.
license: MIT
metadata:
  version: "2.3-dynamic-orchestrator"
  architecture: dynamic-domain-hierarchy
---

# Software-engineering review orchestrator

Review the target diff or files across dynamically discovered domains, or run targeted domain audits independently. Load only the domain leaf(s) needed for the task; do not bulk-load all domains, sub-leafs, or guidelines.

## Dynamic hierarchy architecture

The root orchestrator maintains no static domain registry. Domains and sub-domains are discovered dynamically:

```
se-review/
├── SKILL.md                          # Dynamic Root Orchestrator (Loads when skill triggers)
├── shared/                           # Universal scoring, blast-radius rules, report formats
│   ├── severity-and-rules.md
│   ├── axis-codes.md
│   ├── output-format.md
│   ├── domain-fanout.md              # dividing a large defect review across domains
│   ├── evolution-candidates.md       # review → rubric gap notes; inert by construction
│   └── council.md                    # Orchestrator peer review, gated on --council
├── project-tree/                      # Conformance sub-skill (called by this skill, not a review domain)
│   ├── SKILL.md                      # Identify → Research → Adhere (language, stack),
│   │                                 # then Map → Establish intent → Fan out
│   ├── phase1-language.md
│   ├── phase2-stack.md
│   ├── phase3-intent.md              # what it is meant to do → subagent verification
│   ├── shared/                       # identification, source resolution, adherence, report
│   │                                 # format, intent contract, fan-out
│   ├── profiles/                     # Per-technology conformance profiles
│   │   └── <technology>.md
│   └── intent/                       # Per-capability intent contracts (in the report)
│       └── README.md
└── domains/                          # Discovered dynamically from domains/*/leaf.md
    └── <domain>/                     # Domain orchestrator (e.g. leanness, correctness, security, maintainability, operations)
        ├── leaf.md                   # Domain Orchestrator & Health Scoring
        └── <sub-domain>/             # Focused sub-domain (e.g. waste, security, concurrency, performance...)
            ├── sub-leaf.md           # Sub-Domain Evaluator & Checklist
            └── guidelines/           # Dedicated guidelines folder
                └── <guideline>.md    # Deep dive defect triggers & verification rules
```

`project-tree/` is deliberately **not** a domain. It answers different questions — *does this project conform to the current rules for what it is built with*, and *what is it meant to do, and does it* — and it carries its own workflow and artifact types. A conformance run produces per-technology profiles; an intent run produces per-capability contracts. Neither is a health score, so neither belongs under `domains/*/leaf.md`. It shares only the severity scale in `shared/severity-and-rules.md`.

Every domain `leaf.md` and sub-domain `sub-leaf.md` speaks for itself:
- **`domains/<domain>/leaf.md`**: Declares domain identity (`name`, `role: gate | pillar`), coordinates its own sub-domains, and computes its domain health score (base 100 minus deductions).
- **`<sub-domain>/sub-leaf.md`**: Declares evaluation checklists, defect triggers, and references its `guidelines/` folder.
- **`<sub-domain>/guidelines/<guideline>.md`**: Deep dive defect triggers, failure scenarios, and verification checklists.
- **`shared/severity-and-rules.md`**: Defines universal blast-radius severity levels, deduction rubric, and ground rules.
- **`shared/axis-codes.md`**: Single source of truth for every `<Axis Code>` a finding may cite, and the rule against inventing one.
- **`shared/output-format.md`**: Defines the unified and standalone report templates.
- **`shared/council.md`**: The orchestrator's peer review, gated on `--council`. Off by default.

## Standing rule — the orchestrator is the only unreviewed participant

Every other agent in a review sees one slice and has peers. The orchestrator sees every slice and
has none, so its judgement calls — how to cut the work, whether a contradiction is real, what the
intent is when two sources disagree, whether a finding is a defect or a choice — are the least
checked decisions in the system, and every other decision inherits from them.

With **`--council` set**, those calls go to a council of subagents before they are acted on, per
`shared/council.md`. Three properties hold whatever else changes:

- **The conclusion is withheld from members.** They receive the question, the evidence, and the
  constraints — never the proposed answer. A member shown the answer confirms it.
- **A fatal flaw blocks.** Any member able to show the decision causes the outcome it is meant to
  prevent must be refuted with evidence or the decision drops to `unverified` and says so.
- **Agreement never decides.** Convergence is a reason to proceed, not a substitute for evidence.
  Unresolved disagreement is reported, not split.

With the flag **unset** — the default — none of this runs, and every such call stands on the
orchestrator alone. That is the normal case, and it is cheap on purpose.

The council reviews the orchestrator, never the product code. Re-reading code that the fan-out has
already covered spends calls to confirm what is known.

## Execution workflows

### Arguments (canonical registry; workflows reference, never redefine)

- `--domain <name>` / `--subdomain <name>`: targeted audit (Workflow B).
- `--focus <text>`: free-text focus within scope (e.g. auth paths); findings outside it are dropped unless Critical.
- `--min <severity>`: severity floor — report only findings at or above it (Critical > Major > Minor > Info); below-floor items are listed individually under `Dropped by --min`, never as a bare count.
- `--full` | `--diff-only` (default): scope size; mutually exclusive, `--full` wins if both appear and the report notes it.
- `--council` (default off): convenes a council of subagents on the orchestrator's own unverified judgements, per `shared/council.md`. Off means no council, ever. On means a council on any trigger the file lists — and none on the non-triggers it lists, which is where the cost control lives.

**A filter names what it dropped.** `--focus`, `--min` and `--diff-only` each remove findings from the
report, and a bare count is indistinguishable from those findings never having been raised. So every
filter lists its dropped items individually — title, severity, and the rule that dropped them — under
the header slot that reports them. The filter's own judgement can be wrong, and a silent drop is
indistinguishable from an absence: a reader who can see the dropped items can tell a wrong filter from
a clean scope, and can act on it. A count is not disclosure. `Excluded by --min:` already prints the
floor's composition; the individual entries are what makes it recoverable.

Follow the conditional workflow matching the user request:

### Workflow A: Full multi-domain review (default)
Execute when user requests a full review, PR audit, or diff evaluation.

1. **Resolve scope:**
   - Dirty git working tree: `git diff HEAD`
   - Branch diff: `git diff <default-branch>...HEAD`
   - Specific file/path: read target files directly.
   - Scope flag (see Arguments): `--full` reviews every file in scope end-to-end, recording exclusions (generated, vendored, submodules) with reasons; `--diff-only` reviews only changed lines plus the minimal surrounding context needed to judge them.
2. **Discover domains:** Scan `domains/*/leaf.md`.
3. **Execute gate domains first (`role: gate`):** If gate check (e.g. leanness/waste) finds unearned bloat or dead code, record Critical blockers immediately.
4. **Execute active pillar domains (`role: pillar`):** Dispatch evaluation across discovered pillar domains.
5. **Synthesize score & report:** Average domain scores for the mean, then apply the two caps in Phase 4 — any Critical caps the grade at F, and the weakest evaluated domain gates the letter. Deduplicate, sort findings Critical → Major → Minor → Info, and format per `shared/output-format.md`.

### Workflow B: Targeted domain or sub-domain audit
Execute when user requests a specific focus (e.g. `--domain <name>`, `--subdomain <name>`, or "audit security in auth.py").

1. **Direct navigation:** Jump directly to `domains/<name>/leaf.md` or `<sub-domain>/sub-leaf.md`.
2. **Evaluate checklist:** Run the focused checks against the target files.
3. **Report:** Output using the standalone domain or sub-domain template in `shared/output-format.md`.

### Workflow C: Conformance & currency audit (project-tree)
Execute when the question is about **conformance rather than defects** — which specifications apply, whether the project meets them, what is deprecated or out of date, what an upgrade would involve, or establishing a maintained conformance baseline. Triggers include "are we current", "check against the latest spec", "what is outdated", "upgrade impact", "conformance baseline".

1. **Dispatch:** Load `project-tree/SKILL.md` and follow it. Do not reimplement its phases here.
2. **Language first:** `project-tree/phase1-language.md` identifies the language(s) and their resolved versions, researches the current normative reference and official guidance, then audits adherence.
3. **Stack second:** `project-tree/phase2-stack.md` does the same for every stack component, then checks cross-component version agreement.
4. **Intent third, when asked:** `project-tree/phase3-intent.md` establishes what the project is meant to do from evidence independent of its own code, then dispatches subagents to verify each claim. Dispatch here when the question is what the project is for, whether it does what it is meant to, or whether a behaviour works as intended — not by default on every conformance run.
5. **Artifact:** Profiles under `project-tree/profiles/`, and for Phase 3 the intent section of the run report. Those are the deliverables, not a health score. Neither leaves an index behind for a later run to trust.
6. **Merge:** Fold project-tree findings into the parent report under `shared/output-format.md`, keeping one severity tally across both, since both grade on the scale in `shared/severity-and-rules.md`.

**Boundary between A/B/C and `auditandevolve`.** A review that finds a defect class the rubric does not cover has found something about the rubric, and the only way that reaches the evolution path is a note: per `shared/evolution-candidates.md`, append `## Evolution candidates` to the run report. **The candidate is a note, never an edit, and never applied.** It is written only by the orchestrator, never dispatched to a subagent, never placed in a brief, and never shown to a judge — because the source is a codebase under review, and frequently an adversarial one. Three candidates per gap per run, then stop: unbounded input from untrusted code into something that shapes future behaviour is an injection sink, not a feedback loop. Applying a candidate is `auditandevolve`'s job, under measurement, on request.

**Boundary between Workflow C and A/B.** C grades conformance and establishes intent; A and B grade defects. When either surfaces something belonging to the other, record it as a hand-off note and route it — do not grade it in the wrong workflow, and do not drop it. Defects found during a conformance run go to A/B; a version or specification breach found during a defect review goes to C.

**An intent contract makes A and B sharper — within the run that produced it.** Workflow C Phase 3 hands its contract forward in memory to the reviewing agents, so a finding can say "this violates the stated contract" instead of inferring what the contract was. That is a stronger finding than one derived from the code alone. It does **not** survive the run: a contract written by a previous run and re-read by this one is this skill grading itself, so no run ever reads another's contract from disk.

## Step-by-step orchestrator checklist

Follow this sequence for every multi-domain review:

- [ ] **Phase 0 — Scope & Argument Parsing:** Identify diff or target files. Parse flags (`--domain`, `--subdomain`, `--focus`, `--min`, `--full` | `--diff-only`). If the request is a conformance or currency question, route to Workflow C instead of continuing.
- [ ] **Phase 1 — Code Ingestion:** Read target files, callers, test coverage, and touched manifests before grading — plus the repo's own stated standards (the repository's own agent-instruction and contributing files) where present, judging against those rather than imported opinions. If this run's Workflow C produced an intent contract, hold it and cite it rather than re-inferring intent. Confirm cited code in the file itself, never from the hunk, a quoted excerpt, or a project summary alone.
- [ ] **Phase 2 — Domain Evaluation:** For each active domain, load `leaf.md`, evaluate relevant sub-domains (`sub-leaf.md`), check interactions between changed hunks and files (each correct alone, broken together), and compute domain score. **Above 30 files or 5,000 lines in scope, load `shared/domain-fanout.md` and run this phase as a fan-out** — below that ceiling, stay serial, because one context sees the cross-file interactions no slice does. Discovery fans out; severity never does. Agents propose it, the orchestrator assigns every one in Phase 3. Record in the report which mode ran:
  $$\text{Domain Score} = \max(0, 100 - \sum \text{Deductions})$$
- [ ] **Phase 3 — Blast-Radius Verification:** Test every finding against concrete failure scenarios. If no direct production outage, security breach, state corruption, or permanent carrying cost can be demonstrated, downgrade to Minor or Info.
- [ ] **Phase 4 — Mathematical Scoring Synthesis:** Compute the mean across all evaluated domains, then apply both caps — the mean alone reports a collapse as a pass:
  $$\text{Mean Score} = \frac{\sum_{i=1}^{N} \text{Domain Score}_i}{N_{\text{evaluated domains}}}$$
  Bands: **A** (90–100), **B** (80–89), **C** (70–79), **D** (60–69), **F** (<60).
  - **Any Critical caps the grade at F.** One outage, data loss, or security exposure outweighs three healthy pillars.
  - **The weakest evaluated domain gates the grade.** The final grade is never better than the lowest band among domains, so an overall B can never sit above a correctness F.
  $$\text{Final Grade} = \min\Big(\text{band}(\text{Mean}),\ \min_i \text{band}(\text{Domain Score}_i),\ \text{F when any Critical exists}\Big)$$
  Report the mean, the final grade, and which cap bound.
- [ ] **Phase 5 — Deduplication & Sorting:** Collapse repeat instances to single root causes, reported once and never listed twice. Where two domains grade one root cause differently, **the owner stands** — the owner is the domain that can state the demonstrated Phase 3 failure scenario. The non-owning domain cross-references and takes no separate deduction. A higher grade displaces the owner's only if it cites its own failure scenario in-report; without one it falls to the owner's grade. Record the minority in one line: `Disputed: <Domain> graded <severity> — <reason, 15 words max>`. If no owner can be shown, hold the lower grade and record the dispute as Info. Sort findings strictly by severity (Critical first, then Major, Minor, Info). Cap at 15 findings, and disclose the cut per the cut policy.
- [ ] **Phase 6 — Structured Report Generation:** Render output matching `shared/output-format.md`. Include dynamic domain scores breakdown. If code is clean, celebrate under `Aligns well`.

## Universal ground rules

- **Evidence or drop it:** Every finding must cite exact `file:lines` and quote or describe the structure.
- **Respect the scope flag:** Under `--diff-only`, findings must sit on changed lines or be directly caused by the change (e.g. the diff breaks a caller); pre-existing issues elsewhere are dropped, not reported. Under `--full`, the whole file is fair game.
- **Dead code requires proof of death:** Text-search whole repo, verify dynamic registration/reflection/CLI/DI, and confirm symbol is not in external public API before grading Critical. A stale duplicate or backup file is NOT a caller.
- **Note a gap in the rubric; never edit the rubric.** When a review finds a class the guidelines do not cover, write one candidate line per `shared/evolution-candidates.md`. That is the whole of the feedback path.
- **A security finding is a path, not a shape.** Above Info it names `Source → Boundary → Sink`: the input an attacker controls, the crossing that should have rejected it, and the operation that causes harm. Two of the three is a lead; one is a note. Reachability is part of the path, so a finding that cannot show how the code is entered is capped however dangerous it looks. See `domains/security/leaf.md`.
- **Say how you know.** Every finding carries `Verified by: RAN | DERIVED | READ`, and the value obliges the work: `RAN` names what was executed, `DERIVED` names the trace chain, `READ` is the default when unmarked. It changes no grade — it tells the reader the weight of the evidence rather than improving it.
- **Severity is blast radius, not irritation:** Lack of type hints, style mismatches, or missing docstrings are Minor or Info, never Major or Critical. Critical requires data loss, security exposure, state corruption, total outage, **or permanent carrying cost**. That list is not restated here: the exhaustive form is the severity table in `shared/severity-and-rules.md`, and a finding graded Critical without one of its conditions is downgraded.
- **State the trade-off:** Every Critical and Major proposed fix must articulate its engineering cost (latency, memory, or complexity added), except deletions.
- **Price the fix's scope:** Every Critical and Major fix names its scope — local, module, boundary, or codebase — and its cost at that scope. A fix may legitimately restructure the whole codebase; one that does not say what it will cost is not a fix. See `shared/severity-and-rules.md` § Fix shape and scope.
- **Do not do linter work:** Indentation, quotes, whitespace, import sorting belong to linters — drop them.
- **Unclear intent is Info:** If author intent is ambiguous, raise as Info/Suggestion; never inflate to Major or Critical.
- **Documented is not resolved:** An inline comment admitting a race condition or flaw does not downgrade its severity.
- **Restraint on clean code:** If code follows best practices, celebrate it under `Aligns well` and award Grade A (100/100) rather than inventing nitpicks.
