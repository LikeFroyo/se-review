# se-review

A code-review skill. It reads a change or a tree, grades it against 76 defect
guidelines across five engineering domains, and returns findings with evidence,
severity, and a score — plus a statement of what it did not read.

## Design principles

**Findings are about structure, not symptoms.** One finding per root cause, and
the fix covers every cited instance. Fixing one of three is the ordinary failure.

**Severity is blast radius, not irritation.** Missing type hints and docstrings
are never Major. Doubt is handled by *capping* severity, never by discounting the
deduction — a discounted Critical still trips the Critical cap and so changes
nothing that matters, while one that does not has quietly demoted blast radius.

**Say how you know.** Every finding carries `Verified by: RAN | DERIVED | READ`,
and each value obliges work rather than asserting a feeling. It changes no grade.
It is an honesty feature, not an accuracy feature.

**Absence must never read as clean.** Every report header is a fixed set of slots
printed at every value, including zero. A field printed only when it binds
teaches the reader that nothing means nothing — and a truncated report becomes
indistinguishable from a whole one.

**A denominator must not be the run's own output.** Coverage is measured over
entry points, never over the claims the run derived. Otherwise looking at less
raises the score.

**Tests outrank prose only when they were written first.** A test written by
running the code is the implementation agreeing with its own transcript.
Independence is provenance, not subject.

**The gate fails open.** When a check cannot be completed, the finding is
reported as unprobed. Nothing is quietly dropped.

**Never transcribe what a machine already holds.** Nothing is persisted that a
script could invalidate.

## Parameters

| Parameter | Default | Reach for it when |
|---|---|---|
| `--diff-only` | yes | Reviewing a branch or PR. Only changed lines, plus the minimum context needed to judge them. |
| `--full` | no | Auditing a whole tree. Overrides `--diff-only` and the report says so. Records exclusions — generated, vendored, submodules — with reasons. |
| `--focus <text>` | no | You know the area (`auth paths`, `the ingest pipeline`). Non-Critical findings outside it are dropped. |
| `--min <severity>` | no | You want signal over completeness. Below-floor findings are dropped with a one-line note. |
| `--domain <name>` | no | One domain in depth: `correctness`, `maintainability`, `operations`, `interoperability`, `leanness`. |
| `--subdomain <name>` | no | One sub-domain in depth, e.g. `correctness/testing`. |
| `--council` | off | On any judgement the orchestrator would otherwise take alone. Off means no council, ever. |

`--full` and `--diff-only` are mutually exclusive. Flags compose; each one narrows
the denominator, and the report's `Covered:` line always names what it narrowed to.

## When to use what

| The question | Workflow |
|---|---|
| "Review this." / "Review my PR." / "What is wrong with this diff?" | **A** — full multi-domain review. The default. |
| "Audit security in `auth.py`." / "Is the test suite any good?" | **B** — targeted domain or sub-domain audit. |
| "Are we current with X?" / "What does upgrading involve?" / "What is this project meant to do, and does it?" | **C** — conformance, currency, and intent, via the `project-tree` sub-skill. |

A and B grade **defects**. C grades **conformance** and establishes **intent**.
When they meet, hand the finding off rather than grading it in the wrong
workflow: defects found during a conformance run go to A/B, and a version or
specification breach found during a defect review goes to C. Never drop it.

C's intent phase is not on by default — dispatch it when the question is what the
project is *for*, not on every conformance run.

## Layout

```
SKILL.md          orchestrator: workflows, phases, ground rules
domains/          6 domains · 29 sub-domains · 87 guidelines
shared/           severity scale · report format · axis codes · council
project-tree/     conformance and intent sub-skill (3 phases)
evals/            99 fixtures, runner, diagnostics
scripts/          validator · grader · diagnostics
```

Instruction files name no language, framework, vendor, or model. That is
deliberate: the skill has to survive being read by a stack it was not written
against.

## Checking it

```sh
python3 scripts/validate_skill.py      # structure, references, enforced invariants
python3 scripts/grade_evals.py         # fixture corpus integrity
python3 scripts/eval_diagnostics.py    # verdict health and the ablation kill criterion
```

The validator enforces rules whose failure mode is a *silently wrong verdict*
rather than a broken link — the rank-1 evidence split, the quantified probe
budget, and the report-honesty invariants. Reverting any of them fails the build.

## Known limits

- It over-reports on clean code. The clean controls in the corpus do not pass.
  Treat a Critical on code you believe is sound as a prompt to argue, not a verdict.
- Not a linter, not a formatter, and not for writing features or applying fixes.
- Coverage and score measure **the review**, not the project. A clean review of
  a partial tree is still a partial review.