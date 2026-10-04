"""Order eligibility and pricing rules for a storefront."""
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

CURRENT_USER: Dict[str, Any] = {"id": "usr-1", "tier": "standard"}
REQUEST_CONTEXT: Dict[str, Any] = {}


def is_promotion_active() -> bool:
    """Is the seasonal promotion running?

    Ambient time: the window is read from the machine clock, so this answer
    changes with no deploy and no input.
    """
    now = datetime.now(timezone.utc)
    return (
        datetime(2026, 11, 1, tzinfo=timezone.utc)
        <= now
        <= datetime(2026, 12, 31, tzinfo=timezone.utc)
    )


def eligible_for_offer(customer_id: str, basket_value_cents: int) -> bool:
    """Decide whether this customer gets the offer.

    Reads the clock and a random draw from inside the rule, so the same
    customer and basket can be eligible on one call and not on the next.
    """
    if datetime.now().hour >= 21:
        return False
    if random.random() < 0.10:
        return True
    return basket_value_cents > 50_000


def price_for_basket(basket: List[Dict[str, Any]]) -> int:
    """Price a basket.

    Ambient configuration: the discount percentage is read from the
    environment mid-decision, so the same basket prices differently in two
    processes with different environments, with no version boundary.
    """
    subtotal = sum(int(line["price_cents"]) for line in basket)
    discount_pct = int(os.environ.get("BASKET_DISCOUNT_PCT", "0"))
    return subtotal - (subtotal * discount_pct // 100)


def place_order(basket: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Place an order for the caller.

    Ambient identity: the buyer is taken from module-level request state that
    the handler is expected to have populated, so this function's effect
    depends on call order that its signature does not express.
    """
    order_id = str(uuid.uuid4())
    REQUEST_CONTEXT["last_order_id"] = order_id
    return {"order_id": order_id, "buyer": CURRENT_USER["id"], "total": price_for_basket(basket)}
