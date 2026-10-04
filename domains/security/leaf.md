---
name: se-review-security
description: Domain orchestrator for Security — establishes trust boundaries, then evaluates identity and access, injection and interpretation, and cryptography and secrets. Grades only what has a demonstrated path from untrusted input to harm.
metadata:
  domain: security
  role: gate
  type: domain-orchestrator
---

# Security Domain Orchestrator (`leaf.md`)

Audit **$ARGUMENTS** against the Security gate: **does this code hold its trust boundaries?**

## Why this is a domain and not a sub-domain of correctness

Not because security is as important as correctness. Because the two have **different proof
obligations**, and burying one inside the other quietly applies the wrong one.

A correctness defect is established by a wrong output or a failing input — you can point at it. A
security defect is established only by a **path**: attacker-controlled input → a boundary that should
have rejected it → an operation that causes harm. No path, and it is a hypothesis.

That difference changes how the work is done. Correctness review is bottom-up: read the code, ask
whether it is right. Security review is top-down: start at the edge, ask what a hostile actor does.
It is a different shape of work, not a different topic, and it cannot be run as step 5 of a sequence
that computes one score.

It is a **gate** for the same reason leanness is: a proved authorisation bypass blocks a merge.
That asymmetry is not representable inside a pillar's average — a missed authz defect is not offset
by a clean correctness review, so security is reported as a set of unresolved paths rather than
folded into a score a good average can hide.

## Sequence

**Order is load-bearing.** Trust boundaries run first because every other sub-domain states its
rules in terms of a boundary, and a rule referring to a boundary nobody has located cannot be
applied.

1. **Invoke Trust Boundaries:** Evaluate `sub-domains/trust-boundaries/sub-leaf.md`. Produce the
   boundary inventory, then the attack paths. Nothing downstream can be graded without this.
2. **Invoke Identity & Access:** Evaluate `sub-domains/identity-access/sub-leaf.md` for who the
   caller is, what they may do, and what stays true afterwards.
3. **Invoke Injection & Interpretation:** Evaluate `sub-domains/injection-interpretation/sub-leaf.md`
   for values that gain meaning in a context they were never meant to carry.
4. **Invoke Cryptography & Secrets:** Evaluate `sub-domains/cryptography-secrets/sub-leaf.md` for
   primitives and the material they protect.
5. **Adjudicate paths, not findings:** Every graded finding names a source, a boundary, and a sink,
   or it is a lead at Info. Two reports of the same path are one finding.
6. **Compute Domain Score:** Total deductions from base 100.

## Sub-domain hierarchy

| Sub-Domain | Scope | Axis | Evaluator Entry |
|---|---|---|---|
| **Trust Boundaries** | Untrusted entry points, validation at the crossing, source→boundary→sink | S1 | `trust-boundaries/sub-leaf.md` |
| **Identity & Access** | Authentication, authorisation, object and function level checks, sessions, tokens | S2 | `identity-access/sub-leaf.md` |
| **Injection & Interpretation** | Injection, unsafe parsing, deserialisation, cross-origin trust | S3 | `injection-interpretation/sub-leaf.md` |
| **Cryptography & Secrets** | Primitives, modes, key derivation, secret storage, logging, lifetime | S4 | `cryptography-secrets/sub-leaf.md` |
| **Shared** | Severity definitions, deduction rubric, output templates | — | `../../shared/severity-and-rules.md`, `../../shared/output-format.md` |

The `S` series is **not positional** — the four sub-domains are ordered by the review sequence, not
by number, because Trust Boundaries runs first and the other three state their rules in terms of it.
`A5` was retired when this domain was promoted and was **not** reused; see `shared/axis-codes.md`
§ A5 → S.

## Handing paths to the parent review

A security finding is only useful to the receiving review if the path survives being read. Every
finding carries `Source: <input> → Boundary: <crossing> → Sink: <operation>`, and a finding whose
path cannot be stated in one line is capped at Info.

Where a finding belongs to another domain — a race that becomes an authorisation problem only under
concurrency, say — record it as a hand-off note carrying the path. **Do not grade it here and do not
drop it.**

## Reporting this domain

The report separates three things that a single score would blur, and the separation is the point:

- **Resolved paths** — an attack path that does not reach a sink. Reported, because the effort is
  real and the reader should see it.
- **Open paths** — source, boundary and sink named; harm not demonstrated. These are leads.
- **Unmapped crossings** — a crossing nothing could reach or classify. This is the number that can
  grow while the score stays flat, so it is always printed, including at zero.

A security review that reports a high score while `unmapped` is non-zero has not established that
the code is safe. It has established that it looked at the parts it could reach.