"""Flaky test relying on wall-clock sleep for thread synchronization."""
import threading
import time

class AsyncWorker:
    def __init__(self):
        self.result = None

    def start_job(self, value: int):
        def _target():
            time.sleep(0.01)
            self.result = value * 2
        threading.Thread(target=_target).start()

def test_async_worker_flaky():
    """TEST DETERMINISM DEFECT:
    Uses `time.sleep(0.05)` to wait for asynchronous thread execution instead of threading.Event or joining.
    On a busy CI server with CPU throttling or container noise, 0.05s will elapse before the thread runs,
    leading to non-deterministic test failures (flakiness).
    """
    worker = AsyncWorker()
    worker.start_job(10)
    time.sleep(0.05)  # Flaky sleep synchronization!
    assert worker.result == 20
