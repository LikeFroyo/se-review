---
name: se-review-leanness
description: Domain orchestrator for Leanness — coordinates waste, supply-chain, and synthetic-code sub-domains to audit dead code, premature generality, and bloat.
metadata:
  domain: leanness
  role: gate
  type: domain-orchestrator
---

# Leanness Domain Orchestrator (`leaf.md`)

Audit **$ARGUMENTS** against the Leanness gate: does this code earn its place at all?
Coordinates sub-domain evaluators and synthesizes the Leanness domain health score.

## Sub-domain hierarchy

| Sub-Domain | Scope | Axis | Evaluator Entry |
|---|---|---|---|
| **Waste** | Dead code, unread schema, unused surfaces, YAGNI, redundancy | L1–L4 | `waste/sub-leaf.md` |
| **Supply Chain** | Manifest ranges, lockfiles, build-time execution, build provenance | L5 | `supply-chain/sub-leaf.md` |
| **Synthetic Code** | AI-generated smells, hallucinated APIs, mirror tests, unfinished work | L6 | `synthetic-code/sub-leaf.md` |
| **Shared** | Severity definitions, deduction rubric, output templates | - | `../../shared/severity-and-rules.md`, `../../shared/output-format.md` |

Axis codes are defined in `../../shared/axis-codes.md` and cited as `L<n>`. L1–L4 are axes *within* Waste (L1 dead code, L2 unused surfaces, L3 YAGNI, L4 redundancy), not sub-domains — this series is finer-grained than the others, so do not infer a code from a sub-domain count.

## Domain evaluation workflow

1. **Invoke Waste Sub-Domain:** Evaluate `waste/sub-leaf.md`. Prove death before grading Critical.
2. **Invoke Supply Chain Sub-Domain:** Evaluate `supply-chain/sub-leaf.md` if manifests, lockfiles, CI workflows, or build definitions changed.
3. **Invoke Synthetic Code Sub-Domain:** Evaluate `synthetic-code/sub-leaf.md` for generated smells.
4. **Compute Domain Score:** Calculate total deductions from base 100.

## Scoring & grading rubric

- Base score: **100 points**.
- Deductions:
  - Critical (L1–L4 dead code, unread schema, unearned abstractions, install-time or unverified build execution): **-25 points**
  - Major (vulnerable dependency, active slop defect): **-10 points**
  - Minor (minor unused parameter, local duplicate logic): **-3 points**
  - Info / Suggestion: **0 points**
- Domain Grade: A (90–100), B (80–89), C (70–79), D (60–69), F (<60).

## Output format

When run standalone, format the report per `../../shared/output-format.md`:

```markdown
# Leanness Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Domain Score: <score>/100 (Grade <A-F>)`

## Findings
...
```
When called by the root orchestrator, return findings and score for multi-domain synthesis.
