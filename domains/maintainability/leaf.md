---
name: se-review-maintainability
description: Domain orchestrator for Maintainability — coordinates complexity, design, clarity, and evolvability sub-domains to audit architectural quality and long-term change safety.
metadata:
  domain: maintainability
  role: pillar
  type: domain-orchestrator
---

# Maintainability Domain Orchestrator (`leaf.md`)

Audit **$ARGUMENTS** against the Maintainability pillar: can the next engineer change and maintain this code safely without introducing regressions?
Coordinates sub-domain evaluators and synthesizes the Maintainability domain health score.

## Sub-domain hierarchy

| Sub-Domain | Scope | Axis | Evaluator Entry |
|---|---|---|---|
| **Complexity** | Cyclomatic & cognitive complexity, nesting past 3, parameter lists, state modelling | B1 | `complexity/sub-leaf.md` |
| **Evolvability** | Ambient state, change blast radius, seams, test surface vs code surface | B2 | `evolvability/sub-leaf.md` |
| **Design** | SOLID principles, coupling, cohesion, layer boundaries, DDD | B5 | `design/sub-leaf.md` |
| **Clarity** | Naming semantics, units, magic values, comments explaining why | B4 | `clarity/sub-leaf.md` |
| **Shared** | Severity definitions, deduction rubric, output templates | — | `../../shared/severity-and-rules.md`, `../../shared/output-format.md` |

Axes B3 and B6 remain unassigned; a future sub-domain claims the lowest free code.

## Domain evaluation workflow

1. **Invoke Complexity:** Evaluate `complexity/sub-leaf.md` for nesting levels, method size, boolean flags, and state modelling.
2. **Invoke Evolvability:** Evaluate `evolvability/sub-leaf.md` for ambient state, change blast radius, and whether a change can be verified without the real system.
3. **Invoke Design:** Evaluate `design/sub-leaf.md` for SRP divergent change, coupling, and layer breaches.
4. **Invoke Clarity:** Evaluate `clarity/sub-leaf.md` for misleading names, units, magic values, and comment utility.
5. **Compute Domain Score:** Calculate total deductions from base 100.

## Scoring & grading rubric

- Base score: **100 points**.
- Deductions:
  - Critical (circular dependencies breaking build, architectural collapse, unit misstatement causing silent scale error, lifecycle booleans admitting impossible states, ambient state making behaviour non-reproducible): **-25 points**
  - Major (cyclomatic complexity >15, nesting >4, god method violating SRP, no seam at the highest-churn dependency, test complexity exceeding the code's): **-10 points**
  - Minor (magic numbers, ambiguous naming, redundant comments, container kind omitted from a name): **-3 points**
  - Info / Suggestion: **0 points**
- Domain Grade: A (90–100), B (80–89), C (70–79), D (60–69), F (<60).

## Output format

When run standalone, format the report per `../../shared/output-format.md`:

```markdown
# Maintainability Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Domain Score: <score>/100 (Grade <A-F>)`

## Findings
...
```
When called by the root orchestrator, return findings and score for multi-domain synthesis.
