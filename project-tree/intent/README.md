# Intent artifact contract

A profile records conformance to a technology. An intent artifact records **what the project
is meant to do**, so that verification has something to compare against.

**It is a section of the run report, not a file.** The contract is handed forward inside one
run — to every verifying package and to the receiving review — and dies with the run. Nothing
is left behind for a later run to read, because a later run reading a previous run's conclusions
is a run grading itself. A capability name that matches a folder name has been named wrongly.

## Required sections

```markdown
# <capability> — <one line: what this is for>

## Shape
- Entry point: <where work arrives>
- Owning module: <the module responsible>
- Realised by: <project-authored files, as of this run>
- Crosses: <seams — process, service, store, queue, file, trust boundary>

## Contract

| Claim | Statement | Evidence class | Evidence | Confidence | Verify by |
|---|---|---|---|---|---|
| <id> | <what must be true> | 1a · 1b · 2 · 3 · 4 · 5 · 6 | <file:line> | high · medium · low | <technique> |

Every test cited is classified **1a** (written from an expectation) or **1b** (recorded from
running the code), per `../shared/intent-contract.md` § The rank-1 discriminator. Unclassified is
treated as 1b.

## Verification

| Claim | Verdict | Technique used | Trace |
|---|---|---|---|
| <id> | verified · contradicted · unverified | <technique> | <concrete values followed, or why it could not be> |

## Contradictions
- <claim id> — <what was expected> — <what happens> — <evidence> — <referred to>

## Coverage
- Verified: <claims> · Contradicted: <claims> · Unverifiable: <claims> — <reason>
- Entry points: <ep> total · claimed: <v+c> · unmapped: <n> — <reason> · uncovered: <n>
- Not examined: <paths> — <reason>

## Hand-off
- <observation> — <file:line> — <referred to>

## Re-check triggers
- <the change that makes this artifact stale>
```

## Rules for writing one

- **A claim states intent, never a defect.** If it names a suspicious pattern or points at
  the defect, verification becomes confirmation. See `../shared/intent-contract.md` § Claim
  grammar.
- **Evidence and trace are both mandatory.** A verified claim with no trace is unverified,
  however confidently it was reported.
- **Contradicted and unverified are different columns.** Collapsing them hides the size of
  the audit's own gap.
- **Cite the evidence class.** "Trusts a contract" without saying *which* contract, or
  which precedence rank, is not a finding.
- **No technology names in this skill's own files.** A profile may name technologies freely;
  the skill files stay stack-blind. An intent artifact names whatever the project names.
- **Contradictions route, they do not carry grades.** Severity is the receiving review's call.
- **Re-check triggers are the point.** A structural change, a new entry point, or a rewritten
  test can invalidate claims that no version bump would touch.

## Updating

There is no re-run of an intent artifact, because there is no file. Each run re-establishes
intent from the tree and writes its own section.

If the user supplies a previous report, read it **after** building this run's contract, and
report what moved: a claim added, removed, or reworded; an entry point or owning module that
changed; a contradiction previously routed and now resolved. Treat the prior report as
human-authored declared intent — re-verify it, and report disagreement rather than adopting it.