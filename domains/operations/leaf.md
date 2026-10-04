---
name: se-review-operations
description: Domain orchestrator for Operations — coordinates performance, resilience, distributed, observability, delivery, durability, and data-protection sub-domains to audit production reliability and data survivability.
metadata:
  domain: operations
  role: pillar
  type: domain-orchestrator
---

# Operations Domain Orchestrator (`leaf.md`)

Audit **$ARGUMENTS** against the Operations pillar: does this code survive production scale, transient infrastructure failures, network partitions, and on-call operations?
Coordinates sub-domain evaluators and synthesizes the Operations domain health score.

## Sub-domain hierarchy

| Sub-Domain | Scope | Axis | Evaluator Entry |
|---|---|---|---|
| **Performance** | Memory retention, hot-loop allocations, load scaling bounds, cache correctness | C1, C2 | `performance/sub-leaf.md` |
| **Resilience** | Retries, backoff, jitter, timeouts, breakers, health and shutdown | C3 | `resilience/sub-leaf.md` |
| **Distributed** | Messaging consistency, outbox, DLQs, sagas, distributed coordination | C5 | `distributed/sub-leaf.md` |
| **Observability** | Structured logging, correlation IDs, telemetry, log hygiene, audit trail | C4 | `observability/sub-leaf.md` |
| **Delivery** | Feature flag lifecycle, kill switches, canary ramps, deploy configuration | C6 | `delivery/sub-leaf.md` |
| **Durability** | Untested restores, recovery objectives, failover and reconciliation | C7 | `durability/sub-leaf.md` |
| **Data Protection** | Retention, erasure, minimisation, access to personal data | C8 | `data-protection/sub-leaf.md` |
| **Shared** | Severity definitions, deduction rubric, output templates | - | `../../shared/severity-and-rules.md`, `../../shared/output-format.md` |

Axis codes are defined in `../../shared/axis-codes.md` and cited as `C<n>`. This series is **not positional** — Performance holds two codes (C1 hot loops, C2 caching and load scaling) and Observability (C4) precedes Distributed (C5). The table order above is logical, not numeric.

## Domain evaluation workflow

1. **Invoke Performance:** Evaluate `performance/sub-leaf.md` for unbounded growth, loop allocation pressure, load scaling, and cache staleness.
2. **Invoke Resilience:** Evaluate `resilience/sub-leaf.md` for explicit timeouts, backoff, jitter, retry budgets, health signalling, and shutdown.
3. **Invoke Distributed Systems:** Evaluate `distributed/sub-leaf.md` for idempotency, poison-message DLQs, cross-service compensation, and coordinated-state fencing.
4. **Invoke Observability:** Evaluate `observability/sub-leaf.md` for structured logging, trace context, redaction, and audit records.
5. **Invoke Delivery:** Evaluate `delivery/sub-leaf.md` for feature flag lifecycles, canary rollback gates, and deployment configuration defaults.
6. **Invoke Durability:** Evaluate `durability/sub-leaf.md` when data must survive an outage, an operator error, or a region loss.
7. **Invoke Data Protection:** Evaluate `data-protection/sub-leaf.md` when personal or regulated data is stored, processed, or shared.
8. **Compute Domain Score:** Calculate total deductions from base 100.

## Scoring & grading rubric

- Base score: **100 points**.
- Deductions:
  - Critical (immediate production outage, unbounded data loss, catastrophic memory crash, fleet-wide restart storm, fail-open deploy config, never-tested restore, single-region failure with no failover, erasure not honoured in every copy): **-25 points**
  - Major (unbounded cache memory leak, immediate retries hammering 503, missing timeouts): **-10 points**
  - Minor (missing trace correlation, minor metric label cardinality, unmanaged non-critical flag): **-3 points**
  - Info / Suggestion: **0 points**
- Domain Grade: A (90–100), B (80–89), C (70–79), D (60–69), F (<60).

## Output format

When run standalone, format the report per `../../shared/output-format.md`:

```markdown
# Operations Review: <scope>

`<n> findings · C:<n> M:<n> m:<n> i:<n> · Domain Score: <score>/100 (Grade <A-F>)`

## Findings
...
```
When called by the root orchestrator, return findings and score for multi-domain synthesis.
