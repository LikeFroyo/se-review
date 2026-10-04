"""Fan-out to registered consumers, with a de-duplicating recorder.

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


class ChainRecorder:
    """Holds the latest settlement state for the chain it was given."""

    def __init__(self):
        self._last_price = None
        self.state = None

    def __call__(self, frame):
        if frame["price"] == self._last_price:
            return
        self._last_price = frame["price"]
        self.state = frame["state"]
