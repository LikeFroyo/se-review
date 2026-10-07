Reviewing your flagged paths — inspecting files now.
Found exposed SSNs and secrets in logs — gathering surrounding context for the full review.
Core defect mapped — now checking the detailed security and observability criteria.
# Review: `evals/fixtures/pii_logging.py` — `register_user`

`2 findings · C:2 M:0 m:0 i:0 · Mean 91.7/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/pii_logging.py` · Not examined: 0 — none
Paths: 1 open · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Security: 75/100 · Operations: 75/100 · Correctness: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain C also binds.

## Findings

### [CRITICAL] Plaintext password and CVV written to log stream
- **Domain:** Security (S4)
- **Verified by:** `RAN` — executed `register_user({'email':'a@x.com','password':'P@ssw0rd123','ssn':'123-45-6789','cvv':'123'})`; observed `P@ssw0rd123` and `CVV=123` in `auth_service` log output.
- **Evidence:** `evals/fixtures/pii_logging.py:18-19` — `register_user`:
  `logger.info(f"Registering user {email} with ssn={ssn} and password={password}")`
  `logger.info(f"Payment card registered with CVV={card_cvv}")`
- **Failure scenario:** Source: caller-controlled `user_data` dict → Boundary: `register_user()` entry with no redaction/validation → Sink: `logger.info` to `auth_service` stream. Logs persist to disk/aggregator with broad readership; any log read, backup, or leak exposes reusable credentials and PCI data. Rotation impossible once logged.
- **Fix:** Delete sensitive interpolations now (local, `evals/fixtures/pii_logging.py:18-19`): log only `email`/user-id and non-sensitive outcome. Add module-scope redacting log filter/structured logger denylist (`password, ssn, cvv, card_cvv`) and purge/rotate existing log copies.
- **Trade-off:** Cost is small code churn plus loss of debug convenience; operators can no longer grep logs for passwords/CVVs — intentional. Central filter adds negligible per-record CPU.
- Cross-ref: Operations (C4) for log-hygiene aspect; no separate deduction there for password/CVV.

### [CRITICAL] PII (SSN) written to log stream, expanding retention/access
- **Domain:** Operations (C4)
- **Verified by:** `RAN` — same execution; observed `ssn=123-45-6789` in log output.
- **Evidence:** `evals/fixtures/pii_logging.py:18` — `register_user`: `f"Registering user {email} with ssn={ssn} ..."`.
- **Failure scenario:** SSN persists in operational logs beyond the registration transaction, readable by on-call/analytics/backup roles with no erasure path. A log aggregation breach or subject-erasure request cannot be honoured for this copy.
- **Fix:** Same local fix as above: never log `ssn`; if correlation needed, log truncated/masked reference (e.g. last-4) only. Scope: local for line removal; module for redaction policy. Cross-ref C8 retention/erasure — no separate deduction.
- **Trade-off:** Loses full-SSN grepability in logs; masked reference preserves support workflow at minimal formatting cost.

## Aligns well
- No dead code, speculative generality, or supply-chain surface in 21-line fixture.
- No encoding/time/numeric/wire crossing defect; no concurrency or contract defect in scope.

Ownership note: overlapping line 18 partitioned by data class per Data Protection scope boundary (`Secrets are not personal data`): Security owns credential material, Operations owns PII. Both Critical, no severity dispute.