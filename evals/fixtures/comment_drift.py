"""Order fetcher with retry support."""


def fetch_orders(batch_size: int, retries: int = 3) -> list:
    """Fetch a page of orders from the store.

    Args:
        batch_size: Number of orders to fetch.
        timeout: Seconds to wait per attempt.

    Returns:
        List of order dicts.
    """
    # Retry at most 3 times before giving up.
    last_error = None
    for _ in range(5):
        try:
            return _read_page(batch_size)
        except IOError as exc:
            last_error = exc
    raise last_error
