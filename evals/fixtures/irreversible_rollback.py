"""Release 2026.9.3 database migration and its rollback script."""
from typing import Any, Dict

# Migrations applied in order; 0 = baseline.
APPLIED = ["0001_create_orders", "0142_add_fax_number", "0417_rename_orders_legacy_ref"]


def upgrade_0417(connection: Any) -> None:
    """Release 2026.9.3: consolidate the legacy order reference.

    The release renames `orders.legacy_ref` to `orders.external_ref` and
    backfills it from `orders.fax_number`, then drops `orders.fax_number`.
    """
    with connection.cursor() as cur:
        cur.execute("ALTER TABLE orders RENAME COLUMN legacy_ref TO external_ref")
        cur.execute("UPDATE orders SET external_ref = fax_number WHERE external_ref IS NULL")
        cur.execute("ALTER TABLE orders DROP COLUMN fax_number")
    connection.commit()


def downgrade_0417(connection: Any) -> None:
    """Reverse release 2026.9.3 (required by the documented rollback runbook).

    CRITICAL DEFECT:
    The reversal is not implemented — it raises — while the data needed to
    rebuild the dropped column is gone. The documented rollback is therefore
    unexecutable: if this release causes an outage, running the rollback
    command stops the deploy sequence with the previous version unable to read
    the current schema, and recovery requires a full database restore.
    """
    raise NotImplementedError("downgrade not supported for 0417")


# runbook.md, section "Rollback":
#   1. ./rollback.sh 2026.9.2
#   2. rollback.sh calls downgrade_0417 then restarts the previous image
ROLLBACK_STATE: Dict[str, Any] = {"verified_in_production": False, "last_rehearsed": None}
