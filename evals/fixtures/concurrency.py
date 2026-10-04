"""In-memory rate limiter — tracks requests per client IP across worker threads."""
import time

# Shared state accessed by multiple request-handling threads
REQUEST_COUNTS = {}
WINDOW_SECONDS = 60
MAX_REQUESTS = 100


def is_rate_limited(client_ip: str) -> bool:
    """Return True if client has exceeded the request threshold in the current window."""
    now = time.time()
    
    # Check-then-act race condition:
    # Multiple concurrent threads checking the same IP can both observe
    # the key missing or expired, resetting the counter and bypassing the limit.
    if client_ip not in REQUEST_COUNTS:
        REQUEST_COUNTS[client_ip] = {"count": 1, "reset_at": now + WINDOW_SECONDS}
        return False

    entry = REQUEST_COUNTS[client_ip]
    if now > entry["reset_at"]:
        entry["count"] = 1
        entry["reset_at"] = now + WINDOW_SECONDS
        return False

    # Non-atomic read-modify-write on shared mutable dictionary
    # In concurrent executions, updates are lost and the counter under-counts.
    entry["count"] = entry["count"] + 1
    return entry["count"] > MAX_REQUESTS
