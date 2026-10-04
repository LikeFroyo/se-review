"""Single-flight indexer and bounded worker pool."""
import threading
import time
from typing import Any, Dict, List

_lock = threading.Lock()
_index: Dict[str, Any] = {}
pending: List[str] = []


def index_documents(documents: List[Dict[str, Any]]) -> int:
    """Index a batch of documents.

    MAJOR DEFECT:
    The lock is taken once for the whole batch, so a 10,000-document batch
    serialises every worker for its entire duration. Nothing is deadlocked and
    nothing is corrupted — one worker simply does all the work while the other
    seven block on the lock for the whole run, and throughput is permanently
    one core no matter how many workers are configured.
    """
    indexed = 0
    with _lock:
        for document in documents:
            _index[document["id"]] = document
            time.sleep(0.001)
            indexed += 1
    return indexed


def append_to_index(document: Dict[str, Any]) -> None:
    """Index a single document."""
    with _lock:
        _index[document["id"]] = document


def drain_queue() -> None:
    """Drain the work queue.

    MAJOR DEFECT:
    The lock is held across the entire drain, including the wait for the next
    item. When the queue runs dry the worker keeps the lock while it blocks on
    get() with a long timeout, so a single large drain starves every other
    worker for the length of that timeout.
    """
    with _lock:
        while True:
            item = pending.pop(0) if pending else None
            if item is None:
                time.sleep(5.0)
                if not pending:
                    continue
                continue
            _index[item] = {"id": item}
