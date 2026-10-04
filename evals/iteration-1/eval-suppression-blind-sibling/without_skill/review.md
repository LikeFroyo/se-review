Reviewing your blind-sibling fixture against its constraints.
Review: No violation.

* `suppression_blind_sibling.py:17-19` — `Fanout.dispatch` forwards every `frame` to every consumer in registration order, with no filter/coalescing/dedup. Satisfies C1.
* `suppression_blind_sibling.py:29-33` — `ChainRecorder.__call__` dedupes on `price` inside itself only, does not mutate `frame` or affect delivery to siblings. Explicitly permitted by C2: "A consumer that wants less reduces inside itself."

Blind-sibling filtering is not fan-out suppression.