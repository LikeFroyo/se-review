# Secret material — storage, logging, and lifetime

Audit where a secret lives, who can read it, and what happens to it after use. Most exposure is not
a broken cipher; it is correct cryptography applied to material that reached the wrong place.

- **Secret in a log, an error message, or a returned payload:** A credential included in a failure path, a debug line, or a serialised response, where it outlives the request in a system with wider readership.
- **Secret in source, a fixture, or a default:** A key, password, or token committed in code or shipped as a fallback, so rotating it requires a release.
- **Secret derived predictably:** A token built from a timestamp, a counter, an identifier, or any value an attacker can narrow, rather than drawn from a cryptographic source.
- **No rotation path:** A secret that cannot be replaced without downtime, so a suspected exposure has no remedy and the exposure is permanent.
- **Secret reused across environments or services:** One material in several places, so compromising the weakest copy compromises all of them.
- **Decrypted material held longer than needed:** A secret loaded into memory at start and never released, widening the window for any memory-read defect.
- **Secret cached in a store with weaker protection than its source:** A credential persisted in a cache, index, or replica that has different access control from the system it came from.
