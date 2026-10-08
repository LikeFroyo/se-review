Contained review — inspecting the fixture in its isolated workspace.
Failover and split-brain in scope — loading the targeted review rules.
# Review: evals/fixtures/region_failover.py

`4 findings · C:1 M:3 m:0 i:0 · Mean 45/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: evals/fixtures/region_failover.py · Not examined: 0 — none
Unclassified: 0 findings fit no axis code
Domain Scores: Operations: 45/100 (Grade F)
Gated by: `Critical finding` — split-brain promotion without fencing
5 of 6 domains unmeasured — the grade below covers the 1 assessed (Operations).

## Findings

### [CRITICAL] Unfenced promotion and unsafe rejoin allow dual-writable split-brain
- **Domain:** Operations (C5)
- **Verified by:** DERIVED — `promote_standby()` promotes standby with no fence of primary → both writable → divergent writes; `recover_late_joiner()` re-adds old primary with only `SELECT 1` check → resumes serving.
- **Evidence:** `evals/fixtures/region_failover.py:26-41` — `promote_standby()`:
> `_standby.execute("SELECT pg_promote()")` then Route53 switch, no fence/stop of `_primary`
and `evals/fixtures/region_failover.py:62-72` — `recover_late_joiner()`:
> `_primary.execute("SELECT 1")` then `return {"rejoined": True}`
- **Failure scenario:** Primary stalls, standby promoted, traffic switched. Old primary still writable accepts orders. Two authoritative DBs diverge silently; DNS flapping sends writes to either. Found by customer dispute, unmergeable.
- **Fix:** Fence before promote: stop/fence old primary (STONITH / revoke writes / fencing token check on write), then promote, then switch DNS. On rejoin, require old primary to re-enter as read-replica with divergence check, never as writer. Scope: boundary (failover protocol + DB write path).
- **Trade-off:** Adds failover latency and fencing-infra dependency; mis-fencing risks availability loss to preserve correctness — correct trade for orders.

### [MAJOR] No reconciliation after failover — divergence lost silently
- **Domain:** Operations (C7)
- **Verified by:** DERIVED — `promote_standby()` creates two writers → `reconcile_after_failover()` is `return None` → no compare job exists.
- **Evidence:** `evals/fixtures/region_failover.py:44-50` — `reconcile_after_failover()`:
> `return None` with docstring `whatever the old primary accepted ... is simply lost`
- **Failure scenario:** Any failover with concurrent old-primary writes permanently loses those orders; no job detects it.
- **Fix:** Add post-failover compare/repair job (diff row versions/ledger, quarantine conflicts for manual review) run before old primary is allowed back. Scope: module (recovery path).
- **Trade-off:** Costs comparison I/O and conflict-handling complexity; delays full recovery while diff runs.

### [MAJOR] In-flight session, credential, and lease state does not survive switch
- **Domain:** Operations (C7)
- **Verified by:** DERIVED — state held in failed process per docstring → new side starts empty → all sessions/leases dropped on every failover.
- **Evidence:** `evals/fixtures/region_failover.py:53-59` — `in_flight_sessions()`:
> `Session state, cached credentials, and the scheduler's lease live in the process, not the database`
- **Failure scenario:** Region failover logs out all users, invalidates cached credentials, and drops scheduler lease — duplicate schedulers or stalled jobs after switch.
- **Fix:** Externalize sessions/credentials/leases to replicated store (DB/Redis with TTL) or drain + re-establish protocol on new side. Scope: boundary (session/lease storage contract).
- **Trade-off:** Adds read/write latency to session path and external-store dependency; removes total session loss.

### [MAJOR] Runbook never rehearsed; RTO never measured
- **Domain:** Operations (C7)
- **Verified by:** READ
- **Evidence:** `evals/fixtures/region_failover.py:15-23` — `RUNBOOK` manual `ssh / systemctl / pg_ctl promote / route53` steps, `evals/fixtures/region_failover.py:22` — `LAST_REHEARSAL: Optional[str] = None`, `evals/fixtures/region_failover.py:23` — `FAILOVER_DURATION_SLO = "30 minutes"` as unmeasured string
- **Failure scenario:** First real failover discovers DNS propagation, credential promotion, and reconnect assumptions fail; on-call improvises; 30-minute SLO unprovable.
- **Fix:** Rehearse failover end-to-end (game day), record output checks per runbook step, measure wall-clock recovery and gate SLO on it. Scope: module (runbook + drill harness).
- **Trade-off:** Costs drill time and standby-region write-up; risks drill-induced incident without isolated rehearsal environment.

## Aligns well
- Standby/primary topology and traffic-switch intent are explicit (C7).