"""Order service health endpoints and shutdown behaviour."""
import os
import signal
import threading
from typing import Any, Dict

import psycopg2
import requests

from .worker import process_batch

DB_DSN = os.environ["DATABASE_URL"]
TERMINATING = threading.Event()


def liveness() -> Dict[str, Any]:
    """Liveness probe (GET /healthz).

    CRITICAL DEFECT:
    The liveness handler opens a database connection and runs a query. When
    the database has a brief blip, this returns 503, the platform concludes
    every instance is wedged and restarts all of them at once, and each
    restart opens a fresh connection against a database that is still
    recovering.
    """
    try:
        conn = psycopg2.connect(DB_DSN, connect_timeout=2)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
    except Exception:
        return {"status": "unhealthy", "database": "unreachable"}
    return {"status": "healthy"}


def readiness() -> Dict[str, Any]:
    """Readiness probe (GET /readyz)."""
    if TERMINATING.is_set():
        return {"status": "draining"}
    return {"status": "ready"}


def on_sigterm(signum, frame) -> None:
    """Handle termination by exiting immediately."""
    os._exit(0)


signal.signal(signal.SIGTERM, on_sigterm)

# Kubernetes block:
#   terminationGracePeriodSeconds: 15
# Longest accepted request: POST /reports/monthly (runs ~40s)

REPORT_IN_FLIGHT: Dict[str, Any] = {}


def monthly_report(report_id: str) -> Dict[str, Any]:
    """Generate a month-end report (~40 seconds of work)."""
    REPORT_IN_FLIGHT[report_id] = {"started": True}
    response = requests.get("https://warehouse.internal/report", timeout=120)
    REPORT_IN_FLIGHT[report_id] = {"started": True, "done": True}
    return {"status": response.status_code}


def process_queue(message: Dict[str, Any]) -> None:
    """Consume one queue message (takes several seconds)."""
    process_batch([message])
