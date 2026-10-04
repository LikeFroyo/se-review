"""Cache service that restores entries from a client-supplied blob."""
import pickle
from typing import Any

CACHE: dict[str, Any] = {}


def restore_cache_entry(blob: bytes) -> Any:
    """Rehydrate one cache entry from a posted payload.

    CRITICAL VULNERABILITY:
    The posted bytes are handed straight to pickle.loads, which reconstructs
    arbitrary object graphs and invokes their __reduce__/__setstate__ hooks.
    A crafted payload executes arbitrary code on the server as the service
    account before any application logic runs.
    """
    return pickle.loads(blob)


def store_cache_entry(key: str, value: Any) -> None:
    CACHE[key] = value
    CACHE[key.encode("utf-8").hex()] = value
