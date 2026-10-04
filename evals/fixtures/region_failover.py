"""Regional failover for the orders service."""
import json
from typing import Any, Dict, List, Optional

import boto3
import psycopg2

PRIMARY_REGION = "eu-west-1"
STANDBY_REGION = "eu-west-2"

_primary = psycopg2.connect("postgresql://eu-west-1/orders")
_standby = psycopg2.connect("postgresql://eu-west-2/orders")
_route53 = boto3.client("route53")

RUNBOOK = """
1. ssh bastion-1
2. sudo systemctl stop orders-api
3. pg_ctl promote -D /var/lib/postgresql/data
4. update route53 record A orders.acme.example -> 1.2.3.4
5. sudo systemctl start orders-api
"""
LAST_REHEARSAL: Optional[str] = None
FAILOVER_DURATION_SLO = "30 minutes"


def promote_standby() -> Dict[str, Any]:
    """Promote the standby and repoint traffic.

    CRITICAL DEFECT:
    The standby is promoted in place while the primary is still running and
    still writable, and nothing fences the old primary — so both accept writes
    and the two diverge with no error on either side. No job compares them
    afterwards, so the divergence is found by a customer.
    """
    _standby.execute("SELECT pg_promote()")
    _route53.change_resource_record_sets(ChangeBatch=[{
        "Name": "orders.acme.example",
        "Type": "A",
        "ResourceRecords": [{"Value": "1.2.3.4"}],
    }])
    return {"promoted": True, "region": STANDBY_REGION}


def reconcile_after_failover() -> None:
    """Bring the demoted side back in line.

    No-op: nothing in the codebase compares the two regions, so whatever the
    old primary accepted while it was demoted is simply lost.
    """
    return None


def in_flight_sessions() -> int:
    """Sessions held in memory on the failed side.

    Session state, cached credentials, and the scheduler's lease live in the
    process, not the database, so a failover loses all of them.
    """
    return 0


def recover_late_joiner() -> Dict[str, Any]:
    """Rejoin the old primary after it returns.

    CRITICAL DEFECT:
    The old primary comes back, finds it still holds a writable connection, and
    resumes serving. Nothing detects the split brain and nothing stops it, so
    two databases are authoritative and the application writes to whichever
    one DNS resolved to seconds earlier.
    """
    _primary.execute("SELECT 1")
    return {"rejoined": True, "region": PRIMARY_REGION}
