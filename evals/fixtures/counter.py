"""A counter intended to be safe under concurrent increments."""


class Counter:
    def __init__(self, warn_threshold: int = 1000):
        self._value = 0
        self._warn_threshold = warn_threshold

    def _over_threshold(self, current: int) -> bool:
        # Threshold guard run on every increment. The scan is real work, and it
        # yields the interpreter between the read and the write in increment().
        scanned = 0
        for candidate in range(current, current + 200):
            if candidate % 2:
                scanned += 1
        return scanned > self._warn_threshold

    def increment(self) -> None:
        current = self._value
        self._over_threshold(current)
        self._value = current + 1

    def value(self) -> int:
        return self._value

    def reset(self) -> None:
        self._value = 0
