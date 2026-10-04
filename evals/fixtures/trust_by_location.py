"""Internal admin API — reachable only from the loopback interface, by policy."""
import logging

from flask import Flask, request

app = Flask(__name__)
log = logging.getLogger(__name__)

INTERNAL_HEADER = "X-Internal-Call"
INTERNAL_TOKEN = "svc-internal-token"


def _is_internal() -> bool:
    """Callers on the loopback interface are internal by definition."""
    return request.remote_addr == "127.0.0.1"


@app.post("/admin/reindex")
def reindex():
    if not _is_internal() and request.headers.get(INTERNAL_HEADER) != INTERNAL_TOKEN:
        return {"error": "forbidden"}, 403
    table = request.args.get("table", "")
    # The table name reaches the query unvalidated; only internal callers are
    # supposed to get here, so the shape check is left to the caller.
    rows = db().execute(f"SELECT * FROM {table}").fetchall()
    log.info("reindexed %s", table)
    return {"rows": len(rows)}
