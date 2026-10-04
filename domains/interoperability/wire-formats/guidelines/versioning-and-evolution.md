# Versioning & evolution — adding is free, changing is not

Audit whether a format may still be changed after others depend on it, and whether consumers can survive a change they have not seen.

## What to look for

- **Breaking change without a version gate:** A field renamed, removed, retyped, or made required in a queue message, an object-store payload, or a cache value that an unupgraded consumer still reads, with no version on the payload to select the old behaviour.
- **No unknown-field tolerance:** A consumer configured to fail on unrecognised fields, so a producer's purely additive change breaks it — the change that was supposed to be safe in both directions.
- **Field number or tag reused:** A numeric tag or ordinal bound to a new meaning in a binary format, so an old message is read as the new field with the old value and no error.
- **Format negotiated with no default:** A representation selected per request from an `Accept` header or a query parameter, with no default and no pinning, so a client that omits it silently gets a different shape than the one it was written for.
- **Consumer ahead of producer in the rollout:** A new consumer deployed before its producer, reading a field that does not exist yet, with no fallback for the absent case.
- **Tight coupling to a private internal shape:** An internal event, table dump, or file whose schema is treated as stable but is owned by one team's model, so an unrelated refactor breaks every consumer.
- **No schema recorded anywhere:** A payload shape agreed in a message body or a wiki and implemented twice, so the two implementations are the only definition and there is nothing to validate against.
- **Version recorded but not enforced:** A version field present in the payload that no consumer actually checks, so an incompatible payload is accepted because the field says something.
