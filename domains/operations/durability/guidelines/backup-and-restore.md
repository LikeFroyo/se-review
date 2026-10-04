# Backup & restore — evidence that the data comes back

Audit the gap between a backup being scheduled and data being recoverable. A schedule is a claim; a restore is the evidence.

## What to look for

- **Backup configured, restore never run:** Snapshots, dumps, or replication configured with no record of a full restore ever being performed, so a corrupt or truncated backup is discovered during the incident it was needed for.
- **No stated recovery objective:** No RPO or RTO recorded anywhere, so "how much data can we lose" and "how long can we be down" are answered differently by each engineer and by each stakeholder.
- **Stated objective the architecture cannot meet:** An RPO of zero with asynchronous replication, or an RTO shorter than the measured restore time, so the documented promise is one the system has never been able to keep.
- **No point-in-time recovery:** Only nightly dumps, so an accidental delete, a bad migration, or a malicious wipe is unrecoverable for the last 24 hours regardless of how healthy the backups look.
- **Backup shares the failure domain:** Backups written to the same region, account, or cluster as the primary, or excluded from the region policy, so the event that destroys the primary destroys the copies.
- **Retention shorter than the detection window:** Backups expiring sooner than the period a corruption, a dispute, or an investigation takes to be noticed — a slow-burning corruption is discovered after the good copies are gone.
- **Unencrypted or unbounded-access backups:** An unencrypted dump, or a backup store readable by anyone in the account, so the backup is a larger breach surface than the production data.
