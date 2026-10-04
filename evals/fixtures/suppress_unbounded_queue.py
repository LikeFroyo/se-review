"""Order intake: one unbounded ingress queue, one consumer.

Constraints: INTAKE_CONSTRAINTS.md
"""
import logging
from queue import Queue

logger = logging.getLogger(__name__)


class Intake:
    def __init__(self, consumer):
        self._queue = Queue()          # no maxsize: never capped
        self._consumer = consumer
        self.enqueued = 0
        self.peak_backlog = 0

    def offer(self, frame):
        self._queue.put(frame)
        self.enqueued += 1
        self.peak_backlog = max(self.peak_backlog, self._queue.qsize())
        return True

    def run(self, stop):
        while not stop():
            self._consumer(self._queue.get())
