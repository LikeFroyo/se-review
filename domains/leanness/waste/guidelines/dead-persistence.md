# Dead persistence — schema and configuration nothing reads

Audit for weight that persists: stored objects and declared settings that no live code consumes. The fix is always deletion.

## Orphaned schema

- **Unread tables and columns:** Tables, columns, indexes, views, or triggers with zero readers in application code, jobs, migrations, or reporting — verified with the same search discipline the L1 proof procedure requires, including a check that the only reader is not itself dead.
- **Frozen migration chains:** Migrations retained solely because reversing them is frightening, so every deploy replays a growing set of transformations over state nothing consumes.
- **Unused enum values:** Discriminator or status values no code branches on, left behind by a removed feature.
- **Retention beyond purpose:** A column holding personal or regulated data whose consuming feature was deleted, so the data outlives any lawful reason to keep it.

## Orphaned configuration

- **Unread environment variables:** Names present in `.env.example`, deployment manifests, Helm values, or compose files that no source file, chart, or runbook reads.
- **Stale config keys:** Settings entries retained after the feature that consumed them was removed, still merged, still validated, still documented as supported.
- **Unretired credentials:** A secret declared in a manifest or secret store whose consumer no longer exists, kept "in case" — an attacker's target with no owner.
- **Dead defaults:** A configuration option whose every call site passes the same value, so the key can only be set to what it already is.
