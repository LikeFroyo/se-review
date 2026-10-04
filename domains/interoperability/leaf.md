---
name: se-review-interoperability
description: Domain orchestrator for Interoperability — audits whether data is interpreted the same way on both sides of every boundary it crosses: process, service, language, locale, region, and file format.
metadata:
  domain: interoperability
  role: pillar
  type: domain-orchestrator
---

# Interoperability Domain Orchestrator (`leaf.md`)

Audit **$ARGUMENTS** against the Interoperability pillar: when this value crosses a boundary, is it read the same way on the other side?

Every other domain audits one component. This one audits the *seam* — the place where a value changes representation, encoding, scale, or jurisdiction. A value can be correct in isolation on both sides and still be wrong in transit, which is why these defects are invisible to any single-side review.

## Sub-domain hierarchy

| Sub-Domain | Scope | Axis | Evaluator Entry |
|---|---|---|---|
| **Encoding & Text** | Character sets, normalisation, BOM, line endings, byte truncation | D1 | `encoding-and-text/sub-leaf.md` |
| **Time & Locale** | Timezone and DST, naive datetimes, locale parsing, week rules, collation | D2 | `time-and-locale/sub-leaf.md` |
| **Numeric Boundaries** | Float money, rounding mode, unit conversion, precision loss in transit | D3 | `numeric-boundaries/sub-leaf.md` |
| **Wire Formats** | Field naming, null vs absent, versioned payloads, delimiter escaping | D4 | `wire-formats/sub-leaf.md` |
| **Shared** | Severity definitions, deduction rubric, output templates | — | `../../shared/severity-and-rules.md`, `../../shared/output-format.md` |

Axes D5 and D6 remain unassigned; a future sub-domain claims the lowest free code.

## Domain evaluation workflow

1. **Invoke Encoding & Text:** Evaluate `encoding-and-text/sub-leaf.md` at every read and write of text that leaves the process.
2. **Invoke Time & Locale:** Evaluate `time-and-locale/sub-leaf.md` for anything timestamped, parsed, formatted, or sorted across a boundary.
3. **Invoke Numeric Boundaries:** Evaluate `numeric-boundaries/sub-leaf.md` for any number converted, scaled, or serialised.
4. **Invoke Wire Formats:** Evaluate `wire-formats/sub-leaf.md` for any payload crossing a service, queue, or file boundary.
5. **Compute Domain Score:** Calculate total deductions from base 100.

## Scoring & grading rubric

- Base score: **100 points**.
- Deductions:
  - Critical (silent money or identity corruption from a conversion, a timezone, or an encoding: wrong amount, wrong day, wrong customer): **-25 points**
  - Major (a value that differs between the two sides in a way that corrupts data or breaks a consumer: mojibake, an off-by-one day, a rounded total, a dropped field): **-10 points**
  - Minor (representation differs but both sides agree, or the difference is contained and observable): **-3 points**
  - Info / Suggestion: **0 points**
- Domain Grade: A (90–100), B (80–89), C (70–79), D (60–69), F (<60).

## Scope boundary — read this before reporting

This domain is where the most over-reported findings in a review live. Apply all five:

- **A boundary must actually exist.** Two sides must disagree for there to be a finding. A value read and written in one process with one encoding is not an interoperability defect, however untidy the literal.
- **Cite both sides.** A finding states what each side does, and what the value becomes in between. A one-sided observation is a local defect and belongs to the owning domain.
- **Prefer the pre-change owning domain where one exists.** Encoding and injection are `correctness/security`; NaN/precision in a single process is `correctness/logic`; unbounded payloads are `operations/performance`. Report here only what is genuinely a *crossing* problem, and cross-reference rather than duplicate.
- **Both sides may be defensible and still disagree.** That is the finding. Do not resolve it by declaring one side "wrong" without a stated contract.
- **Restraint is graded.** Reporting a locale-dependent format that both ends already agreed on is the noise this boundary rule exists to prevent.
