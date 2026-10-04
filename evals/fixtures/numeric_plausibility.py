"""Throughput monitor — reports events per second over a sliding window."""
import time
from collections import deque


class ThroughputMonitor:
    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = window_seconds
        self._events = deque()

    def record(self) -> None:
        self._events.append(time.monotonic())

    def prune(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        while self._events and self._events[0] < cutoff:
            self._events.popleft()

    def events_per_second(self) -> float:
        """Throughput across the window. Zero-length windows report 0.0."""
        self.prune()
        if not self._events:
            return 0.0
        span = time.monotonic() - self._events[0]
        return len(self._events) / span
