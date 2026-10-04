"""Fan-out to registered consumers.

Constraints: FANOUT_CONSTRAINTS.md
"""
import logging

logger = logging.getLogger(__name__)


class Fanout:
    def __init__(self):
        self._consumers = []

    def register(self, consumer):
        self._consumers.append(consumer)

    def dispatch(self, frame):
        for consumer in self._consumers:
            consumer(frame)


class StrikeSampler:
    """Wants one strike per hundred; samples inside itself, not in dispatch."""

    def __init__(self):
        self._seen = 0
        self.latest = None

    def __call__(self, frame):
        self._seen += 1
        if self._seen % 100:
            return
        self.latest = frame
