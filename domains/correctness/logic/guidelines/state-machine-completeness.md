# State machine completeness — the transitions that were never written

Audit the transition relation, not the representation. How states are stored is covered under
complexity; this asks whether the machine can actually move, and whether it can get out.

## Missing transitions

- **No exit from a waiting state:** A reachable pending, waiting, or in-progress state has no outbound transition other than deletion — no timeout, expiry, cancellation, or release — so anything that never receives its completion event stays there forever.
- **No transition for an event that will occur:** Late arrival, duplicate delivery, out-of-order arrival, or a stream that simply stops are all real and none has a transition.
- **Initial state undefined or wrong:** The starting state is not defined, or is defined as something other than "nothing has happened yet", so a cold start enters a state the machine was never designed to be in.

## Transitions that are not closed

- **State set not closed:** Any combination of fields is storable and the reader must infer the meaning, so an invalid combination is representable and reachable.
- **Guard bypassed by a direct write:** A transition is protected by a check inside a method, but the fields are also writable elsewhere, so the invariant holds only on the path somebody remembered to use.
- **Transition effects not idempotent:** Re-entering the same state reapplies its side effects — a counter incremented twice, an event emitted twice — so a retry or a re-delivery duplicates the effect.
- **No recorded reason for a state:** A state can be reached without any record of how, so an unexpected state cannot be diagnosed from the system itself.
