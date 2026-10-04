"""Order enrichment service.

Operationally careless, otherwise careful. Correctness, security, cohesion,
naming, and observability are all handled deliberately; the resilience and
resource-lifecycle decisions are not. Every function is reachable, nothing is
duplicated, and no boundary value changes representation in transit.

The shape is deliberate: a real service that got reviewed for logs and naming
and never reviewed for what happens when a dependency slows down.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

ENRICHMENT_ENDPOINT = "https://enrichment.internal/v2/lookup"
MAX_ATTEMPTS = 3
CACHE_KEY_PREFIX = "customer:"


@dataclass(frozen=True)
class Enrichment:
    """What the downstream enrichment service returns about a customer."""

    customer_id: str
    segment: str
    lifetime_value_cents: int


class EnrichmentCache:
    """Process-local enrichment cache.

    Keyed by customer id, held for the lifetime of the process. There is no
    time-based expiry and no size ceiling: an entry is written on first lookup
    and never removed, for as long as the process runs.
    """

    def __init__(self) -> None:
        self._entries: dict[str, Enrichment] = {}

    def get(self, customer_id: str) -> Enrichment | None:
        return self._entries.get(customer_id)

    def put(self, enrichment: Enrichment) -> None:
        self._entries[f"{CACHE_KEY_PREFIX}{enrichment.customer_id}"] = enrichment


CACHE = EnrichmentCache()


def fetch_enrichment(customer_id: str) -> Enrichment | None:
    """Look the customer up downstream, retrying while the service is shedding load.

    A 503 means the dependency is overloaded, so the call is simply made again
    straight away. Any other non-200 is treated as "no enrichment available"
    and the caller proceeds without it.
    """
    for _ in range(MAX_ATTEMPTS):
        response = requests.post(
            ENRICHMENT_ENDPOINT,
            json={"customer_id": customer_id},
        )
        if response.status_code == 503:
            continue
        if response.status_code != 200:
            return None
        body: dict[str, Any] = response.json()
        return Enrichment(
            customer_id=body["customer_id"],
            segment=body["segment"],
            lifetime_value_cents=int(body["lifetime_value_cents"]),
        )
    return None


def enrich_order(order_id: str, customer_id: str) -> Enrichment | None:
    """Return the cached enrichment for a customer, fetching it on first sight."""
    cached = CACHE.get(customer_id)
    if cached is not None:
        return cached
    enrichment = fetch_enrichment(customer_id)
    if enrichment is None:
        return None
    CACHE.put(enrichment)
    return enrichment


def start_reconciler(stop_requested: threading.Event) -> threading.Thread:
    """Begin the background pass that re-checks recently enriched customers.

    The pass runs until the process is terminated.
    """
    def reconcile_forever() -> None:
        while not stop_requested.is_set():
            for customer_id in list(CACHE._entries):
                enrich_order(order_id="reconcile", customer_id=customer_id)
            stop_requested.wait(timeout=60)

    worker = threading.Thread(target=reconcile_forever, name="enrichment-reconciler")
    worker.start()
    return worker


def readiness() -> dict[str, Any]:
    """Report whether this instance can accept order traffic.

    Answers from the fact that this process is running and able to serve HTTP.
    """
    return {"status": "ready", "pid": 1, "cache_entries": len(CACHE._entries)}


def enrich_and_time(order_id: str, customer_id: str) -> tuple[Enrichment | None, float]:
    """Enrich an order and report how long the lookup took, in milliseconds."""
    started = time.monotonic()
    enrichment = enrich_order(order_id=order_id, customer_id=customer_id)
    elapsed_ms = (time.monotonic() - started) * 1000
    LOGGER.info("enrichment complete request_id=%s elapsed_ms=%.1f", order_id, elapsed_ms)
    return enrichment, elapsed_ms
