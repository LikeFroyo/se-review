"""Absorber: one writer, the pipeline's single consumer thread.

Constraints: ACCUMULATOR_CONSTRAINTS.md
"""
from collections import defaultdict


class Absorber:
    def __init__(self):
        self._frozen = {}          # slot -> value, owned by the consumer thread
        self._pending = defaultdict(int)

    def apply(self, slot, contribution):
        self._pending[slot] += contribution
        if contribution == 0:
            return
        self._frozen[slot] = self._frozen.get(slot, 0.0) + contribution

    def freeze(self):
        return {slot: value for slot, value in self._frozen.items()}


PUMPED = 0


def pump(rows, absorber):
    """The only caller of apply(). Started once, on one thread."""
    global PUMPED
    for row in rows:
        absorber.apply(row["slot"], row["contribution"])
        PUMPED += 1
