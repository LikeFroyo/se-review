# Caching — staleness bounds and invalidation safety

Audit every cached value as a correctness claim: how stale may it be, who invalidates it, and what happens when they all miss at once.

## Staleness

- **No stated staleness bound:** A cache with no TTL, no version, and no invalidation path, so a reader cannot know how old the value is.
- **No write path:** Nothing updates or invalidates the entry when the source of truth changes, so a revoked permission, a corrected price, or a deleted record keeps being served.
- **Partial cache key:** A key built from some of the inputs that determine the value, so two different results collide on one cached entry.
- **Cache treated as source of truth:** A value read only from cache, with no path back to the authoritative store when the entry is missing or corrupt.

## Invalidation safety

- **Flush as the invalidation strategy:** Dropping the whole cache to refresh part of it, so every hot key misses simultaneously and the origin takes the full read load.
- **No stampede protection:** A per-key miss that recomputes without a lock, a single-flight guard, or a stale-while-revalidate path, so a popular key is recomputed by every concurrent request.
- **Negative caching without a bound:** Caching "not found" for a long period, so a record created after the miss is invisible until the entry expires.
