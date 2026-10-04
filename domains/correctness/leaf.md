---
name: se-review-correctness
description: Domain orchestrator for Correctness — coordinates logic, concurrency, data, api-contracts, testing, ai-systems, and type-and-contracts sub-domains to audit integrity and safety.
metadata:
  domain: correctness
  role: pillar
  type: domain-orchestrator
---

# Correctness Domain Orchestrator (`leaf.md`)

Audit **$ARGUMENTS** against the Correctness pillar: does the code do the right thing, every time, across all execution branches?
Coordinates sub-domain evaluators and synthesizes the Correctness domain health score.

## Sub-domain hierarchy

| Sub-Domain | Scope | Axis | Evaluator Entry |
|---|---|---|---|
| **Logic** | Boundary off-by-one, numeric float precision, swallowed errors | A1 | `logic/sub-leaf.md` |
| **Concurrency** | Shared mutable state, check-then-act races, deadlocks, locks | A2 | `concurrency/sub-leaf.md` |
| **Data** | N+1 queries, unbounded SELECT, transactions, migrations | A3 | `data/sub-leaf.md` |
| **API Contracts** | Breaking changes, schema evolution, idempotency keys | A4 | `api-contracts/sub-leaf.md` |
| ~~Security~~ | _Moved to the `security` domain; `A5` retired, not renumbered._ | — | see `shared/axis-codes.md` § A5 → S |
| **Testing** | Coverage honesty, real assertions, determinism, flakiness | A6 | `testing/sub-leaf.md` |
| **AI Systems** | Prompt injection, untrusted model output, tool agency, eval gates | A7 | `ai-systems/sub-leaf.md` |
| **Type & Contracts** | Unchecked casts, unjustified suppressions, unenforced boundary contracts | A8 | `type-and-contracts/sub-leaf.md` |
| **Shared** | Severity definitions, deduction rubric, output templates | - | `../../shared/severity-and-rules.md`, `../../shared/output-format.md` |

Axis codes are defined in `../../shared/axis-codes.md` and cited as `A<n>`. Codes are positional over the table order above.

## Domain evaluation workflow

1. **Invoke Logic:** Evaluate `logic/sub-leaf.md` for boundary conditions and error propagation.
2. **Invoke Concurrency:** Evaluate `concurrency/sub-leaf.md` for shared state and atomicity.
3. **Invoke Data:** Evaluate `data/sub-leaf.md` for query loops and transaction scope.
4. **Invoke API Contracts:** Evaluate `api-contracts/sub-leaf.md` for backward compatibility.
5. **Invoke Testing:** Evaluate `testing/sub-leaf.md` for test adequacy and determinism.
6. **Invoke AI Systems:** Evaluate `ai-systems/sub-leaf.md` when a language model is called, retrieved for, or granted tools.
7. **Invoke Type & Contracts:** Evaluate `type-and-contracts/sub-leaf.md` at deserialization, dynamic-lookup, and cast boundaries.
8. **Compute Domain Score:** Calculate total deductions from base 100.

## Scoring & grading rubric

- Base score: **100 points**.
- Deductions:
  - Critical (SQLi/SSRF/IDOR, auth or token bypass, unsafe deserialization, path traversal, prompt injection reaching a privileged tool, model output executed, unchecked cast on a money path, hardcoded live secret, state corruption): **-25 points**
  - Major (concurrency race, N+1 query loop, unhandled error cascade, untested path): **-10 points**
  - Minor (minor edge case, non-constant timing on non-secret, unverified branch): **-3 points**
  - Info / Suggestion: **0 points**
- Domain Grade: A (90–100), B (80–89), C (70–79), D (60–69), F (<60).

## Output format

When run standalone, format the report per `../../shared/output-format.md`:

```markdown
# Correctness Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Domain Score: <score>/100 (Grade <A-F>)`

## Findings
...
```
When called by the root orchestrator, return findings and score for multi-domain synthesis.
