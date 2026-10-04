# Complexity Sub-Domain Evaluator

Evaluates structural complexity, nesting depths, method sizes, and parameter lists.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Cognitive & Cyclomatic** | Decision points >15, nesting past 3, long methods | `guidelines/cognitive-cyclomatic.md` |
| **Parameter Lists** | Boolean flag parameters, excessive arity, parameter objects, transposable pairs | `guidelines/parameter-lists.md` |
| **State Representation** | Independent booleans admitting impossible states, unvalidated status | `guidelines/state-representation.md` |

## Sub-domain scoring & deduction rules
- Extreme cyclomatic complexity (>15) or nesting past 3: **MAJOR** (-10 points).
- Boolean flag arguments switching internal execution paths: **MAJOR** (-10 points).
- Long methods (>50 lines) doing multiple things: **MAJOR** or **MINOR** (-10 to -3 points).
- Adjacent same-typed parameters transposable at the call site with no type error: **MAJOR** (-10 points).
- Independent booleans representing a lifecycle, so an invalid combination is storable and no transition rejects it: **CRITICAL** (-25 points).
