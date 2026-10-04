# Memory retention — unbounded caches, leaks, and high cardinality

Audit memory lifecycle and collection retention.

## What to look for

- **Unbounded in-memory collections:** Module-level or global dictionaries and lists accumulating request payloads, sessions, or records without max-size bounds or TTL eviction.
- **Leaked listeners & workers:** Attaching observers, callbacks, or spawning worker loops that are never detached or canceled on teardown.
- **High-cardinality cache keys:** Using raw UUIDs, unbounded user IDs, or query parameter combinations as in-memory cache keys without eviction.
- **Object graph retention:** Retaining references to large parent data structures when only a small primitive or slice was needed.
