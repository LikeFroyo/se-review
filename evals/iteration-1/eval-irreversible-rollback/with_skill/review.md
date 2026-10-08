Reviewing target files now.
Found the irreversible migration defect — now mapping the eval context.
I've confirmed the scope and scoring rules — now inspecting the migration and rollback specifics.
# Review: `evals/fixtures/irreversible_rollback.py`

`3 findings · C:1 M:1 m:1 i:0 · Mean 94/100 · Final Grade F`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/irreversible_rollback.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no untrusted entry points in migration script
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 90/100 · Operations: 75/100 · Security: 100/100 · Leanness: 100/100 · Maintainability: 100/100 · Interoperability: 100/100
Gated by: `Critical finding` — any Critical caps grade at F; weakest domain Operations (C, 75/100) also gates.

## Findings

### [CRITICAL] Documented rollback unexecutable — downgrade raises, dropped column unrecoverable
- **Domain:** Operations (C7)
- **Verified by:** DERIVED — `downgrade_0417` raises → `rollback.sh` aborts → old image vs new schema → full restore. Chain: `irreversible_rollback.py:21-31` + `34-37` + runbook comment `34-36`.
- **Evidence:** `irreversible_rollback.py:21-31` — `def downgrade_0417(connection: Any) -> None: raise NotImplementedError("downgrade not supported for 0417")`; `irreversible_rollback.py:17` — `ALTER TABLE orders DROP COLUMN fax_number`; `irreversible_rollback.py:37` — `ROLLBACK_STATE = {"verified_in_production": False, "last_rehearsed": None}`.
- **Failure scenario:** Release 2026.9.3 causes outage → on-call runs `./rollback.sh 2026.9.2` per runbook → `downgrade_0417` raises → deploy sequence halts mid-rollback with schema on `external_ref` (no `fax_number`/`legacy_ref`) that previous image cannot read → only recovery is full database restore, which was never rehearsed (`verified_in_production: False`). Cross-ref: Correctness (A3) for destructive DDL; Delivery (C6) for broken rollback gate.
- **Fix:** Scope: boundary. 1) Block release until reversible. 2) Replace with expand-contract: add `external_ref NULL`, backfill, dual-write, cut over, drop `fax_number` in later release after old image retired. 3) Implement and rehearse `downgrade_0417` + backup/restore in staging, flip `ROLLBACK_STATE` only after observed restore.
- **Trade-off:** Costs an extra release cycle, dual-write complexity, and temporary storage for both columns; defers cleanup for deploy safety.

### [MAJOR] Breaking schema change with conditional data loss, no compat window
- **Domain:** Correctness (A3)
- **Verified by:** DERIVED — `upgrade_0417:14-18` renames `legacy_ref→external_ref` then `UPDATE ... WHERE external_ref IS NULL` then drops `fax_number`; any row with non-NULL `external_ref` discards its `fax_number` silently.
- **Evidence:** `irreversible_rollback.py:8-18` — `upgrade_0417`: `RENAME COLUMN legacy_ref TO external_ref`, `UPDATE orders SET external_ref = fax_number WHERE external_ref IS NULL`, `DROP COLUMN fax_number`.
- **Failure scenario:** Old code reading `legacy_ref`/`fax_number` breaks on new schema; rows where `external_ref` was already set lose `fax_number` permanently with no backup copy — backfill is lossy, not just irreversible.
- **Fix:** Scope: module. Preserve `fax_number` until compat window closes; backfill without `WHERE` filter or log conflicts to reconciliation table; gate `DROP COLUMN` on prior-version retirement.
- **Trade-off:** Retaining dropped column prolongs migration debt and doubles write path during transition.

### [MINOR] No atomicity / failure handling around multi-statement DDL
- **Domain:** Correctness (A3)
- **Verified by:** READ
- **Evidence:** `irreversible_rollback.py:14-18` — three `cur.execute` + single `connection.commit()`, no rollback; DDL auto-commit on many engines makes partial apply likely.
- **Fix:** Wrap in transactional DDL where supported, or make each step idempotent with pre-flight backup.

## Aligns well
- Defect is self-documented in docstring `irreversible_rollback.py:24-30` (A3/C7): states reversal unimplemented and data gone — honest, though documented-is-not-resolved.
- Linear, low-complexity migration (B1): no branching, no ambient state.