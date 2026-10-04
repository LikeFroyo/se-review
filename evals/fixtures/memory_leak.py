"""Query caching service for analytics and reporting requests.
Demonstrates unbounded in-memory cache accumulation (C1/C2) with no TTL,
no size cap, and no eviction policy.
"""

import time
from typing import Any, Dict, List, Optional

# Global cache mapping session/request IDs to full query payloads and result sets
# Smell: High cardinality keys, unbounded dictionary growth, no TTL, no eviction policy
QUERY_RESULT_CACHE: Dict[str, Dict[str, Any]] = {}


def fetch_analytics_report(
    session_id: str,
    query_params: Dict[str, Any],
    raw_dataset: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Execute analytics aggregation and cache results in memory.

    C1/C2 Defect: Each call registers a new session entry into QUERY_RESULT_CACHE
    without any capacity ceiling, TTL expiration, or LRU eviction mechanism.
    Under continuous traffic, process resident memory grows monotonically until OOM crash.
    """
    cache_key = f"{session_id}:{query_params.get('metric')}:{query_params.get('start_date')}"

    if cache_key in QUERY_RESULT_CACHE:
        return QUERY_RESULT_CACHE[cache_key]["data"]

    # Compute metrics from raw dataset
    metric = query_params.get("metric", "views")
    aggregated_val = sum(item.get(metric, 0) for item in raw_dataset)

    result_payload = {
        "metric": metric,
        "count": len(raw_dataset),
        "aggregated_total": aggregated_val,
        "raw_samples": raw_dataset[:100],  # stores large object references
        "generated_at": time.time(),
    }

    # Unbounded retention: indefinitely kept in memory for the process lifetime
    QUERY_RESULT_CACHE[cache_key] = {
        "session_id": session_id,
        "data": result_payload,
        "cached_at": time.time(),
    }

    return result_payload
