# Durability Sub-Domain Evaluator

Evaluates whether the data survives the failures it is assumed to survive: an untested restore, a single region, an irreversible step, a recovery path never rehearsed.

## Guidelines in this sub-domain

| Area | Focus | File |
|---|---|---|
| **Backup & Restore** | Untested restores, RPO/RTO never stated, missing point-in-time recovery | `guidelines/backup-and-restore.md` |
| **Recovery Paths** | Single-region dependency, runbooks never rehearsed, no reconciliation after failover | `guidelines/recovery-paths.md` |

## Sub-domain scoring & deduction rules
- Backup exists but restore has never been performed end to end: **CRITICAL** (-25 points).
- No point-in-time recovery, or a stated RPO the architecture cannot meet: **CRITICAL** (-25 points).
- Single-region or single-AZ dependency with no documented failover: **CRITICAL** (-25 points).
- Recovery procedure never rehearsed, or a runbook that names a command nobody has run: **MAJOR** (-10 points).
- Destructive or unrecoverable step with no pre-step checkpoint: **MAJOR** (-10 points).
- No reconciliation after a failover, so the two sides diverge silently: **MAJOR** (-10 points).
- Restore time slower than the stated RTO, with the number never measured: **MAJOR** (-10 points).

## Scope boundary

- **A backup that is configured is not a backup that works.** This sub-domain grades the evidence that data can be recovered, not the presence of a schedule.
- Application-level transaction correctness belongs to `correctness/data`; this sub-domain starts where recovery begins.
- A dependency's own durability guarantees are a dependency note unless the project can violate them by its own configuration.
