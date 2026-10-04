# Architectural boundaries & DDD — domain purity and layering

Audit architectural layering and domain model isolation.

## What to look for

- **Layer breaches:** Core domain logic importing web frameworks, HTTP request types, or database-specific drivers.
- **Anemic domain models:** Bare data classes with zero invariants, while all business validation is scattered across controllers or service scripts.
- **Leaky abstractions:** Low-level implementation details (e.g. database locking hints or network serialization formats) leaking through interface signatures.
- **Primitive obsession:** Passing loose primitives (e.g. `amount: float`, `currency: str`) everywhere instead of cohesive Value Objects with construction validation.

## Error policy at a boundary

- **Undefined failure contract:** A module that catches and returns a null, an empty collection, or a sentinel value, while its callers read that as a real absence rather than a failure — so a lookup that threw and a lookup that found nothing are indistinguishable.
- **Failure swallowed at the boundary:** An exception caught and discarded at the seam, so the caller's error handling never runs and the failure surfaces as wrong data several layers up.
- **Exception type as the only contract:** A boundary whose failure mode is an exception class the caller must already know, with no documented or typed alternative, so a new caller silently treats the error as a value.
- **Error translated lossily on the way out:** An internal failure mapped to a generic error before crossing the boundary, discarding the distinction a caller would need to decide whether to retry, fall back, or escalate.
