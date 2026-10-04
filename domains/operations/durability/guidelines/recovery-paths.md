# Recovery paths — the failover that has never happened

Audit whether the documented way out of a failure actually works, and whether the system converges after it.

## What to look for

- **Single point of failure with no failover:** One region, one availability zone, one cluster, or one node holding state the whole service depends on, with no automatic or documented manual alternative.
- **Failover never rehearsed:** A documented procedure for promoting a standby, failing over a database, or switching traffic, that no one has executed — so DNS propagation, credential promotion, and application reconnection are all assumed rather than known.
- **Undocumented manual step:** A recovery procedure whose critical step exists only as knowledge in one person's head, or in a runbook that names a command with no expected output to check it against.
- **State that does not survive the switch:** Session state, in-flight work, cached credentials, or a leased lock held by the failed side, with nothing to re-establish it on the new side.
- **No reconciliation after failover:** Two sides now serving or holding state with no job comparing them, so divergence grows silently and is discovered by a customer rather than by a check.
- **Recovery depends on the failed component:** A rollback, failover, or reconciliation job that calls the system that just failed, so the recovery cannot start.
- **Backwards recovery assumed to be safe:** Promoting a standby in place of a primary, with no consideration of what happens if the old primary returns — two writable copies, both authoritative.
- **Unbounded recovery window:** A procedure whose steps are not time-boxed, so the on-call engineer improvises the rest under pressure and the improvisation is what causes the second incident.
