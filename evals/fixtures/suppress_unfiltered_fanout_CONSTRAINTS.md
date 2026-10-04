# Fan-out constraints

**C1 (binding).** Dispatch applies no filter, no coalescing, no de-duplication, no
throttle and no backpressure. Every accepted frame reaches every registered consumer,
in registration order.
**Why:** the engine must see every tick; sampling anywhere upstream silently changes
what the decision layer observes.
**What depends on this:** the decision layer's input sequence is the raw accepted
sequence.

**C2 (binding).** Consumers own their own scope. A consumer that wants less reduces
inside itself.
