# Backward compatibility — contract stability and breaking changes

Audit API endpoints, wire serialization, and public contract changes.

## What to look for

- **Breaking contract changes:** Renaming or removing fields in request or response schemas on unversioned or active API endpoints.
- **Type narrowing:** Enforcing stricter validation or changing optional fields into required fields on existing contracts.
- **Leaking domain entities:** Returning internal database models or ORM entities directly across the wire rather than explicit Data Transfer Objects (DTOs).
- **Silent status code flips:** Changing HTTP response status codes (e.g. changing 404 to 200 with empty body) without version gates.

## Response shape

- **Response enum widened without a tolerance rule:** A closed set of values in a response that the server may now emit a new member of, where existing clients switch exhaustively and fail on the unknown case — the server change is backward-incompatible by construction.
- **Null conflated with absent:** A field that is `null` both when the value is missing and when it is explicitly cleared, so the client cannot tell "never set" from "set to nothing" and never asks again.
- **New field that shadows an old one:** An added field whose meaning differs from an existing field of a similar name, so an older client reading the old field gets a value with new semantics.
- **Version segment with no branch:** A `/v1/`, `/v2/` path segment that does not actually select different behaviour, so the version a client declares carries no guarantee and two incompatible contracts share one handler.
