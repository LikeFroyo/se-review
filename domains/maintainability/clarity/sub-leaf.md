# Clarity Sub-Domain Evaluator

Evaluates identifier semantics, magic values, comment honesty, and documentation.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Naming Semantics** | Misleading names, generic naming, boolean predicates, container kind | `guidelines/naming-semantics.md` |
| **Units & Magnitude** | Names that misstate scale, untyped conversions, unit-free persistence | `guidelines/units-and-magnitude.md` |
| **Magic Values & Comments** | Magic literals, echo comments, intent capture, unenforced invariants | `guidelines/magic-values-comments.md` |
| **Documentation Drift** | Stale comments, docstring drift, doc-file claims vs repo facts | `guidelines/doc-drift.md` |

## Sub-domain scoring & deduction rules
- Misleading function name with unexpected side effect: **MAJOR** (-10 points).
- Unit or magnitude misstated by its name, producing a silent scale error: **CRITICAL** (-25 points).
- Magic numbers/strings without domain constants: **MINOR** (-3 points).
- Redundant echo comments or comments compensating for bad code: **MINOR** (-3 points).
- Invariant documented in a comment and enforced nowhere: **MAJOR** (-10 points).
- Stale comment or docstring contradicting current code: **MAJOR** (-10 points).
- Doc-file claim (README or the agent-instruction file) contradicting repo facts: **MAJOR** (-10 points).
