# Wire Formats Sub-Domain Evaluator

Audits the shape of a payload as it crosses a service, a queue, or a file: field names, presence, nullability, defaults, and version.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Field Agreement** | Naming convention, null vs absent, default drift, required-vs-optional mismatch | `guidelines/field-agreement.md` |
| **Versioning & Evolution** | Additive-only evolution, version negotiation, unknown-field tolerance, format pinning | `guidelines/versioning-and-evolution.md` |

## Sub-domain scoring & deduction rules
- A field consumed under a different name, case, or nesting than it is produced, so the value is always absent: **CRITICAL** (-25 points).
- A producer emitting `null` where the consumer requires a value, or the reverse, so a legitimate record is rejected or a required field is read as absent: **MAJOR** (-10 points).
- A breaking shape change shipped without a version gate or a compatibility window: **CRITICAL** (-25 points).
- Consumer with no tolerance for unknown fields, breaking on a producer's additive change: **MAJOR** (-10 points).
- Format negotiated per request with no default and no pinning, so behaviour depends on an `Accept` header: **MAJOR** (-10 points).
- Both sides on one declared schema, validated on write and on read: **INFO** (0 points).

## Scope boundary

- Consumer-facing contract breakage is `correctness/api-contracts`; report it there and cross-reference. This sub-domain covers the non-HTTP seams — queues, files, object stores, cache values, internal RPC — and the *shape* problems that the API rules do not reach.
- A leaked internal field across a wire is `correctness/api-contracts` backward-compatibility, not a field-agreement finding.
