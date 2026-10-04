"""Backups, retention, and the subject-data lifecycle."""
import datetime
from typing import Any, Dict, List, Optional

import boto3
import psycopg2

_conn = psycopg2.connect("postgresql://localhost/orders")

# Nightly snapshot, same account, same region as production.
SNAPSHOT_BUCKET = "acme-orders-snapshots"
REGION = "eu-west-1"
SNAPSHOT_RETENTION_DAYS = 7
LAST_RESTORE_TEST = "never"
RPO_TARGET_MINUTES = 0

SEARCH_INDEX = "orders-search"
CACHE = "orders-cache"
WAREHOUSE = "orders-warehouse"


def snapshot_now() -> Dict[str, Any]:
    """Take the nightly snapshot.

    CRITICAL DEFECT:
    The snapshot is written to the same account and the same region as the
    primary, with no cross-region copy and no point-in-time recovery, so the
    region event that destroys the primary destroys every copy. Retention is
    seven days against an RPO target of zero, and LAST_RESTORE_TEST records
    that no restore has ever been performed.
    """
    client = boto3.client("s3", region_name=REGION)
    client.put_object(
        Bucket=SNAPSHOT_BUCKET,
        Key=datetime.datetime.utcnow().isoformat(),
        Body=_conn.dump(),
    )
    return {"bucket": SNAPSHOT_BUCKET, "region": REGION}


def restore(snapshot_key: str) -> None:
    """Restore the database from a snapshot.

    CRITICAL DEFECT:
    The routine has never been executed. It reads the snapshot from the
    production account's bucket, which requires a production credential, and
    it drops the live database first — so the first attempt at recovery during
    an incident is also the first execution of the code, against production,
    with no rehearsed copy and no verified timing against the RTO.
    """
    client = boto3.client("s3", region_name=REGION)
    _conn.execute("DROP DATABASE orders")
    _conn.execute("CREATE DATABASE orders")
    _conn.restore(client.get_object(Bucket=SNAPSHOT_BUCKET, Key=snapshot_key)["Body"])


def retention_policy() -> Dict[str, Any]:
    """The documented retention schedule.

    CRITICAL DEFECT:
    The schedule is a returned dictionary. No job reads it, no lifecycle rule
    is attached to the bucket, and no expiry column exists on any personal-data
    table, so nothing is ever deleted and the "90 days" below is a number in a
    response body rather than an enforced limit.
    """
    return {"orders": "90 days", "backups": "7 days", "support_tickets": "24 months"}


def delete_customer(customer_id: str) -> Dict[str, Any]:
    """Delete a customer's personal data at their request.

    CRITICAL DEFECT:
    The primary row is deleted and the request is answered "done", while the
    same person's records remain in the search index, the read cache, the
    warehouse, the message queue's dead-letter history, and every nightly
    snapshot for the retention window. The erasure is reported as complete and
    the data is still everywhere, including in a backup a later disaster will
    restore.
    """
    _conn.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
    SEARCH_INDEX.delete_by_query({"customer_id": customer_id})
    CACHE.pop(f"customer:{customer_id}", None)
    WAREHOUSE.execute("DELETE FROM dim_customer WHERE id = %s", (customer_id,))
    return {"deleted": True, "customer_id": customer_id}


def support_notes(customer_id: str) -> str:
    """Free-text support notes for a customer.

    The field carries whatever the agent typed, including full addresses,
    dates of birth, and card digits, with no classification and no length bound.
    """
    row = _conn.execute(
        "SELECT notes FROM support_notes WHERE customer_id = %s", (customer_id,)
    ).fetchone()
    return row[0] if row else ""
