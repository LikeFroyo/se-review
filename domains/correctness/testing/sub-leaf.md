# Testing Sub-Domain Evaluator

Evaluates test adequacy, mock validity, determinism, and isolation.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Test Adequacy** | Untested changed behavior, assertion validity, mock honesty | `guidelines/test-adequacy.md` |
| **Determinism** | Sleep flakiness, wall-clock dependence, test state isolation | `guidelines/determinism.md` |
| **Expected-Value Provenance** | Expected values derived from the code under test, tautologies | `guidelines/expected-value-provenance.md` |
| **Fixture Realism** | Inputs stripped of what production actually sends | `guidelines/fixture-realism.md` |
| **Concurrency Coverage** | Concurrent code checked only sequentially | `guidelines/concurrency-coverage.md` |

## Sub-domain scoring & deduction rules
- Changed critical behavior shipped with zero test coverage: **MAJOR** (-10 points).
- Assertion-free test, mock asserting mock, or assertions surviving trivial mutants: **MAJOR** (-10 points).
- Flaky sleep-based test: **MINOR** (-3 points).
- Disabled or xfail test with no reason and no owner: **MAJOR** (-10 points).
