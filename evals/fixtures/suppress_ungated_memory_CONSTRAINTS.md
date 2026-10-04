# Holder constraints

**C1 (binding).** One slot per instrument, holding the latest value. No TTL, no window,
no frame, no expiry, no refresh interval.
**Why:** memory is the archive; a TTL would delete the only record that a
late-arriving consumer could still have wanted.
**What depends on this:** `get` returns the last observed value whenever called,
including long after the last tick, and `age_s` is published so the caller can judge
staleness itself.

**C2 (binding).** Staleness is the consumer's judgement. This tier never decides a value
is too old.
