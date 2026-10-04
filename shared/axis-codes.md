# Axis code registry

Single source of truth for the `<Axis Code>` field in a finding. Every code a report may
cite is listed here. A code that is not in this file does not exist.

Each domain's `leaf.md` carries an Axis column pointing here; this file is authoritative
where the two ever disagree.

## Rules

- **One domain, one code per finding.** A finding belongs to the domain that owns the
  defect, and cites that domain's code. A defect that genuinely spans two domains is two
  cross-referenced findings, not one finding with two codes.
- **Never invent a code.** A defect that fits no existing axis is reported with no code
  and a note that the axis is missing. A plausible-looking `C5` is worse than a blank:
  a wrong code sends the reader to a guideline that does not discuss their defect.
- **Unassigned codes are reserved.** They appear in the tables below and must not be
  reused for something else. A new sub-domain claims the lowest free code in its series.
- **Codes are stable.** Once published in a report, a code keeps its meaning. Renumbering
  invalidates every prior review; open a new code instead.

## A — Correctness

Cited as `A<n>`. Codes are positional over the sub-domain order in
`domains/correctness/leaf.md`.

| Code | Sub-Domain | Scope |
|---|---|---|
| **A1** | Logic | Boundary off-by-one, float precision, swallowed errors, error propagation, numeric plausibility, transition completeness, cold start |
| **A2** | Concurrency | Shared mutable state, check-then-act races, deadlocks, locks |
| **A3** | Data | N+1 queries, unbounded SELECT, transaction scope, migrations, incremental aggregate drift |
| **A4** | API Contracts | Breaking changes, schema evolution, idempotency keys |
| *A5* | *retired* | **Moved to the `S` series.** See § A5 → S below. Not renumbered: `A6`–`A8` keep their meanings. |
| **A6** | Testing | Coverage honesty, real assertions, determinism, flakiness, expected-value provenance, fixture realism, concurrency coverage |
| **A7** | AI Systems | Prompt injection, untrusted model output, tool agency, eval gates |
| **A8** | Type & Contracts | Unchecked casts, unjustified suppressions, unenforced boundary contracts |

### A5 → S: the security migration

Security was `A5` inside Correctness and is now the `S` series. **The number was retired, not
reused**, because the codes are positional over the sub-domain order and reusing a slot would
silently change what every recorded verdict citing `A6`–`A8` means.

| Was | Is now |
|---|---|
| `A5` | `S1` trust boundaries · `S2` identity & access · `S3` injection & interpretation · `S4` cryptography & secrets |

**Reading an older verdict.** A finding cited `A5` when it was a security finding with no more
precision than that; map it to the `S` series by subject, not mechanically. A finding that cited
`A1` for a missing authorisation check is a correctness finding about a branch condition — leave it.

The promotion was not cosmetic. `A5` was one flat bag of seven guideline files evaluated as step 5 of
a sequence that computes one average, which applied correctness's proof obligation — *point at the
wrong output* — to a class of defect that has none. A security finding needs a **path**: untrusted
source → boundary that should have rejected it → sink. Stated in the sub-domain, not here, because a
rule referring to a boundary nobody has located cannot be applied.

## S — Security

Cited as `S<n>`. **This series is not positional**: the four sub-domains are ordered by the review
sequence, not by number, because Trust Boundaries runs first and everything else refers to it.

| Code | Sub-Domain | Scope |
|---|---|---|
| **S1** | Trust Boundaries | Untrusted entry points, validation at the crossing, trust assumed downstream |
| **S2** | Identity & Access | Authentication, authorisation, object and function level checks, sessions, tokens |
| **S3** | Injection & Interpretation | Injection, unsafe parsing, deserialisation, cross-origin trust |
| **S4** | Cryptography & Secrets | Primitives, modes, key derivation, secret storage, logging, lifetime |

**A security finding above Info names all three of source, boundary, and sink.** Two of the three is
a lead, graded MAJOR at most. One is a note, graded Info. Reachability is part of the path, so a
finding that cannot show how the code is entered is capped however dangerous its shape.

## B — Maintainability

Cited as `B<n>`.

| Code | Sub-Domain | Scope |
|---|---|---|
| **B1** | Complexity | Cyclomatic & cognitive complexity, nesting, parameter lists, state modelling |
| **B2** | Evolvability | Ambient state, change blast radius, seams, test surface vs code surface |
| **B4** | Clarity | Naming semantics, units, magic values, comments explaining why |
| **B5** | Design | SOLID symptoms, coupling, cohesion, layer boundaries, DDD |
| *B3* | *unassigned* | reserved |
| *B6* | *unassigned* | reserved |

## C — Operations

Cited as `C<n>`. **This series is not positional.** Performance holds two codes, and
Observability precedes Distributed. The sub-domain order in
`domains/operations/leaf.md` is logical, not numeric — read the table below, not the
counting.

| Code | Sub-Domain | Scope |
|---|---|---|
| **C1** | Performance | Hot loops, per-iteration allocation, unbounded growth |
| **C2** | Performance | Cache correctness and eviction, load-scaling bounds |
| **C3** | Resilience | Retries, backoff, jitter, timeouts, breakers, health and shutdown, work-unit retry safety |
| **C4** | Observability | Structured logging, correlation, redaction, audit trail, log hygiene |
| **C5** | Distributed | Messaging consistency, outbox, DLQs, sagas, coordination, fencing |
| **C6** | Delivery | Feature flag lifecycle, kill switches, canary ramps, deploy config |
| **C7** | Durability | Untested restores, recovery objectives, failover and reconciliation |
| **C8** | Data Protection | Retention, erasure, minimisation, access to personal data |

## D — Interoperability

Cited as `D<n>`. Codes are positional over the sub-domain order in
`domains/interoperability/leaf.md`.

| Code | Sub-Domain | Scope |
|---|---|---|
| **D1** | Encoding & Text | Character sets, normalisation, BOM, line endings, byte truncation |
| **D2** | Time & Locale | Timezone and DST, naive datetimes, locale parsing, week rules, collation |
| **D3** | Numeric Boundaries | Float money, rounding mode, unit conversion, precision loss in transit |
| **D4** | Wire Formats | Field naming, null vs absent, versioned payloads, delimiter escaping |
| *D5* | *unassigned* | reserved |
| *D6* | *unassigned* | reserved |

## L — Leanness

Cited as `L<n>`. **This series is finer-grained than the others**: L1–L4 are axes *within*
the Waste sub-domain, not sub-domains. Do not infer a code from a sub-domain count here.

| Code | Sub-Domain | Scope |
|---|---|---|
| **L1** | Waste | Dead code, unread schema |
| **L2** | Waste | Unused surfaces, unused parameters |
| **L3** | Waste | YAGNI, speculative generality |
| **L4** | Waste | Redundancy, duplicate implementations, stale shims |
| **L5** | Supply Chain | Manifest ranges, lockfiles, build-time execution, typosquats, provenance |
| **L6** | Synthetic Code | Hallucinated APIs, mirror tests, completion markers, unfinished work |

## Conformance

project-tree findings cite a project-tree sub-domain and phase (for example
`PT-02/phase-1`), not a letter-series code. See the project-tree sub-skill's own tables.
