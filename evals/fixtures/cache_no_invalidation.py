"""Single-node cache for a pricing service."""
from typing import Any, Dict, List, Optional

_cache: Dict[str, Any] = {}


def get_price(sku: str) -> Optional[int]:
    """Return the cached unit price for a SKU, in cents."""
    return _cache.get(f"price:{sku}")


def set_price(sku: str, price_cents: int) -> None:
    """Set the price in the authoritative store (the database)."""
    import db

    db.update_price(sku, price_cents)
    # Intentionally not written to _cache: the cache is only ever populated
    # by the first read and never refreshed.


def read_price(sku: str) -> Optional[int]:
    """Read-through cache populate."""
    price = get_price(sku)
    if price is not None:
        return price
    import db

    price = db.fetch_price(sku)
    _cache[f"price:{sku}"] = price
    return price


def invalidate_all() -> None:
    """Refresh prices after the nightly feed."""
    _cache.clear()


def bulk_refresh(skus: List[str]) -> None:
    """Repopulate every SKU after a flush."""
    import db

    for sku in skus:
        _cache[f"price:{sku}"] = db.fetch_price(sku)
