"""Order intake with a reconnect disarm window.

Constraints: INTAKE_CONSTRAINTS.md
"""
import logging
from queue import Queue

logger = logging.getLogger(__name__)


class Intake:
    def __init__(self, consumer):
        self._queue = Queue()
        self._consumer = consumer
        self._armed = True
        self.enqueued = 0
        self.peak_backlog = 0

    def arm(self):
        self._armed = True

    def disarm(self):
        self._armed = False

    def offer(self, frame):
        if not self._armed:
            return False
        self._queue.put(frame)
        self.enqueued += 1
        self.peak_backlog = max(self.peak_backlog, self._queue.qsize())
        return True

    def run(self, stop):
        while not stop():
            self._consumer(self._queue.get())


class SocketAdapter:
    """Bridges the socket's byte callback onto the intake queue."""

    def __init__(self, intake):
        self.on_message = intake.offer
