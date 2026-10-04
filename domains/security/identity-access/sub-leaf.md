# Identity & Access Sub-Domain Evaluator

Evaluates who a caller is, what they may do, and what remains true of that after the fact. Every
rule here presumes a boundary from *Trust Boundaries*: "unauthorised" is meaningless until the
crossing that should have rejected the caller is named.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Authentication** | Identity establishment, credential handling, session lifecycle | `guidelines/authentication.md` |
| **Access Control** | Authorisation, object-level and function-level checks, privilege boundaries | `guidelines/access-control.md` |
| **Token Validation** | Signature, claims, expiry, audience, revocation | `guidelines/token-validation.md` |

## Sub-domain scoring & deduction rules

- **Authorisation absent on a path reachable from an untrusted source:** **CRITICAL** (-25).
- **Authentication bypassable:** **CRITICAL** (-25).
- **Privilege confused between two actor classes:** **CRITICAL** (-25) — this is the boundary the
  whole domain exists to hold.
- **Session or token lifetime longer than the privilege it carries:** **MAJOR** (-10).
- **Missing check on an administrative path:** **MAJOR** (-10).
