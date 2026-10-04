# Data Protection Sub-Domain Evaluator

Evaluates personal and regulated data for the whole of its life: what is collected, how long it is kept, who can reach it, and whether a person can get it back or have it removed.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Retention & Erasure** | Retention limits, right-to-erasure across every copy, backup expiry, legal holds | `guidelines/retention-and-erasure.md` |
| **Exposure & Minimisation** | Collection beyond need, over-broad access, encryption at rest, subject-request handling | `guidelines/exposure-and-minimisation.md` |

## Sub-domain scoring & deduction rules
- Erasure request not honoured in every copy, queue, index, cache, and backup: **CRITICAL** (-25 points).
- Personal data retained with no stated retention period, or retained past the stated one: **CRITICAL** (-25 points).
- Personal data stored unencrypted, or a backup readable by the whole account: **CRITICAL** (-25 points).
- Collection of data with no stated purpose, or never read by any consumer: **MAJOR** (-10 points).
- Access to personal data not scoped to the minimum, or no record of who read it: **MAJOR** (-10 points).
- Subject-access request with no way to produce the complete record for one person: **MAJOR** (-10 points).
- Data shared with a third party with no stated basis, purpose, or deletion obligation: **MAJOR** (-10 points).
- Consent or notice handled outside the system that holds the data: **MINOR** (-3 points).

## Scope boundary

- **Secrets are not personal data.** Credential and key handling is `correctness/security`; a secret that is also a person's credential is graded once at the higher severity.
- A defect here is graded on the regulatory or breach consequence, not on the tidiness of the schema.
- Where a finding is an ordinary access-control defect, grade it there **and** cross-reference, so the existing IDOR findings are never double-counted.
