# Distributed Systems Sub-Domain Evaluator

Evaluates asynchronous message delivery, consistency guarantees, DLQs, backpressure, distributed coordination, and cross-service workflow recovery.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Messaging Consistency** | Eventual consistency, at-least-once delivery, DLQs, backpressure | `guidelines/messaging-consistency.md` |
| **Producer Reliability** | Dual writes, transactional outbox, publish ordering | `guidelines/producer-reliability.md` |
| **Workflow Compensation** | Sagas, compensating actions, partial-failure states | `guidelines/workflow-compensation.md` |
| **Coordinated State** | Leases, fencing tokens, dedupe record cost | `guidelines/coordinated-state.md` |

## Sub-domain scoring & deduction rules
- Consumer queue lacking Dead-Letter Queue (poison message stall): **MAJOR** (-10 points).
- Treating eventual consistency as strong on critical read path: **MAJOR** (-10 points).
- Missing message deduplication on non-idempotent consumer: **MAJOR** (-10 points).
- Dual-write publish without atomic outbox (lost or ghost events): **MAJOR** (-10 points).
- Cross-service flow with no saga or compensation (permanent partial state): **CRITICAL** (-25 points).
- Distributed lease without a fencing token (concurrent stale writer): **CRITICAL** (-25 points).
