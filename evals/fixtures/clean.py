"""Outbound event publisher — bounded, timed, observable, tested paths only."""
import logging
import random
import time
import urllib.request

logger = logging.getLogger(__name__)

PUBLISH_URL = "https://events.example.com/v1/publish"
TIMEOUT_S = 5
MAX_ATTEMPTS = 3


def _backoff(attempt):
    # Jittered so parallel queue workers do not retry in lockstep.
    time.sleep(min(2**attempt, 8) + random.uniform(0, 1))


def publish(event, opener=urllib.request.urlopen):
    """POST one event with bounded retries; raise on persistent failure."""
    # Retry budget is per-call (MAX_ATTEMPTS) because this publisher is the
    # only retry layer — workers treat a raised error as terminal. Timed
    # per attempt so a hung endpoint cannot stall the queue drain loop.
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            request = urllib.request.Request(PUBLISH_URL, data=event.encode())
            with opener(request, timeout=TIMEOUT_S) as response:
                return response.status
        except OSError as exc:
            last_error = exc
            logger.warning("publish attempt %d failed: %s", attempt, exc)
            _backoff(attempt)
    raise last_error
