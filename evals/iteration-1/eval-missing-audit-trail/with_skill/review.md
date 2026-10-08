Reviewing the flagged fixture and run directory.
Found the missing audit calls — now checking the surrounding run context.
Scope confirmed to a single fixture — now loading the review rubric.
The audit-trail gap maps directly to the rubric — now verifying scope before finalizing.
# Review: `missing_audit_trail.py`

`1 findings · C:0 M:1 m:0 i:1 · Mean 98/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/missing_audit_trail.py` · Not examined: 0 — none
Paths: 0 resolved open | 0 · Unmapped: 0 — no trust-boundary crossings left unclassified
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 100/100 · Security: 100/100 · Operations: 90/100 · Leanness: 100/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: `weakest domain: Operations (B)` — neither Critical cap bound

## Findings

### [MAJOR] No audit record for access, money, and bulk-read actions
- **Domain:** Operations (C4)
- **Verified by:** DERIVED — traced `grant_admin_role` → `DIRECTORY POST` with only `logger.debug`; `issue_refund` → `PAYMENTS POST` with no log at all; `export_customer_data` → `DIRECTORY GET` with no log; `_audit()` exists but has zero prod callers
- **Evidence:** `missing_audit_trail.py:17-35,38-53,56-70,73-75` — `grant_admin_role()` logs only `logger.debug("role %s granted to %s",...)` on 201; `issue_refund()` and `export_customer_data()` emit no audit call; `_audit(action,actor,target)` defined at 13-14 is called only by `_audit_is_defined_but_unused()` at 73-75
- **Failure scenario:** Erroneous `admin` grant discovered later — no actor, prior role, or timestamp to attribute or roll back. Disputed refund — no actor/amount/authorization record for auditor or chargeback. Bulk tenant export — breach investigation cannot establish what left, so notification clock never starts. Debug-level line is dropped at production log level / rotation.
- **Fix:** Call append-only audit on each handler's success and failure paths, recording actor (from verified session, not caller field), target, before/after state, timestamp, source; scope: module — the three handlers plus `_audit` sink.
- **Trade-off:** Adds one durable write per privileged action (latency + storage); requires immutable store and retention policy longer than dispute window.

### [INFO] Audit helper is dead in prod path
- **Domain:** Leanness (L2)
- **Verified by:** READ
- **Evidence:** `missing_audit_trail.py:13-14,73-75`
- **Fix:** Do not delete — this is the intended sink for the Major fix above; retained once wired in. No deduction.

## Aligns well
- External calls carry explicit `timeout=10/120` (C3)
- Endpoints and tokens passed via `Authorization: Bearer` header, not URL (S4)

## Evolution candidates
None — `audit-trail.md` already covers this class.