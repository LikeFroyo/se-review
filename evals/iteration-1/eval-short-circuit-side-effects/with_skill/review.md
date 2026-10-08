Reviewing the short-circuit fixture — inspecting code and run directory.
Found the vulnerable ordering patterns — gathering eval context to complete the review.
This is a single-file scope — discovering review domains to run the full audit.
I've mapped the early-return gaps against the guidelines — checking the eval harness for expected signals.
# Review: `evals/fixtures/short_circuit_side_effects.py`

`3 findings · C:0 M:2 m:1 i:0 · Mean 96/100 · Final Grade B`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/short_circuit_side_effects.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — all crossings classified
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 90/100 · Security: 90/100 · Operations: 97/100 · Maintainability: 100/100 · Interoperability: 100/100 · Leanness: 100/100
Gated by: `weakest domain: Correctness/Security (B)` — always printed.
Serial mode (1 file, well under fan-out ceiling). No council (default off).

## Findings

### [MAJOR] Early returns skip required effects; one effect fires before the authz check
- **Domain:** Correctness (A1)
- **Verified by:** DERIVED — `update_email` lines 17→20→22-24 and `deactivate_account` lines 33→37-38 traced statically.
- **Evidence:** `short_circuit_side_effects.py:12-25` (`update_email`) and `:28-39` (`deactivate_account`):
```python
if not user.get("email_verified"):      # L17
    logger.info(...)                    # L18 — effect before authz
    return {"status": 422}              # skips audit + metrics
if not actor.get("is_admin") ...:       # L20 authz
    return {"status": 403}              # L21 — no audit, no metric, no log
# success: db.update_email + audit.info + metrics["updated"] += 1
```
`deactivate_account` 403 path (L33-36) emits `metrics["forbidden"] += 1` + `logger.info` but no `audit.info`, while success (L37-38) emits `audit.info` but no success metric — asymmetric with `update_email`, whose 403 emits nothing.
- **Failure scenario:** Forbidden/422 probes leave no audit record, so credential-stuffing or cross-account probing is invisible precisely when it is happening; incident response cannot reconstruct who was targeted. Cross-references Operations (C4) incomplete-coverage note below; deduction taken once here.
- **Fix:** Module scope — check authorization before state validation in `update_email`; emit an `audit.info` (actor, target, decision, reason) on every deny path (404/422/403), and make `forbidden`/`updated` accounting consistent across both handlers.
- **Trade-off:** Extra audit writes on deny paths add small storage/latency cost and require a durable append-only sink so the audit trail itself cannot be rotated away.

### [MAJOR] Validation-before-authorization leaks account verification state
- **Domain:** Security (S2)
- **Verified by:** DERIVED — Source → Boundary → Sink chain traced below; no execution.
- **Evidence:** `short_circuit_side_effects.py:17-21` (`update_email`): `email_verified` check precedes the `is_admin`/self check. Source: untrusted `actor` + `user_id` params to `update_email`. Boundary: authz check at L20, placed after the L17 verification gate. Sink: distinguishable outcomes — `422` + `logger.info("unverified…")` for unverified accounts vs `403` for verified-but-unauthorized accounts (vs `404` for nonexistent).
- **Failure scenario:** Any caller (including unauthenticated, depending on router) enumerates which accounts exist and which are unverified by scanning `user_id`s, enabling targeted phishing of unverified accounts and log-oracle probing. `deactivate_account` (L33) orders correctly (authz first), proving the contract.
- **Fix:** Local scope — move the L20 authz check above the L17 verification check; return `403` before any state-dependent branch or log line. Authorized self-callers still get `422` for their own unverified account, so legitimate UX is unchanged.
- **Trade-off:** Negligible — one comparison reordered; error precedence changes only for unauthorized callers, which is the point. Cross-references Correctness (A1) ordering finding above.

### [MINOR] Audit entries record outcome only, no actor/target/before-after
- **Domain:** Operations (C4)
- **Verified by:** DERIVED — cited log calls read directly; no append-only store or identity fields present.
- **Evidence:** `short_circuit_side_effects.py:23` (`audit.info("email changed")`) and `:38` (`audit.info("account deactivated")`) — outcome string only; no actor id from verified session, no target `user_id`, no before/after email value.
- **Fix:** Include actor (from verified session, not caller-supplied field), target, timestamp/source, and before/after values in each audit event.
- **Verified by note:** READ-equivalent weight otherwise; chain is the two call sites above.

## Aligns well
- Correctness (A1): authz predicate itself (`is_admin` or self) is correct in both handlers; no bypass.
- Correctness (A1): `None`-user → `404` handled before any mutation in both functions.
- Operations (C4): separate `audit` logger from debug `logger` is the right shape; content is what needs work.
- Leanness: no dead code, no speculative surface (100/100).
- Maintainability: two short handlers, clear names, flat guard-clause structure (100/100).
- Interoperability: no encoding/time/numeric/wire crossing in scope (100/100).