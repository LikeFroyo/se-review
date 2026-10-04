"""Running total over a stream of adjustments, maintained incrementally."""
from dataclasses import dataclass, field


@dataclass
class Ledger:
    balance: int = 0
    applied: list = field(default_factory=list)

    def apply(self, entry) -> None:
        self.balance += entry.amount
        self.applied.append(entry)

    def reclassify(self, entry, new_amount: int) -> None:
        """Move an entry to a different amount without re-deriving the balance."""
        entry.amount = new_amount
        self.applied[entry.index] = entry
