# Type & contracts — assertions the type system should be making

Audit the places where a check is asserted rather than enforced: casts, suppressions, dynamic lookups, and generated/validated boundaries.

## Unchecked assertion

- **Blanket cast across a real boundary:** `Any`, `as T`, a non-null assertion, or a C-style cast converting one shape into another with no validation between — a cast is a claim, and an unchecked one is an unverified claim.
- **Suppression without a justification:** A type-ignore, `@ts-ignore`, lint-disable, or `noqa` with no comment recording what was checked and by what, so the suppression accumulates and nobody can audit it later.
- **Dynamic attribute or key access:** `getattr`, `obj[field]`, or a string-keyed lookup whose result is used as a typed value with no check that the key exists or the shape matches.

## Boundary validation

- **Parsed input trusted as the declared type:** A deserialised payload, a query row, an environment value, or an HTTP body used as its annotation without validating required fields, nullability, ranges, or unknown keys.
- **Contract drift between producer and consumer:** A typed record, schema, or dataclass declared in one place and constructed from a differently-shaped payload in another, with no single source both sides are checked against.
- **Partial implementation of a declared interface:** A subclass or adapter that satisfies the type while omitting methods, returning wrong shapes, or raising for the ones it does not implement.
- **Default that masks a missing required value:** A default supplied for a field the contract declares required, so a missing value is silently replaced rather than rejected.
- **Validator that can be bypassed:** Validation applied on one construction path (an API handler) and not on another (a background job, a migration, a fixture), so the same invalid record is constructible.
