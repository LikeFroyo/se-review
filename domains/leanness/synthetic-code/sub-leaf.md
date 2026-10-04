# Synthetic Code Sub-Domain Evaluator

Evaluates suspected AI-generated patterns for hallucinated symbols, mirror tests, duplication, and work that only looks finished.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **AI Patterns** | Hallucinated APIs, mirror tests, block duplication, error masking | `guidelines/ai-patterns.md` |
| **Completion Markers** | Unimplemented bodies, placeholder returns, unimplemented guarantees | `guidelines/completion-markers.md` |

## Sub-domain scoring & deduction rules
- Hallucinated API call or unprovable mirror test: **MAJOR** (-10 points).
- Insecure concatenated query from generator: **CRITICAL** (-25 points).
- 5+ lines block duplication: **MAJOR** (-10 points).
- Reachable stub, placeholder return, or mock data in a production path: **CRITICAL** (-25 points).
- Docstring guarantees a property the code does not implement: **MAJOR** (-10 points).
