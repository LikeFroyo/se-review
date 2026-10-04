Reviewing your blind-sibling fixtures against their constraints.
Found the price-only dedup that blinds state changes — now checking how it's exercised.
Review of `suppression_blind_sibling.py` vs `suppress_unfiltered_fanout_CONSTRAINTS.md`:

* `suppression_blind_sibling.py:17-19` `Fanout.dispatch` compliant with C1: no filter/coalesce/dedupe, iterates `self._consumers` in registration order.
* `suppression_blind_sibling.py:29-33` `ChainRecorder.__call__` defective: dedupes on `frame["price"]` alone, then returns before updating `self.state`. Same-price / new-`state` frame e.g. `{"price":100,"state":"open"}` -> `{"price":100,"state":"settled"}` leaves `state=="open"` stale.
* C2 permits consumer-side reduction, but not this one: class contract is “holds latest settlement state”, so suppressing on blind sibling field contradicts its own scope.
* Fix: dedupe on `(price, state)` or full frame, or always assign `self.state`.
* Nit: `suppression_blind_sibling.py:3` references `FANOUT_CONSTRAINTS.md`, actual file is `suppress_unfiltered_fanout_CONSTRAINTS.md`.