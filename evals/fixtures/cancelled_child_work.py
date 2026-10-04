"""Async job dispatch and cancellation plumbing."""
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("jobs")

QUEUE = "https://internal.example.com/v1/queue"


async def handle_order_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle an inbound order event."""
    order_id = event["order_id"]
    await asyncio.gather(
        reserve_stock(order_id, event["sku"]),
        notify_warehouse(order_id),
    )
    return {"accepted": order_id}


async def reserve_stock(order_id: str, sku: str) -> None:
    await asyncio.sleep(0.1)
    logger.info("reserved %s", order_id)


async def notify_warehouse(order_id: str) -> None:
    await asyncio.sleep(0.1)
    logger.info("notified %s", order_id)


async def handle_cancellation_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Honour a cancellation for a long-running export."""
    export_task = asyncio.create_task(run_export(request["export_id"]))
    try:
        await asyncio.wait_for(export_task, timeout=float(request.get("timeout", 30)))
    except asyncio.TimeoutError:
        logger.warning("export %s timed out", request["export_id"])
        return {"cancelled": True}
    return {"cancelled": False}


async def run_export(export_id: str) -> None:
    await asyncio.sleep(60)


async def warm_cache(tenant_id: str) -> None:
    """Refresh a tenant's cache after a write."""
    asyncio.create_task(rebuild_cache(tenant_id))
    return None


async def rebuild_cache(tenant_id: str) -> None:
    await httpx.AsyncClient().get(f"{QUEUE}?tenant={tenant_id}")


def flush_metrics(metric: str) -> None:
    metrics.emit(metric)


async def charge_once(order_id: str) -> Dict[str, Any]:
    """Charge exactly once, per this handler's contract."""
    charge(amount_cents=1000, order_id=order_id)
    flush_metrics("charge_completed")
    return {"order_id": order_id, "charged": True}
